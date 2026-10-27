import base64
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

import httpx
from fastapi.testclient import TestClient
from servidor_pc.cloud import CloudBridge, CloudConfig
from servidor_pc.main import create_app
from servidor_pc.models import Sample


class CloudIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        environment = patch.dict('os.environ', {'SFA_CLOUD_CONFIG': self.tmp.name + '/no-cloud-config.json', 'GOOGLE_APPLICATION_CREDENTIALS': ''})
        environment.start()
        self.addCleanup(environment.stop)
        self.app=create_app(self.tmp.name,background=False)
        self.rt=self.app.state.runtime
        self.client=TestClient(self.app);self.client.__enter__()
        self.headers={'Authorization':'Bearer '+self.rt.token}
        self.config={'url':'https://example.supabase.co','publishable_key':'sb_publishable_only_test_123456789',
            'classroom_id':str(uuid.uuid4()),'gateway_id':str(uuid.uuid4()),'gateway_secret':'test-secret-'+('x'*60)}
        self.rt.cloud.config=CloudConfig(**self.config)
        self.calls=[]
        self.sample_time=time.time()-120

    def tearDown(self):
        self.client.__exit__(None,None,None);self.tmp.cleanup()

    def handler(self,request):
        payload=json.loads(request.content)
        name=request.url.path.split('/')[-1]
        self.calls.append((name,payload))
        self.assertEqual(request.headers['apikey'],self.config['publishable_key'])
        self.assertNotIn('authorization',request.headers) # La key publishable no es JWT.
        if name=='aire_gateway_poll':
            return httpx.Response(200,json={'classroom_id':self.config['classroom_id'],'incidents':[]})
        if name=='aire_ingest':
            return httpx.Response(200,json={'accepted_seq':payload['p_packet']['seq'],'incidents':[]})
        if name=='aire_claim_push':
            return httpx.Response(200,json={'jobs':[]})
        return httpx.Response(200,json=None)

    def ingest(self,mq=560):
        self.rt.switch('simulacion')
        self.rt.ingest(Sample(mq_raw=mq,temperature=25,humidity=55,warmed_up=True),'simulacion',self.sample_time)
        self.sample_time+=61

    def test_durable_outbox_http_contract_and_ack(self):
        self.ingest()
        self.assertEqual(self.rt.cloud.snapshot()['pending'],1)
        self.rt.cloud.transport=httpx.MockTransport(self.handler)
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.cloud.snapshot()['pending'],0)
        self.assertEqual(self.rt.cloud.state,'conectado')
        packet=[p['p_packet'] for name,p in self.calls if name=='aire_ingest'][0]
        self.assertEqual(packet['seq'],1)
        self.assertEqual(packet['source'],'simulacion')
        self.assertEqual(packet['observation']['mq_raw'],560)
        self.assertNotIn(self.rt.token,json.dumps(packet))

    def test_public_defaults_expose_only_client_configuration(self):
        response=self.client.get('/api/public-config')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),{'configured':True,'url':self.config['url'],'key':self.config['publishable_key']})
        self.assertNotIn(self.config['gateway_secret'],response.text)
        self.assertNotIn(self.rt.token,response.text)

    def test_failed_upload_retains_order_and_does_not_drop_data(self):
        self.ingest();self.ingest(300)
        def offline(request): raise httpx.ConnectError('offline')
        self.rt.cloud.transport=httpx.MockTransport(offline)
        self.rt.cloud.sync_once(force=True)
        rows=self.rt.store.rows('SELECT * FROM cloud_outbox ORDER BY seq')
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['attempts'],1)
        self.rt.cloud.transport=httpx.MockTransport(self.handler)
        self.rt.cloud.sync_once(force=True)
        self.assertEqual([name for name,_ in self.calls],['aire_gateway_poll'])
        with self.rt.store.transaction() as db: db.execute('UPDATE cloud_outbox SET next_try=0')
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.cloud.snapshot()['pending'],0)
        self.assertEqual([p['p_packet']['seq'] for name,p in self.calls if name=='aire_ingest'],[1,2])

    def test_restart_preserves_origin_and_queued_payload(self):
        self.ingest()
        second=create_app(self.tmp.name,background=False)
        try:
            self.assertEqual(second.state.runtime.cloud.origin,self.rt.cloud.origin)
            self.assertEqual(second.state.runtime.store.rows('SELECT count(*) n FROM cloud_outbox')[0]['n'],1)
        finally: second.state.runtime.store.db.close()

    def test_configuration_rejects_admin_keys_and_http(self):
        with self.assertRaises(ValueError): CloudConfig(**{**self.config,'url':'http://example.supabase.co'})
        with self.assertRaises(ValueError): CloudConfig(**{**self.config,'publishable_key':'sb_secret_'+('x'*30)})
        claims=base64.urlsafe_b64encode(json.dumps({'role':'service_role'}).encode()).decode().rstrip('=')
        with self.assertRaises(ValueError): CloudConfig(**{**self.config,'publishable_key':'eyJ.'+claims+'.fake'})

    def test_state_and_status_never_disclose_cloud_secret(self):
        data=self.client.get('/api/state',headers=self.headers).text
        self.assertNotIn(self.config['gateway_secret'],data)
        self.assertNotIn(self.config['publishable_key'],data)
        self.assertEqual(self.client.get('/api/cloud/status').status_code,401)

    def test_cloud_attention_is_authoritative(self):
        response=self.client.post('/api/incidents/'+str(uuid.uuid4())+'/attention',headers=self.headers,json={'action':'atender','note':'Docente revisando'})
        self.assertEqual(response.status_code,409)

    def test_attention_merge_without_new_sensor_data(self):
        self.rt.switch('simulacion');now=time.time()
        for n in range(0,16,3):self.rt.ingest(Sample(mq_raw=560,temperature=25,humidity=55,warmed_up=True),'simulacion',now+n)
        incident=self.rt.snapshot()['incidents'][0]['id']
        def with_attention(request):
            if request.url.path.endswith('aire_gateway_poll'):
                return httpx.Response(200,json={'classroom_id':self.config['classroom_id'],'incidents':[{'id':incident,'status':'en_atencion','note':'Docente remoto','severity':'alerta'}]})
            return self.handler(request)
        with self.rt.store.transaction() as db: db.execute('DELETE FROM cloud_outbox')
        self.rt.cloud.transport=httpx.MockTransport(with_attention)
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.snapshot()['incidents'][0]['status'],'en_atencion')

    def test_gateway_cannot_silently_move_to_other_classroom(self):
        self.ingest()
        self.rt.cloud.transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'classroom_id':str(uuid.uuid4()),'incidents':[]}))
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.cloud.state,'error_sincronizacion')
        self.assertEqual(self.rt.cloud.snapshot()['pending'],1)

    def test_cloud_push_claim_send_finish_contract(self):
        self.rt.push.credential='not-a-real-file'
        self.rt.push.send=Mock(return_value='fcm/fake')
        delivery=str(uuid.uuid4());lease=str(uuid.uuid4());incident=str(uuid.uuid4())
        def jobs(request):
            if request.url.path.endswith('aire_claim_push'):
                return httpx.Response(200,json={'jobs':[{'id':delivery,'lease_id':lease,'incident_id':incident,'source':'simulacion','severity':'alerta','token':'fake-token','installation_id':'fixture-session-binding'}]})
            return self.handler(request)
        self.rt.cloud.transport=httpx.MockTransport(jobs)
        self.rt.cloud.sync_once(force=True)
        message=self.rt.push.send.call_args.args[1]
        self.assertEqual(message['notification_contract'],'2');self.assertEqual(message['installation_id'],'fixture-session-binding');self.assertEqual(message['channel'],'cloud');self.assertIn('SIMULACIÓN',message['title'])
        finished=[p for name,p in self.calls if name=='aire_finish_push'][0]
        self.assertEqual(finished['p_delivery_id'],delivery)
        self.assertEqual(finished['p_lease_id'],lease)
        self.assertIsNone(finished['p_error'])

    def test_cloud_mode_does_not_duplicate_local_push_jobs(self):
        self.client.post('/api/devices',headers=self.headers,json={'installation_id':'phone-local-old','token':'fake-local-token-not-a-recipient','accept_simulations':True})
        self.rt.switch('simulacion');now=time.time()
        for n in range(0,16,3):self.rt.ingest(Sample(mq_raw=560,temperature=25,humidity=55,warmed_up=True),'simulacion',now+n)
        self.assertEqual(len(self.rt.snapshot()['incidents']),1)
        self.assertEqual(self.rt.snapshot()['deliveries'],[])
        self.assertGreater(self.rt.cloud.snapshot()['pending'],0)

    def test_remote_sender_prevents_pc_claim_even_with_local_credential(self):
        self.rt.push.credential='not-a-real-file'
        self.rt.push.send=Mock()
        def remote(request):
            if request.url.path.endswith('aire_gateway_poll'):
                return httpx.Response(200,json={'classroom_id':self.config['classroom_id'],
                    'incidents':[],'push_transport':'cloud','push_worker':{'enabled':True,'error':None}})
            return self.handler(request)
        self.rt.cloud.transport=httpx.MockTransport(remote)
        self.ingest()
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.cloud.state,'conectado')
        self.assertEqual(self.rt.cloud.snapshot()['push'],'emisor_cloud')
        self.assertEqual(self.rt.cloud.snapshot()['pending'],0)
        self.assertFalse(any(n=='aire_claim_push' for n,_ in self.calls))
        self.rt.push.send.assert_not_called()

    def test_remote_sender_error_is_visible_without_stopping_measurements(self):
        def remote(request):
            if request.url.path.endswith('aire_gateway_poll'):
                return httpx.Response(200,json={'classroom_id':self.config['classroom_id'],'incidents':[],
                    'push_transport':'cloud','push_worker':{'enabled':True,'error':'FirebaseOAuthError'}})
            return self.handler(request)
        self.rt.cloud.transport=httpx.MockTransport(remote)
        self.ingest()
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.cloud.state,'conectado')
        self.assertEqual(self.rt.cloud.snapshot()['pending'],0)
        self.assertEqual(self.rt.cloud.snapshot()['push_worker']['error'],'FirebaseOAuthError')

    def test_coordination_event_uses_private_generic_push_and_same_finish_contract(self):
        self.rt.push.credential='not-a-real-file'
        self.rt.push.send=Mock(return_value='fcm/fake-coordination')
        event=str(uuid.uuid4());delivery=str(uuid.uuid4());lease=str(uuid.uuid4())
        def jobs(request):
            if request.url.path.endswith('aire_claim_push'):
                return httpx.Response(200,json={'jobs':[{'id':delivery,'lease_id':lease,
                    'incident_id':str(uuid.uuid4()),'source':'simulacion','severity':'alerta',
                    'token':'fake-token','installation_id':'fixture-session-binding','event_id':event,'event_kind':'impedimento'}]})
            return self.handler(request)
        self.rt.cloud.transport=httpx.MockTransport(jobs)
        self.rt.cloud.sync_once(force=True)
        message=self.rt.push.send.call_args.args[1]
        self.assertEqual(message['event_id'],event)
        self.assertEqual(message['event_kind'],'impedimento')
        self.assertIn('SIMULACIÓN',message['title'])
        self.assertIn('Coordinación',message['title'])
        self.assertIn('se solicita apoyo',message['body'])
        self.assertNotIn('trasladar',message['body']) # La decisión se consulta autenticada.
        self.assertEqual([p for n,p in self.calls if n=='aire_finish_push'][0]['p_provider_id'],'fcm/fake-coordination')

    def test_exhausted_push_reserve_keeps_ack_and_does_not_pause_measurements(self):
        self.ingest()
        budget={'operational_push_today':80,'operational_push_limit':80,
                'laboratory_push_today':20,'laboratory_push_limit':20,
                'operational_push_omitted_today':1}
        def exhausted(request):
            if request.url.path.endswith('aire_ingest'):
                seq=json.loads(request.content)['p_packet']['seq']
                return httpx.Response(200,json={'accepted_seq':seq,'incidents':[],'budget':budget})
            return self.handler(request)
        self.rt.cloud.transport=httpx.MockTransport(exhausted)
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.cloud.state,'conectado')
        self.assertEqual(self.rt.cloud.snapshot()['pending'],0)
        self.assertEqual(self.rt.cloud.snapshot()['budget'],budget)
        self.assertEqual(self.rt.cloud.pause_until,0)
        self.assertEqual(len(self.rt.store.rows('SELECT * FROM samples')),1)


if __name__=='__main__':unittest.main(verbosity=2)
