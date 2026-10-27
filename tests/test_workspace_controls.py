import json,tempfile,unittest,uuid
from unittest.mock import Mock,patch
from types import SimpleNamespace
import httpx
from fastapi.testclient import TestClient
from servidor_pc.main import create_app
from servidor_pc.cloud import CloudConfig
class WorkspaceControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  env=patch.dict('os.environ',{'SFA_CLOUD_CONFIG':self.tmp.name+'/absent.json','GOOGLE_APPLICATION_CREDENTIALS':''});env.start();self.addCleanup(env.stop)
  self.app=create_app(self.tmp.name,background=False);self.rt=self.app.state.runtime;self.client=TestClient(self.app);self.client.__enter__();self.addCleanup(lambda:self.client.__exit__(None,None,None))
  self.room=str(uuid.uuid4());self.gateway=str(uuid.uuid4());self.calls=[];self.allowed=True
  self.rt.cloud.config=CloudConfig(url='https://example.supabase.co',publishable_key='sb_publishable_fixture_only_123',classroom_id=self.room,gateway_id=self.gateway,gateway_secret='fixture-only-secret-'+'x'*50)
  def transport(request):
   self.calls.append(request)
   return httpx.Response(200,json={'classroom_id':json.loads(request.content)['p_classroom_id'],'can_manage_gateways':self.allowed,'gateways':[{'id':self.gateway,'enabled':True}]})
  self.rt.workspace_transport=httpx.MockTransport(transport)
 def call(self,action,**extra):
  return self.client.post('/api/workspace/local',headers={'Authorization':'Bearer actor-session-fixture'},json={'classroom_id':self.room,'action':action,**extra})
 def test_requires_session(self):
  r=self.client.post('/api/workspace/local',json={'classroom_id':self.room,'action':'state'});self.assertEqual(r.status_code,401);self.assertEqual(self.calls,[])
 def test_read_state_never_exposes_control_key_or_gateway_secret(self):
  r=self.call('state');self.assertEqual(r.status_code,200);text=r.text;self.assertNotIn(self.rt.token,text);self.assertNotIn(self.rt.cloud.config.gateway_secret,text);self.assertNotIn('token',r.json());self.assertEqual(r.json()['classroom_id'],self.room)
 def test_observer_cannot_read_or_control_local_admin(self):
  self.allowed=False
  for action in ['state','ports','connect','stop','rules']:self.assertEqual(self.call(action).status_code,403)
 def test_other_classroom_cannot_operate_this_pc(self):
  r=self.client.post('/api/workspace/local',headers={'Authorization':'Bearer actor-session-fixture'},json={'classroom_id':str(uuid.uuid4()),'action':'stop'});self.assertEqual(r.status_code,409);self.assertEqual(self.rt.source,'detenido')
 def test_scans_ports_without_connecting(self):
  with patch('serial.tools.list_ports.comports',return_value=[SimpleNamespace(device='COM7',description='Arduino UNO')]),patch('serial.Serial') as serial:
   r=self.call('ports');self.assertEqual(r.json()['ports'][0]['port'],'COM7');serial.assert_not_called()
 def test_connect_and_stop_use_same_runtime_and_monitor_contract(self):
  port=Mock();port.port='COM7'
  with patch('serial.tools.list_ports.comports',return_value=[SimpleNamespace(device='COM7',description='UNO')]),patch('serial.Serial',return_value=port):
   r=self.call('connect',port='COM7');self.assertEqual(r.status_code,200);port.write.assert_called_with(b'MONITOR\n');self.assertEqual(self.rt.source,'arduino')
   r=self.call('stop');self.assertEqual(r.status_code,200);port.write.assert_called_with(b'PARAR\n');port.close.assert_called();self.assertEqual(self.rt.source,'detenido')
 def test_arbitrary_unlisted_port_is_rejected(self):
  with patch('serial.tools.list_ports.comports',return_value=[]),patch('serial.Serial') as serial:
   self.assertEqual(self.call('connect',port='COM999').status_code,400);serial.assert_not_called()
 def test_mutation_rechecks_permission_even_after_cached_read(self):
  self.assertEqual(self.call('state').status_code,200);self.allowed=False
  self.assertEqual(self.call('stop').status_code,403);self.assertEqual(len(self.calls),2)
 def test_rules_are_versioned_and_temperature_can_be_configured(self):
  state=self.call('state').json();rules=state['rules'];rules['temperature_enabled']=True
  r=self.call('rules',rules=rules,rules_revision=state['rules_revision']);self.assertEqual(r.status_code,200);self.assertTrue(self.rt.rules.temperature_enabled)
  self.assertEqual(self.call('rules',rules=rules,rules_revision=state['rules_revision']).status_code,409)
 def test_wrong_response_or_disabled_gateway_never_authorizes(self):
  for value in [{'classroom_id':str(uuid.uuid4()),'can_manage_gateways':True},{'classroom_id':self.room,'can_manage_gateways':True,'gateways':[{'id':self.gateway,'enabled':False}]}]:
   self.rt.workspace_transport=httpx.MockTransport(lambda req:httpx.Response(200,json=value))
   self.assertIn(self.call('stop').status_code,[403,409])

 def test_assignment_status_explains_other_classroom_without_exposing_secrets(self):
  target=str(uuid.uuid4())
  r=self.client.post('/api/workspace/local',headers={'Authorization':'Bearer actor-session-fixture'},json={'classroom_id':target,'action':'assignment'})
  self.assertEqual(r.status_code,200);self.assertFalse(r.json()['assigned']);self.assertEqual(r.json()['current_classroom_id'],self.room)
  self.assertNotIn(self.rt.cloud.config.gateway_secret,r.text)
 def assign_to(self,target):
  return self.client.post('/api/workspace/local',headers={'Authorization':'Bearer actor-session-fixture'},json={'classroom_id':target,'action':'assign'})
 def test_assignment_rejects_running_source_and_unsent_queue(self):
  target=str(uuid.uuid4());self.rt.switch('simulacion');self.assertEqual(self.assign_to(target).status_code,409)
  self.rt.switch('detenido')
  with self.rt.store.transaction() as db:db.execute("insert into cloud_outbox(gateway_id,payload,created) values(?,?,0)",(self.gateway,'{}'))
  self.assertEqual(self.assign_to(target).status_code,409);self.assertEqual(str(self.rt.cloud.config.classroom_id),self.room)
 def assignment_transport(self,target,new_gateway,fail=False):
  def transport(request):
   self.calls.append(request);body=json.loads(request.content)
   if request.url.path.endswith('aire_assign_pc'):
    self.assertEqual(body['p_previous_gateway_id'],self.gateway);self.assertGreaterEqual(len(body['p_secret']),40)
    return httpx.Response(503,json={'message':'offline'}) if fail else httpx.Response(200,json={'gateway_id':new_gateway,'classroom_id':target})
   return httpx.Response(200,json={'classroom_id':body['p_classroom_id'],'can_manage_gateways':self.allowed,'gateways':[{'id':new_gateway,'enabled':True}]})
  self.rt.workspace_transport=httpx.MockTransport(transport)
 def test_assignment_persists_without_moving_history_and_restarts(self):
  from pathlib import Path
  from servidor_pc.cloud import CloudBridge
  target=str(uuid.uuid4());new_gateway=str(uuid.uuid4());self.assignment_transport(target,new_gateway)
  with self.rt.store.transaction() as db:db.execute("insert into incidents(id,source,severity,opened,updated) values('old','arduino','aviso',0,0)")
  r=self.assign_to(target);self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['assigned']);self.assertNotIn('secret',r.text)
  self.assertEqual(str(self.rt.cloud.config.classroom_id),target)
  self.assertEqual(self.rt.store.rows("select cloud_gateway_id from incidents where id='old'")[0]['cloud_gateway_id'],self.gateway)
  restarted=CloudBridge(self.rt.store,self.rt.cloud.path,self.rt.push);self.assertEqual(str(restarted.config.gateway_id),new_gateway)
  self.assertTrue((self.rt.cloud.path.parent/'pc-bindings'/(self.room+'.json')).exists())
  self.assertNotIn('actor-session-fixture',self.rt.cloud.path.read_text())
 def test_failed_assignment_keeps_old_config_and_reuses_pending_secret(self):
  target=str(uuid.uuid4());new_gateway=str(uuid.uuid4());self.assignment_transport(target,new_gateway,True)
  self.assertEqual(self.assign_to(target).status_code,503);self.assertEqual(str(self.rt.cloud.config.gateway_id),self.gateway)
  first=json.loads(self.calls[-1].content)['p_secret'];self.assignment_transport(target,new_gateway)
  self.assertEqual(self.assign_to(target).status_code,200);self.assertEqual(json.loads(self.calls[-1].content)['p_secret'],first)
 def test_assignment_rejects_lan_control(self):
  with TestClient(self.app,client=('192.168.1.55',45000)) as client:
   r=client.post('/api/workspace/local',headers={'Authorization':'Bearer actor-session-fixture'},json={'classroom_id':str(uuid.uuid4()),'action':'assign'})
   self.assertEqual(r.status_code,403)

 def test_new_aula_alert_never_reuses_or_uploads_old_aula_incident(self):
  from servidor_pc.models import Sample
  target=str(uuid.uuid4());new_gateway=str(uuid.uuid4());self.assignment_transport(target,new_gateway)
  with self.rt.store.transaction() as db:db.execute("insert into incidents(id,source,severity,opened,updated) values('old-aula-incident','arduino','aviso',0,0)")
  self.assertEqual(self.assign_to(target).status_code,200)
  self.rt.switch('arduino')
  decision=SimpleNamespace(state='alerta',ratio=2,causes=['mq135'],transition='alerta')
  with patch.object(self.rt.engine,'evaluate',return_value=decision):
   self.rt.ingest(Sample(mq_raw=600,temperature=25,humidity=55),'arduino',now=100)
  rows=self.rt.store.rows('select * from cloud_outbox');self.assertEqual(len(rows),1)
  packet=json.loads(rows[0]['payload']);self.assertEqual(rows[0]['gateway_id'],new_gateway)
  self.assertEqual(len(packet['incidents']),1);self.assertNotEqual(packet['incidents'][0]['id'],'old-aula-incident')
  self.assertEqual(len(self.rt.store.rows('select * from incidents')),2)
