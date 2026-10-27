import tempfile,unittest,uuid
from unittest.mock import Mock,patch
from fastapi.testclient import TestClient
from servidor_pc.main import create_app

class ServiceShutdown(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  env=patch.dict('os.environ',{'SFA_CLOUD_CONFIG':self.tmp.name+'/absent.json','GOOGLE_APPLICATION_CREDENTIALS':''});env.start();self.addCleanup(env.stop)
  self.app=create_app(self.tmp.name,background=False);self.rt=self.app.state.runtime
  self.client=TestClient(self.app);self.client.__enter__();self.addCleanup(lambda:self.client.__exit__(None,None,None))
 def call(self,identity=None):
  return self.client.post('/api/maintenance/shutdown',headers={'Authorization':'Bearer '+self.rt.token},json={'instance_id':identity or self.rt.instance_id})
 def test_requires_local_control_credential(self):
  self.assertEqual(self.client.post('/api/maintenance/shutdown',json={'instance_id':self.rt.instance_id}).status_code,401)
 def test_rejects_wrong_instance(self):
  self.rt.shutdown_callback=Mock();self.assertEqual(self.call(str(uuid.uuid4())).status_code,409);self.rt.shutdown_callback.assert_not_called()
 def test_rejects_unmanaged_runtime(self):
  self.assertEqual(self.call().status_code,409)
 def test_schedules_graceful_shutdown_only_after_response(self):
  callback=Mock();self.rt.shutdown_callback=callback
  with patch('servidor_pc.main.threading.Timer') as timer:
   self.assertEqual(self.call().json(),{'state':'stopping'});timer.assert_called_once_with(.3,callback);timer.return_value.start.assert_called_once();callback.assert_not_called()
 def test_remote_client_cannot_stop_service(self):
  self.rt.shutdown_callback=Mock()
  with TestClient(self.app,client=('192.168.1.10',50000)) as remote:
   self.assertEqual(remote.post('/api/maintenance/shutdown',headers={'Authorization':'Bearer '+self.rt.token},json={'instance_id':self.rt.instance_id}).status_code,403)
