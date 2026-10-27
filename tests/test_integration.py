"""Pruebas del recorrido serial/reglas/SQLite/API/cola FCM con proveedor simulado."""
import json
import tempfile
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from servidor_pc.main import create_app
from servidor_pc.models import Rules, Sample
from servidor_pc.engine import Engine


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        environment = patch.dict('os.environ', {'SFA_CLOUD_CONFIG': self.tmp.name + '/no-cloud-config.json', 'GOOGLE_APPLICATION_CREDENTIALS': ''})
        environment.start()
        self.addCleanup(environment.stop)
        self.app = create_app(self.tmp.name, background=False)
        self.rt = self.app.state.runtime
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.headers = {'Authorization': 'Bearer ' + self.rt.token}
        self.now = time.time()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tmp.cleanup()

    def call(self, method, path, body=None):
        return self.client.request(method, '/api' + path, headers=self.headers, json=body)

    def sample(self, mq=560, **kwargs):
        return Sample(mq_raw=mq, temperature=25, humidity=55, warmed_up=True, **kwargs)

    def simulate_alert(self):
        self.call('POST', '/simulation', {'scenario': 'alerta'})
        for n in range(0, 16, 3):
            self.rt.ingest(self.sample(), 'simulacion', self.now + n)
        return self.rt.snapshot()['incidents'][0]['id']

    def device(self, simulations=True):
        return self.call('POST', '/devices', {'installation_id': 'test-phone-123',
            'token': 'fake-fcm-token-not-a-real-recipient', 'accept_simulations': simulations}).json()

    def test_authentication_and_no_token_disclosure(self):
        self.assertEqual(self.client.get('/api/state').status_code, 401)
        self.device()
        payload = self.call('GET', '/state').text
        self.assertNotIn('fake-fcm-token', payload)
        self.assertNotIn(self.rt.token, payload)

    def test_persistence_dedup_push_and_receipts(self):
        self.device()
        incident = self.simulate_alert()
        self.assertEqual(len(self.rt.snapshot()['incidents']), 1)
        for n in range(18, 36, 3):
            self.rt.ingest(self.sample(), 'simulacion', self.now + n)
        self.assertEqual(len(self.rt.snapshot()['deliveries']), 1)
        # Hacer vencida la fecha de ejecución simulada, manteniendo una cola reciente.
        with self.rt.store.transaction() as db:
            db.execute('UPDATE deliveries SET next_try=?', (time.time()-1,))
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append((token, data)) or 'fcm/fake-id')
        job = self.rt.snapshot()['deliveries'][0]
        self.assertEqual(job['status'], 'aceptado_fcm')
        self.assertEqual(sent[0][1]['incident_id'], incident)
        self.assertIn('SIMULACIÓN', sent[0][1]['title'])
        response = self.call('POST', f"/deliveries/{job['id']}/receipt", {'installation_id':'test-phone-123','action':'abierto'})
        self.assertEqual(response.status_code, 200)
        job = self.rt.snapshot()['deliveries'][0]
        self.assertIsNotNone(job['received'])
        self.assertIsNotNone(job['opened'])

    def test_simulations_cannot_notify_real_only_device(self):
        self.device(False)
        self.simulate_alert()
        self.assertEqual(self.rt.snapshot()['deliveries'], [])

    def test_faults_warmup_and_missing_baseline_do_not_open_incident(self):
        self.rt.switch('arduino')
        for n in range(0, 30, 3):
            self.rt.ingest(self.sample(), 'arduino', self.now + n)
        self.assertEqual(self.rt.snapshot()['incidents'], [])
        self.assertEqual(self.rt.latest['state'], 'sin_calibrar')
        self.rt.rules = Rules(baseline=300, conditioned=True)
        self.rt.ingest(self.sample(dht_ok=False), 'arduino', self.now+30)
        self.assertEqual(self.rt.latest['state'], 'fallo_sensor')
        self.rt.ingest(Sample(mq_raw=560,temperature=25,humidity=55), 'arduino', self.now+33)
        self.assertEqual(self.rt.latest['state'], 'calentando')

    def test_stale_source_and_cross_source_rejection(self):
        self.rt.switch('arduino')
        self.rt.ingest(self.sample(300), 'arduino', self.now - 20)
        self.assertEqual(self.rt.snapshot()['state'], 'sin_datos')
        with self.assertRaises(ValueError):
            self.rt.ingest(self.sample(), 'simulacion')

    def test_attention_is_optional_note_and_independent_of_environment(self):
        self.device()
        incident = self.simulate_alert()
        before = self.rt.snapshot()['state']
        self.assertEqual(self.call('POST', f'/incidents/{incident}/attention', {'action':'resolver'}).status_code,200)
        self.assertEqual(self.rt.snapshot()['incidents'][0]['status'], 'resuelto')
        self.assertEqual(self.rt.snapshot()['state'], before)
        self.assertIn('No confirma normalización', self.rt.snapshot()['incidents'][0]['note'])
        self.assertEqual(self.rt.snapshot()['deliveries'][0]['status'], 'pendiente')
        with self.rt.store.transaction() as db:
            db.execute('UPDATE deliveries SET next_try=?',(time.time()-1,))
        sent=[]
        self.rt.push.process_once(lambda token,data:sent.append(data) or 'fcm/mock')
        self.assertEqual(len(sent),1)

    def test_recovery_does_not_automatically_close_notice(self):
        incident = self.simulate_alert()
        for n in range(18, 45, 3):
            self.rt.ingest(self.sample(300), 'simulacion', self.now + n)
        self.assertEqual(self.rt.snapshot()['incidents'][0]['status'], 'pendiente')
        self.assertEqual(self.call('POST', f'/incidents/{incident}/attention', {'action':'resolver','note':'x'}).status_code,200)

    def test_retry_is_persisted_without_false_delivery(self):
        self.device(); self.simulate_alert()
        with self.rt.store.transaction() as db:
            db.execute('UPDATE deliveries SET next_try=?', (time.time()-1,))
        def unavailable(token,data):
            raise ConnectionError('not logged')
        self.rt.push.process_once(unavailable)
        job = self.rt.snapshot()['deliveries'][0]
        self.assertEqual(job['status'], 'reintento')
        self.assertEqual(job['attempts'],1)
        self.assertEqual(job['error'],'ConnectionError')
        self.assertIsNone(job['received'])

    def test_real_sdk_message_contract_without_network(self):
        from firebase_admin import messaging
        with patch('firebase_admin.credentials.Certificate'), patch('firebase_admin.initialize_app') as initialize, patch('firebase_admin.messaging.send') as send:
            send.return_value='projects/test/messages/example'
            result=self.rt.push.send('fake-registration-token', {'delivery_id':'test','title':'SIMULACIÓN'})
            message=send.call_args.args[0]
            self.assertIsInstance(message,messaging.Message)
            self.assertEqual(message.android.priority,'high')
            self.assertEqual(message.android.ttl.total_seconds(),300)
            self.assertIsNone(message.notification)
            self.assertEqual(result,'projects/test/messages/example')
            initialize.assert_called_once()

    def test_websocket_requires_auth_and_streams_state(self):
        with self.client.websocket_connect('/ws') as ws:
            ws.send_json({'token':self.rt.token})
            self.assertEqual(ws.receive_json()['source'],'detenido')

    def test_rules_persist_and_validate(self):
        rules=Rules(baseline=310,conditioned=True).model_dump()
        self.assertEqual(self.call('PUT','/rules',rules).status_code,200)
        self.assertEqual(self.rt.store.setting('rules')['baseline'],310)
        rules['alert_ratio']=1.2
        self.assertEqual(self.call('PUT','/rules',rules).status_code,422)

    def test_serial_json_contract_and_partial_failure(self):
        class FakeSerial:
            in_waiting=1
            def readline(self,size):
                self.in_waiting=0
                return b'{"device_id":"aula-01","mq_raw":350,"temperature":null,"humidity":null,"dht_ok":false,"warmed_up":true}\n'
            def write(self,data): pass
            def close(self): pass
        self.rt.switch('arduino'); self.rt.serial=FakeSerial()
        self.rt.serial_tick()
        self.assertEqual(self.rt.latest['state'],'fallo_sensor')
        self.assertEqual(self.rt.latest['mq_raw'],350)

    def test_restart_preserves_incident_and_identity(self):
        incident=self.simulate_alert()
        second=create_app(self.tmp.name,False)
        try:
            self.assertEqual(second.state.runtime.token,self.rt.token)
            self.assertEqual(second.state.runtime.snapshot()['incidents'][0]['id'],incident)
            self.assertEqual(second.state.runtime.source,'detenido')
        finally: second.state.runtime.store.db.close()

    def test_hysteresis_and_gap_reset_persistence(self):
        engine=Engine(); rules=Rules(baseline=300,conditioned=True)
        for n in (0,3,6,30,33,36): engine.evaluate(self.sample(),rules,n)
        self.assertEqual(engine.level,'normal')
        engine.evaluate(self.sample(),rules,42)
        self.assertEqual(engine.level,'alerta')
        for n in range(45,81,3): engine.evaluate(self.sample(460),rules,n)
        self.assertEqual(engine.level,'alerta')


if __name__=='__main__':
    unittest.main(verbosity=2)
