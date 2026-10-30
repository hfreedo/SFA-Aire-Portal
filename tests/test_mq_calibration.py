import tempfile,time,unittest,uuid,json
from unittest.mock import Mock,patch
import httpx
from fastapi.testclient import TestClient
from servidor_pc.main import create_app
from servidor_pc.models import Sample
from servidor_pc.cloud import CloudConfig
from servidor_pc.mq_calibration import MQCalibration
class MQReferenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  env=patch.dict('os.environ',{'SFA_CLOUD_CONFIG':self.tmp.name+'/none.json','GOOGLE_APPLICATION_CREDENTIALS':''});env.start();self.addCleanup(env.stop)
  self.app=create_app(self.tmp.name,False);self.rt=self.app.state.runtime;self.client=TestClient(self.app);self.client.__enter__();self.addCleanup(lambda:self.client.__exit__(None,None,None))
  self.room=str(uuid.uuid4());self.gateway=str(uuid.uuid4());self.allowed=True
  self.rt.cloud.config=CloudConfig(url='https://example.supabase.co',publishable_key='sb_publishable_test_only_123456',classroom_id=self.room,gateway_id=self.gateway,gateway_secret='fixture-only-'+'x'*50)
  self.rt.workspace_transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'classroom_id':self.room,'can_manage_gateways':self.allowed,'gateways':[{'id':self.gateway,'enabled':True}]}))
  self.rt.switch('arduino');self.rt.serial=Mock();self.rt.serial.port='COM7';self.rt.ingest(Sample(mq_raw=85,dht_ok=False,warmed_up=True),'arduino');self.now=time.time()
 def call(self,action,**body):return self.client.post('/api/workspace/local',headers={'Authorization':'Bearer fixture-admin'},json={'classroom_id':self.room,'action':action,**body})
 def test_observed_values_are_provisional_and_do_not_change_rules(self):
  state=self.call('state').json();self.assertEqual(state['calibration']['observed']['usual_min'],70);self.assertEqual(state['calibration']['observed']['peak_max'],315);self.assertIsNone(state['rules']['baseline'])
 def test_capture_rejects_simulation_stale_and_unwarmed_frames(self):
  self.rt.ingest_serial(Sample(serial_contract=2,simulated=True,mq_raw=300,temperature=23,humidity=52,warmed_up=True));self.assertEqual(self.call('calibration_start').status_code,409)
  self.rt.ingest(Sample(mq_raw=85,dht_ok=False,warmed_up=False),'arduino');self.assertEqual(self.call('calibration_start').status_code,409)
  self.rt.ingest(Sample(mq_raw=85,dht_ok=False,warmed_up=True),'arduino',time.time()-20);self.assertEqual(self.call('calibration_start').status_code,409)
 def capture(self):
  with patch('time.time',return_value=self.now):self.assertEqual(self.call('calibration_start',duration_s=60).status_code,200)
  for n in range(30):self.rt.ingest(Sample(mq_raw=80 if n%2==0 else 90,dht_ok=False,warmed_up=True),'arduino',self.now+2*n)
  with patch('time.time',return_value=self.now+61):return self.call('state').json()['calibration']
 def test_capture_median_needs_explicit_apply_and_keeps_temperature_rules(self):
  self.rt.rules.temperature_warning=31
  calibration=self.capture();self.assertEqual(calibration['capture']['result']['baseline'],85);self.assertEqual(calibration['capture']['count'],30);self.assertIsNone(self.rt.rules.baseline)
  self.assertEqual(self.call('calibration_apply',rules_revision=0,conditioned=False).status_code,200);self.assertEqual(self.rt.rules.baseline,85);self.assertFalse(self.rt.rules.conditioned);self.assertEqual(self.rt.rules.temperature_warning,31)
  self.assertEqual(self.rt.mq_calibration.snapshot()['profile']['origin'],'captura')
 def test_provisional_is_not_conditioned_and_restore_is_versioned(self):
  result=self.call('calibration_provisional',rules_revision=0).json();self.assertEqual(result['rules']['baseline'],85);self.assertFalse(result['rules']['conditioned'])
  self.assertEqual(self.call('calibration_provisional',rules_revision=0).status_code,409)
  previous=result['calibration']['history'][0]
  result=self.call('calibration_restore',history_id=previous['id'],rules_revision=1).json();self.assertIsNone(result['rules']['baseline']);self.assertEqual(result['calibration']['profile']['origin'],'restauracion')
 def test_requires_admin_and_rejects_wrong_classroom(self):
  self.allowed=False
  self.assertEqual(self.call('calibration_provisional',rules_revision=0).status_code,403)
  self.assertIsNone(self.rt.rules.baseline)
 def test_insufficient_data_and_cancel_cannot_apply(self):
  self.assertEqual(self.call('calibration_start',duration_s=60).status_code,200)
  with patch('time.time',return_value=time.time()+61):self.assertEqual(self.call('state').json()['calibration']['capture']['status'],'insufficient')
  self.assertEqual(self.call('calibration_apply',rules_revision=0).status_code,409)
  self.assertEqual(self.call('calibration_start',duration_s=60).status_code,200);self.rt.switch('detenido');self.assertEqual(self.rt.mq_calibration.snapshot()['capture']['status'],'cancelled')
 def test_history_persists_locally_and_is_scoped_to_classroom(self):
  self.call('calibration_provisional',rules_revision=0);self.rt.mq_calibration=MQCalibration(self.rt)
  self.assertEqual(self.rt.mq_calibration.snapshot()['profile']['baseline'],85)
  self.rt.cloud.config=self.rt.cloud.config.model_copy(update={'classroom_id':uuid.uuid4()});self.assertIsNone(self.rt.mq_calibration.snapshot()['profile']);self.assertEqual(self.rt.mq_calibration.snapshot()['history'],[])
