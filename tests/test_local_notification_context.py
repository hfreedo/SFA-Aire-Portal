"""Contrato LAN v2 con FCM simulado: identidad, persistencia y cambios de registro."""
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient
from servidor_pc.main import create_app
from servidor_pc.models import Sample
from servidor_pc.store import Store


class LocalNotificationContext(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        environment = patch.dict('os.environ', {'SFA_CLOUD_CONFIG': self.tmp.name + '/absent.json',
                                               'GOOGLE_APPLICATION_CREDENTIALS': ''})
        environment.start()
        self.addCleanup(environment.stop)
        self.app = create_app(self.tmp.name, background=False)
        self.rt = self.app.state.runtime
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.headers = {'Authorization': 'Bearer ' + self.rt.token}
        self.binding = str(uuid.uuid4())
        self.receiver = self.rt.store.receiver_id
        self.phone = 'fixture-phone-123'
        self.token = 'fake-fcm-token-never-send-123456'

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tmp.cleanup()

    def call(self, method, path, body=None):
        return self.client.request(method, '/api' + path, headers=self.headers, json=body)

    def register(self, binding=None, token=None, phone=None, **extra):
        body = {'installation_id': phone or self.phone, 'token': token or self.token,
                'accept_simulations': True}
        if binding is not None:
            body.update(notification_binding=binding, receiver_id=self.receiver)
        body.update(extra)
        return self.call('POST', '/devices', body)

    def alert(self):
        self.rt.switch('simulacion')
        now = time.time()
        for tick in range(0, 16, 3):
            self.rt.ingest(Sample(mq_raw=560, temperature=25, humidity=55, warmed_up=True),
                           'simulacion', now + tick)
        with self.rt.store.transaction() as db:
            db.execute('UPDATE deliveries SET next_try=?', (time.time() - 1,))
        return self.rt.store.rows('SELECT * FROM deliveries ORDER BY rowid DESC')[0]

    def delivery(self, identity):
        return self.rt.store.rows('SELECT * FROM deliveries WHERE id=?', (identity,))[0]

    def receipt(self, identity, binding=None, receiver=None):
        body = {'installation_id': self.phone, 'action': 'abierto'}
        if binding is not None:
            body['notification_binding'] = binding
        if receiver is not None:
            body['receiver_id'] = receiver
        return self.call('POST', f'/deliveries/{identity}/receipt', body)

    def test_receiver_identity_is_authenticated_durable_and_independent(self):
        self.assertEqual(self.client.get('/api/state').status_code, 401)
        state = self.call('GET', '/state').json()
        self.assertEqual(str(uuid.UUID(state['receiver_id'])), self.receiver)
        self.assertNotIn('receiver_id', self.client.get('/health').json())
        self.assertNotIn('receiver_id', self.client.get('/api/public-config').json())
        reopened = Store(Path(self.tmp.name) / 'aire.sqlite3')
        different = Store(Path(self.tmp.name) / 'different.sqlite3')
        try:
            self.assertEqual(reopened.receiver_id, self.receiver)
            self.assertNotEqual(different.receiver_id, self.receiver)
        finally:
            reopened.db.close()
            different.db.close()

    def test_legacy_sqlite_migrates_without_rebinding_history(self):
        path = Path(self.tmp.name) / 'legacy.sqlite3'
        legacy = sqlite3.connect(path)
        legacy.executescript('''
            CREATE TABLE devices(id TEXT PRIMARY KEY,token TEXT UNIQUE,name TEXT,accept_simulations INTEGER,updated REAL);
            CREATE TABLE deliveries(id TEXT PRIMARY KEY,incident_id TEXT,device_id TEXT,severity TEXT,status TEXT,
              attempts INTEGER DEFAULT 0,next_try REAL,provider_id TEXT,error TEXT,received REAL,opened REAL,
              UNIQUE(incident_id,device_id,severity));
            INSERT INTO devices VALUES('old-phone','fake-old-token','Anterior',1,12);
            INSERT INTO deliveries(id,incident_id,device_id,severity,status,next_try) VALUES('old-delivery','old-incident','old-phone','alerta','pendiente',12);
        ''')
        legacy.close()
        store = Store(path)
        try:
            self.assertEqual(store.rows('SELECT notification_binding FROM devices'), [{'notification_binding': None}])
            job = store.rows('SELECT * FROM deliveries')[0]
            self.assertEqual(job['id'], 'old-delivery')
            self.assertIsNone(job['notification_binding'])
            self.assertEqual(job['next_try'], 12)
        finally:
            store.db.close()

    def test_registration_requires_auth_valid_binding_and_matching_handshake(self):
        self.assertEqual(self.register(self.binding).status_code, 200)
        old = self.rt.store.rows('SELECT * FROM devices')[0]
        self.assertEqual(self.client.post('/api/devices', json={'installation_id': self.phone, 'token': self.token}).status_code, 401)
        self.assertEqual(self.register(str(uuid.uuid4()), receiver_id=str(uuid.uuid4())).status_code, 409)
        self.assertEqual(self.register(str(uuid.uuid4()), receiver_id=None).status_code, 409)
        self.assertEqual(self.register('not-a-uuid').status_code, 422)
        self.assertEqual(self.rt.store.rows('SELECT * FROM devices')[0], old)

    def test_v2_delivery_snapshots_binding_and_sends_private_generic_contract(self):
        self.assertEqual(self.register(self.binding).status_code, 200)
        job = self.alert()
        self.assertEqual(job['notification_binding'], self.binding)
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append((token, data)) or 'fcm/mock')
        self.assertEqual(len(sent), 1)
        payload = sent[0][1]
        self.assertEqual(payload['local_contract'], '2')
        self.assertEqual(payload['channel'], 'local')
        self.assertEqual(payload['receiver_id'], self.receiver)
        self.assertEqual(payload['notification_binding'], self.binding)
        self.assertTrue(all(isinstance(value, str) for value in payload.values()))
        self.assertNotIn(self.token, json.dumps(payload))
        self.assertNotIn(self.rt.token, json.dumps(payload))
        self.assertEqual(self.delivery(job['id'])['status'], 'aceptado_fcm')

    def test_binding_change_cancels_old_work_without_reassigning_it(self):
        self.register(self.binding)
        job = self.alert()
        replacement = str(uuid.uuid4())
        self.assertEqual(self.register(replacement).status_code, 200)
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append(data) or 'fcm/mock')
        self.assertEqual(sent, [])
        old = self.delivery(job['id'])
        self.assertEqual(old['status'], 'cancelado')
        self.assertEqual(old['notification_binding'], self.binding)
        self.assertEqual(old['attempts'], 0)
        self.assertEqual(self.receipt(job['id'], self.binding, self.receiver).status_code, 409)
        self.assertIsNone(self.delivery(job['id'])['received'])

    def test_processor_rechecks_binding_even_if_registration_did_not_cancel(self):
        self.register(self.binding)
        job = self.alert()
        with self.rt.store.transaction() as db:
            db.execute('UPDATE devices SET notification_binding=? WHERE id=?', (str(uuid.uuid4()), self.phone))
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append(data) or 'fcm/mock')
        self.assertEqual(sent, [])
        self.assertEqual(self.delivery(job['id'])['status'], 'cancelado')

    def test_rotation_of_token_keeps_binding_but_uses_current_token(self):
        self.register(self.binding)
        job = self.alert()
        rotated = 'fake-rotated-token-never-send-98765'
        self.register(self.binding, token=rotated)
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append((token, data)) or 'fcm/mock')
        self.assertEqual(sent[0][0], rotated)
        self.assertEqual(sent[0][1]['notification_binding'], self.binding)
        self.assertEqual(self.delivery(job['id'])['attempts'], 1)

    def test_token_transfer_cancels_old_installation(self):
        self.register(self.binding)
        job = self.alert()
        self.register(str(uuid.uuid4()), phone='replacement-phone-456')
        self.assertEqual(len(self.rt.store.rows('SELECT id FROM devices')), 1)
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append(data) or 'fcm/mock')
        self.assertEqual(sent, [])
        self.assertEqual(self.delivery(job['id'])['status'], 'cancelado')

    def test_v2_receipt_requires_delivery_and_current_registration_context(self):
        self.register(self.binding)
        job = self.alert()
        for binding, receiver in [(None, None), (self.binding, None), (None, self.receiver),
                                  (str(uuid.uuid4()), self.receiver), (self.binding, str(uuid.uuid4()))]:
            self.assertEqual(self.receipt(job['id'], binding, receiver).status_code, 409)
            self.assertIsNone(self.delivery(job['id'])['received'])
        self.assertEqual(self.receipt(job['id'], self.binding, self.receiver).status_code, 200)
        delivered = self.delivery(job['id'])
        self.assertEqual(delivered['status'], 'recibido_app')
        self.assertIsNotNone(delivered['opened'])
        self.assertIsNotNone(delivered['received'])

    def test_v1_payload_and_receipt_are_preserved_without_invented_binding(self):
        self.assertEqual(self.register().status_code, 200)
        job = self.alert()
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append(data) or 'fcm/mock')
        self.assertEqual(sent[0]['receiver_id'], self.receiver)
        self.assertNotIn('local_contract', sent[0])
        self.assertNotIn('notification_binding', sent[0])
        self.assertIsNone(job['notification_binding'])
        self.assertEqual(self.receipt(job['id']).status_code, 200)

    def test_upgrade_does_not_relabel_legacy_pending_delivery(self):
        self.register()
        job = self.alert()
        self.register(self.binding)
        sent = []
        self.rt.push.process_once(lambda token, data: sent.append(data) or 'fcm/mock')
        self.assertEqual(sent, [])
        self.assertIsNone(self.delivery(job['id'])['notification_binding'])
        self.assertEqual(self.delivery(job['id'])['status'], 'cancelado')

    def test_successful_inflight_send_does_not_reactivate_replaced_binding(self):
        self.register(self.binding)
        job = self.alert()
        def accepted_old_attempt(token, data):
            self.assertEqual(data['notification_binding'], self.binding)
            self.assertEqual(self.register(str(uuid.uuid4())).status_code, 200)
            return 'fcm/mock-accepted-before-cancel'
        self.rt.push.process_once(accepted_old_attempt)
        outcome = self.delivery(job['id'])
        self.assertEqual(outcome['status'], 'cancelado')
        self.assertEqual(outcome['attempts'], 1)
        self.assertEqual(outcome['provider_id'], 'fcm/mock-accepted-before-cancel')
        self.rt.push.process_once(lambda *_: self.fail('Retired delivery retried'))

    def test_failed_inflight_send_does_not_reactivate_unregistered_phone(self):
        self.register(self.binding)
        job = self.alert()
        def failed_old_attempt(token, data):
            self.assertEqual(self.call('DELETE', f'/devices/{self.phone}').status_code, 200)
            raise ConnectionError('mock provider failure')
        self.rt.push.process_once(failed_old_attempt)
        outcome = self.delivery(job['id'])
        self.assertEqual(outcome['status'], 'cancelado')
        self.assertEqual(outcome['error'], 'ConnectionError')
        self.assertEqual(outcome['attempts'], 1)

    def test_receipt_during_send_remains_received_after_provider_success(self):
        self.register(self.binding)
        job = self.alert()
        def opened_before_provider_returns(token, data):
            self.assertEqual(self.receipt(job['id'], self.binding, self.receiver).status_code, 200)
            return 'fcm/mock'
        self.rt.push.process_once(opened_before_provider_returns)
        self.assertEqual(self.delivery(job['id'])['status'], 'recibido_app')
        self.assertIsNotNone(self.delivery(job['id'])['opened'])

    def test_late_receipt_records_evidence_without_reopening_cancelled_status(self):
        self.register(self.binding)
        job = self.alert()
        with self.rt.store.transaction() as db:
            db.execute("UPDATE deliveries SET status='cancelado' WHERE id=?", (job['id'],))
        self.assertEqual(self.receipt(job['id'], self.binding, self.receiver).status_code, 200)
        outcome = self.delivery(job['id'])
        self.assertEqual(outcome['status'], 'cancelado')
        self.assertIsNotNone(outcome['received'])

    def test_process_is_not_reentered_and_simulation_consent_is_rechecked(self):
        self.register(self.binding)
        job = self.alert()
        calls = []
        def one_attempt(token, data):
            calls.append(data)
            self.rt.push.process_once(lambda *_: self.fail('Nested processor sent twice'))
            return 'fcm/mock'
        self.rt.push.process_once(one_attempt)
        self.assertEqual(len(calls), 1)
        with self.rt.store.transaction() as db:
            db.execute("UPDATE deliveries SET status='pendiente' WHERE id=?", (job['id'],))
        self.register(self.binding, accept_simulations=False)
        self.rt.push.process_once(lambda *_: self.fail('Revoked simulation consent sent'))
        self.assertEqual(self.delivery(job['id'])['status'], 'cancelado')
