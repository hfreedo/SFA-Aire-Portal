import tempfile,time,unittest
from unittest.mock import patch,Mock
from servidor_pc.main import create_app
from servidor_pc.models import Sample
from servidor_pc.cloud import CloudConfig
class UsbSimulation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  env=patch.dict('os.environ',{'SFA_CLOUD_CONFIG':self.tmp.name+'/none.json','GOOGLE_APPLICATION_CREDENTIALS':''});env.start();self.addCleanup(env.stop)
  self.rt=create_app(self.tmp.name,background=False).state.runtime
  self.addCleanup(self.rt.store.db.close);self.addCleanup(lambda:self.rt.switch('detenido'))
  self.rt.switch('arduino')
 def sample(self,mq=300):return Sample(serial_contract=2,simulated=True,mq_raw=mq,temperature=23.4,humidity=52,dht_ok=True,warmed_up=True)
 def test_usb_simulation_is_marked_and_never_persisted_or_queued(self):
  self.rt.cloud.enqueue=Mock(side_effect=AssertionError('Simulation attempted cloud enqueue'))
  for mq in [300,400,500,600,700]:self.rt.ingest_serial(self.sample(mq))
  state=self.rt.snapshot();self.assertEqual(state['source'],'simulacion');self.assertTrue(state['latest']['usb_simulation'])
  self.assertEqual(self.rt.source,'arduino') # Serial reader remains active.
  for table in ['samples','incidents','deliveries','cloud_outbox']:self.assertEqual(self.rt.store.rows('select count(*) as n from '+table)[0]['n'],0)
  self.rt.cloud.enqueue.assert_not_called()
 def test_simulation_cannot_use_regular_cloud_ingestion(self):
  with self.assertRaises(ValueError):self.rt.ingest(self.sample(),'arduino')
 def test_real_packet_after_preview_keeps_real_contract(self):
  self.rt.ingest_serial(self.sample());self.rt.ingest_serial(Sample(mq_raw=6,dht_ok=False))
  state=self.rt.snapshot();self.assertEqual(state['source'],'arduino');self.assertFalse(state['latest'].get('usb_simulation',False));self.assertNotIn('simulated',state['latest'])
  self.assertEqual(self.rt.store.rows('select count(*) as n from samples')[0]['n'],1)
 def test_simulation_requires_v2_and_boolean_marker(self):
  with self.assertRaises(ValueError):Sample(simulated=True,mq_raw=300,dht_ok=False)
  with self.assertRaises(ValueError):Sample(serial_contract=2,simulated='false',mq_raw=300,dht_ok=False)
 def test_stopping_clears_preview(self):
  self.rt.ingest_serial(self.sample());self.rt.switch('detenido');self.assertIsNone(self.rt.latest);self.assertEqual(self.rt.snapshot()['source'],'detenido')
 def test_lost_simulation_still_expires_without_fabricated_timestamp(self):
  self.rt.ingest_serial(self.sample());received=self.rt.latest['received'];self.rt.last_valid=time.time()-20
  self.assertEqual(self.rt.snapshot()['state'],'sin_datos');self.assertEqual(self.rt.latest['received'],received)

 def test_serial_handshake_enables_preview_without_assuming_real_data(self):
  port=Mock();port.in_waiting=1
  def read(_):
   port.in_waiting=0
   return b'# SFA Aire SIMULACION USB v2. Firmware temporal sin sensores.\n'
  port.readline.side_effect=read;self.rt.serial=port;self.rt.last_monitor=time.time()
  self.rt.serial_tick()
  self.assertEqual([c.args[0] for c in port.write.call_args_list],[b'SIMULACION_USB_V2\n',b'MONITOR\n'])
  self.assertIsNone(self.rt.latest)
