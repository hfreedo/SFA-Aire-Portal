import json,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from servidor_pc.main import create_app
from servidor_pc.cloud import PublicConnection,CloudBridge

class FirstPC(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  env=patch.dict('os.environ',{'SFA_CLOUD_CONFIG':self.tmp.name+'/secrets/supabase-pc.json','SFA_PUBLIC_CONFIG':self.tmp.name+'/public.json','GOOGLE_APPLICATION_CREDENTIALS':''});env.start();self.addCleanup(env.stop)
  self.app=create_app(self.tmp.name,background=False);self.rt=self.app.state.runtime
  self.rt.public_connection=PublicConnection(url='https://example.supabase.co',publishable_key='sb_publishable_fixture_only_123')
  self.room=str(uuid.uuid4());self.gateway=str(uuid.uuid4());self.allowed=True;self.fail=False;self.requests=[]
  def transport(req):
   body=json.loads(req.content);self.requests.append((req.url.path,body))
   if req.url.path.endswith('aire_admin_capabilities'):return httpx.Response(200,json={'classroom_id':self.room,'can_manage_gateways':self.allowed,'gateways':[{'id':self.gateway,'enabled':True}] if self.rt.cloud.config else []})
   if req.url.path.endswith('aire_enroll_pc'):return httpx.Response(503,json={'message':'offline'}) if self.fail else httpx.Response(200,json={'classroom_id':self.room,'gateway_id':self.gateway})
   raise AssertionError('Unexpected endpoint')
  self.rt.workspace_transport=httpx.MockTransport(transport)
  self.client=TestClient(self.app);self.client.__enter__();self.addCleanup(lambda:self.client.__exit__(None,None,None))
 def call(self,action,client=None):return (client or self.client).post('/api/workspace/local',headers={'Authorization':'Bearer actor-fixture'},json={'classroom_id':self.room,'action':action})
 def test_public_connection_without_gateway_and_role_gate(self):
  self.assertTrue(self.client.get('/api/public-config').json()['configured']);self.assertIsNone(self.rt.cloud.config)
  self.assertEqual(self.call('assignment').json()['current_classroom_id'],None)
  self.assertEqual(self.call('ports').status_code,409)
  self.allowed=False;self.assertEqual(self.call('assign').status_code,403)
  self.assertFalse(self.rt.cloud.path.exists())
 def test_enrollment_is_private_and_does_not_reassign_local_history(self):
  with self.rt.store.transaction() as db:db.execute("insert into incidents(id,source,severity,opened,updated) values('old-local','arduino','aviso',0,0)")
  response=self.call('assign');self.assertEqual(response.status_code,200)
  cfg=self.rt.cloud.config;self.assertEqual(str(cfg.gateway_id),self.gateway);self.assertNotIn(cfg.gateway_secret,response.text)
  self.assertNotIn('actor-fixture',self.rt.cloud.path.read_text());self.assertEqual(self.call('state').status_code,200);self.assertEqual(self.call('assign').status_code,200)
  self.assertEqual(sum(p.endswith('aire_enroll_pc') for p,b in self.requests),1)
  restarted=CloudBridge(self.rt.store,self.rt.cloud.path,self.rt.push);self.assertEqual(str(restarted.config.gateway_id),self.gateway)
  old=self.rt.store.rows("select cloud_gateway_id from incidents where id='old-local'")[0]['cloud_gateway_id'];self.assertTrue(old.startswith('local:'))
 def test_retry_reuses_secret_without_shipping_existing_credentials(self):
  self.fail=True;self.assertEqual(self.call('assign').status_code,503);self.assertIsNone(self.rt.cloud.config)
  first=self.requests[-1][1]['p_secret'];self.fail=False;self.assertEqual(self.call('assign').status_code,200);self.assertEqual(self.requests[-1][1]['p_secret'],first)
 def test_rejects_lan_and_active_acquisition(self):
  with TestClient(self.app,client=('192.168.1.55',45000)) as client:self.assertEqual(self.call('assign',client).status_code,403)
  self.rt.switch('simulacion');self.assertEqual(self.call('assign').status_code,409);self.assertIsNone(self.rt.cloud.config)
 def test_private_keys_cannot_be_public_configuration(self):
  for key in ['sb_secret_'+'forbidden_fixture_123456','not-a-publishable-key']:
   with self.assertRaises(ValueError):PublicConnection(url='https://example.supabase.co',publishable_key=key)
