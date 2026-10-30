import tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from servidor_pc.main import create_app
from servidor_pc.models import Sample
from servidor_pc.workspace import connect_serial
class SerialRecovery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  env=patch.dict('os.environ',{'SFA_CLOUD_CONFIG':self.tmp.name+'/none.json','GOOGLE_APPLICATION_CREDENTIALS':''});env.start();self.addCleanup(env.stop)
  self.rt=create_app(self.tmp.name,background=False).state.runtime
  self.addCleanup(self.rt.store.db.close)
  self.addCleanup(lambda:self.rt.switch('detenido'))
  self.info=SimpleNamespace(device='COM7',vid=0x1a86,pid=0x7523,serial_number=None)
 def configure(self,port):
  with patch('serial.tools.list_ports.comports',return_value=[self.info]),patch('serial.Serial',return_value=port):connect_serial(self.rt,'COM7')
 def port(self):
  port=Mock();port.port='COM7';port.in_waiting=0;return port
 def test_disconnect_even_close_failure_does_not_kill_reader_and_recovers(self):
  broken=self.port();self.configure(broken)
  type(broken).in_waiting=property(lambda _:(_ for _ in ()).throw(OSError('unplugged')))
  broken.close.side_effect=OSError('gone');self.rt.serial_tick()
  self.assertIsNone(self.rt.serial);self.assertEqual(self.rt.serial_state,'reconectando')
  self.rt.serial_retry_at=0;recovered=self.port()
  with patch('serial.tools.list_ports.comports',return_value=[self.info]),patch('serial.Serial',return_value=recovered):self.rt.serial_tick()
  self.assertIs(self.rt.serial,recovered);recovered.write.assert_called_with(b'MONITOR\n')
  self.assertIsNone(self.rt.latest) # Reconnection is not a fabricated sample.
 def test_no_other_port_or_changed_hardware_is_opened(self):
  self.configure(self.port());self.rt.serial=None
  for info in [SimpleNamespace(device='COM8',vid=0x1a86,pid=0x7523,serial_number=None),SimpleNamespace(device='COM7',vid=999,pid=1,serial_number=None)]:
   self.rt.serial_retry_at=0
   with patch('serial.tools.list_ports.comports',return_value=[info]),patch('serial.Serial') as opened:self.rt.serial_tick();opened.assert_not_called()
 def test_retry_is_bounded_and_stop_disables_it(self):
  self.configure(self.port());self.rt.serial=None;self.rt.serial_retry_at=time.time()+4
  with patch('serial.tools.list_ports.comports') as scan:self.rt.serial_tick();scan.assert_not_called()
  self.rt.switch('detenido');self.assertIsNone(self.rt.serial_target)
  with patch('serial.Serial') as opened:self.rt.serial_tick();opened.assert_not_called()
 def test_reset_with_open_port_resends_monitor_when_data_stops(self):
  port=self.port();self.configure(port)
  self.rt.ingest(Sample(mq_raw=6,dht_ok=False),'arduino',time.time()-20)
  self.rt.last_monitor=time.time()-5;port.write.reset_mock();self.rt.serial_tick()
  port.write.assert_called_once_with(b'MONITOR\n');self.assertEqual(self.rt.serial_state,'esperando_arduino')
 def test_fragmented_frame_survives_read_timeout(self):
  chunks=[b'{"mq_raw":6,"dht_ok":',b'false}\n']
  class Port:
   port='COM7'
   @property
   def in_waiting(self):return len(chunks)
   def readline(self,n):return chunks.pop(0)
   def write(self,data):pass
   def close(self):pass
  self.configure(Port());self.rt.serial_tick()
  self.assertEqual(self.rt.latest['mq_raw'],6);self.assertFalse(self.rt.latest['dht_ok'])
 def test_noise_does_not_skip_following_valid_sample(self):
  port=self.port();self.configure(port);port.in_waiting=1
  frames=iter([b'{invalid}\n',b'{"mq_raw":8,"dht_ok":false}\n'])
  def read(_):
   line=next(frames)
   if b'8' in line:port.in_waiting=0
   return line
  port.readline.side_effect=read;self.rt.serial_tick();self.assertEqual(self.rt.latest['mq_raw'],8)
