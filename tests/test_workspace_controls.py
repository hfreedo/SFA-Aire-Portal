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
 def test_local_read_does_not_wait_for_cloud_network_lock(self):
  import threading
  self.assertEqual(self.call('state').status_code,200)
  held=threading.Event();release=threading.Event()
  def cloud_network():
   with self.rt.cloud.config_lock:
    held.set();release.wait(3)
  thread=threading.Thread(target=cloud_network);thread.start();self.assertTrue(held.wait(1))
  try:
   result=[]
   reader=threading.Thread(target=lambda:result.append(self.call('state')));reader.start();reader.join(1)
   self.assertFalse(reader.is_alive(),'Las lecturas locales esperan a la red cloud')
   self.assertEqual(result[0].status_code,200)
  finally:
   release.set();thread.join();reader.join()
 def test_missing_dht_keeps_mq135_reading(self):
  from servidor_pc.models import Sample
  self.rt.switch('arduino')
  self.rt.ingest(Sample(mq_raw=123,dht_ok=False), 'arduino')
  state=self.call('state').json()
  self.assertEqual(state['latest']['mq_raw'],123)
  self.assertIsNone(state['latest']['temperature'])
  self.assertFalse(state['latest']['dht_ok'])
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

 def test_retired_pc_can_register_again_without_reactivating_old_secret(self):
  new_gateway=str(uuid.uuid4());old_secret=self.rt.cloud.config.gateway_secret;seen=[]
  def transport(req):
   name=req.url.path.split('/')[-1];body=json.loads(req.content)
   if name=='aire_enroll_pc':
    seen.append(body);self.assertNotEqual(body['p_secret'],old_secret)
    return httpx.Response(200,json={'classroom_id':self.room,'gateway_id':new_gateway})
   return httpx.Response(200,json={'classroom_id':self.room,'can_manage_gateways':True,'gateways':[{'id':self.gateway,'enabled':False},{'id':new_gateway,'enabled':True}]})
  self.rt.workspace_transport=httpx.MockTransport(transport)
  self.assertFalse(self.call('assignment').json()['assigned'])
  response=self.call('assign');self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(str(self.rt.cloud.config.gateway_id),new_gateway)
  self.assertNotEqual(self.rt.cloud.config.gateway_secret,old_secret)
  self.assertNotIn(self.rt.cloud.config.gateway_secret,response.text)
  self.assertTrue(self.call('assignment').json()['assigned'])
  self.assertEqual(self.call('assign').status_code,200);self.assertEqual(len(seen),1)

 def test_retired_pc_failed_response_preserves_retry_identity_and_old_config(self):
  new_gateway=str(uuid.uuid4());secrets=[]
  def transport(req):
   if req.url.path.endswith('aire_enroll_pc'):
    secrets.append(json.loads(req.content)['p_secret'])
    return httpx.Response(503,json={}) if len(secrets)==1 else httpx.Response(200,json={'classroom_id':self.room,'gateway_id':new_gateway})
   return httpx.Response(200,json={'classroom_id':self.room,'can_manage_gateways':True,'gateways':[{'id':self.gateway,'enabled':False}]})
  self.rt.workspace_transport=httpx.MockTransport(transport)
  self.assertEqual(self.call('assign').status_code,503)
  self.assertEqual(str(self.rt.cloud.config.gateway_id),self.gateway)
  self.assertEqual(self.call('assign').status_code,200)
  self.assertEqual(secrets[0],secrets[1])

 def test_retired_pc_recovery_still_requires_admin_and_stopped_acquisition(self):
  self.rt.workspace_transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'classroom_id':self.room,'can_manage_gateways':True,'gateways':[{'id':self.gateway,'enabled':False}]}))
  self.rt.switch('arduino');self.assertEqual(self.call('assign').status_code,409)
  self.rt.switch('detenido')
  self.rt.workspace_transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'classroom_id':self.room,'can_manage_gateways':False,'gateways':[]}))
  self.assertEqual(self.call('assign').status_code,403)

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

 def test_usb_cloud_start_requires_admin_and_current_simulation_frames(self):
  from servidor_pc.models import Sample
  self.assertEqual(self.call('start_usb_lab',run_id=str(uuid.uuid4()),free_plan_confirmed=True).status_code,409)
  self.rt.switch('arduino');self.rt.serial=Mock();self.rt.serial.port='COM7';self.rt.ingest_serial(Sample(mq_raw=6,dht_ok=False))
  self.assertEqual(self.call('start_usb_lab',run_id=str(uuid.uuid4()),free_plan_confirmed=True).status_code,409)
  self.rt.ingest_serial(Sample(serial_contract=2,simulated=True,mq_raw=300,temperature=23,humidity=52,warmed_up=True))
  self.allowed=False
  self.assertEqual(self.call('start_usb_lab',run_id=str(uuid.uuid4()),free_plan_confirmed=True).status_code,403)
 def test_usb_cloud_button_uses_authenticated_rpc_then_gateway_command(self):
  from servidor_pc.models import Sample
  from datetime import datetime,timezone
  import time
  self.rt.switch('arduino');self.rt.serial=Mock();self.rt.serial.port='COM7';self.rt.ingest_serial(Sample(serial_contract=2,simulated=True,mq_raw=300,temperature=23,humidity=52,warmed_up=True))
  run=str(uuid.uuid4());seen=[]
  command={'id':run,'input_source':'usb','temperature':25,'humidity':55,'mq_raw':700,'duration_s':180,'allow_push':True,'allow_takeover':False,'status':'pendiente','expires_at':datetime.fromtimestamp(time.time()+225,timezone.utc).isoformat()}
  def transport(req):
   name=req.url.path.split('/')[-1];seen.append(name)
   if name=='aire_admin_capabilities':return httpx.Response(200,json={'classroom_id':self.room,'can_manage_gateways':True,'gateways':[{'id':self.gateway,'enabled':True}]})
   if name=='aire_lab_start_usb':
    self.assertEqual(req.headers['Authorization'],'Bearer actor-session-fixture');self.assertTrue(json.loads(req.content)['p_free_plan_confirmed']);return httpx.Response(200,json=run)
   if name=='aire_gateway_poll':return httpx.Response(200,json={'classroom_id':self.room,'lab':command,'push_transport':'cloud'})
   return httpx.Response(200,json=None)
  self.rt.workspace_transport=self.rt.cloud.transport=httpx.MockTransport(transport)
  result=self.call('start_usb_lab',run_id=run,free_plan_confirmed=True)
  self.assertEqual(result.status_code,200,result.text);self.assertTrue(result.json()['usb_lab']['active']);self.assertIn('aire_lab_start_usb',seen);self.assertEqual(self.rt.source,'arduino')
