import tempfile,time,json,uuid,unittest
from datetime import datetime,timezone
from unittest.mock import patch,Mock
from servidor_pc.main import create_app
from servidor_pc.models import Sample
from servidor_pc.cloud import CloudConfig
class UsbCloudLab(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  env=patch.dict('os.environ',{'SFA_CLOUD_CONFIG':self.tmp.name+'/absent.json','GOOGLE_APPLICATION_CREDENTIALS':''});env.start();self.addCleanup(env.stop)
  self.rt=create_app(self.tmp.name,background=False).state.runtime;self.addCleanup(self.rt.store.db.close);self.addCleanup(lambda:self.rt.switch('detenido'))
  self.rt.cloud.config=CloudConfig(url='https://example.supabase.co',publishable_key='sb_publishable_test_only_123456',classroom_id=uuid.uuid4(),gateway_id=uuid.uuid4(),gateway_secret='fixture-only-'+'x'*50)
  self.rt.switch('arduino');self.port=Mock();self.rt.serial=self.port;self.rt.ingest_serial(self.sample())
  self.now=time.time();self.command={'id':str(uuid.uuid4()),'input_source':'usb','temperature':25,'humidity':55,'mq_raw':700,'duration_s':180,'allow_push':True,'allow_takeover':False,'expires_at':datetime.fromtimestamp(self.now+225,timezone.utc).isoformat(),'status':'pendiente'}
 def sample(self,mq=300):return Sample(serial_contract=2,simulated=True,mq_raw=mq,temperature=23.4,humidity=52,warmed_up=True)
 def test_authorized_usb_uses_same_engine_store_and_cloud_outbox(self):
  self.rt.lab.accept(self.command);start=self.rt.lab.started;self.port.close.assert_not_called();self.port.write.assert_called_with(b'REINICIAR\n')
  for sec in range(0,180,2):
   with patch('time.time',return_value=start+sec):
    self.rt.lab.tick();self.rt.ingest_serial(self.sample(300+(sec//60)*100))
  rows=self.rt.store.rows('select * from samples');self.assertLessEqual(len(rows),61);self.assertGreater(len(rows),30)
  self.assertTrue(all(r['source']=='simulacion' for r in rows))
  incidents=self.rt.store.rows('select * from incidents');self.assertEqual(len(incidents),1);self.assertEqual(incidents[0]['severity'],'alerta');self.assertEqual(incidents[0]['lab_run_id'],self.command['id'])
  packets=[json.loads(r['payload']) for r in self.rt.store.rows('select payload from cloud_outbox')]
  self.assertTrue(all(p['lab_run_id']==self.command['id'] and p['observation']['usb_cloud'] for p in packets))
  self.assertTrue(any(p['state']=='aviso' for p in packets));self.assertTrue(any(p['state']=='alerta' for p in packets))
  saved=len(rows);self.rt.lab.tick(start+180);self.assertIsNone(self.rt.lab.command);self.assertIs(self.rt.serial,self.port)
  self.rt.ingest_serial(self.sample());self.assertEqual(len(self.rt.store.rows('select * from samples')),saved);self.assertFalse(self.rt.latest.get('usb_cloud',False))
 def test_no_usb_data_cannot_start_cloud_mode(self):
  self.rt.latest=None;self.rt.lab.accept(self.command);self.assertIsNone(self.rt.lab.command);self.assertEqual(self.rt.cloud.lab_report['status'],'error')
 def test_polling_ticks_do_not_generate_fake_readings_in_usb_mode(self):
  self.rt.lab.accept(self.command)
  for sec in range(0,30,3):self.rt.lab.tick(self.rt.lab.started+sec)
  self.assertEqual(self.rt.store.rows('select count(*) n from samples')[0]['n'],0)
 def test_real_packet_ends_usb_simulation_before_real_ingestion(self):
  self.rt.lab.accept(self.command);self.rt.ingest_serial(Sample(mq_raw=8,dht_ok=False))
  self.assertIsNone(self.rt.lab.command);self.assertEqual(self.rt.latest['source'],'arduino');self.assertIsNone(self.rt.lab_run_id)
