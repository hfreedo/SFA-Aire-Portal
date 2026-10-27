import json
import tempfile
import time
import unittest
from datetime import datetime,timezone
from unittest.mock import Mock, patch
import uuid
import httpx
from fastapi.testclient import TestClient
from servidor_pc.main import create_app
from servidor_pc.models import Rules,Sample
from servidor_pc.engine import Engine
from servidor_pc.cloud import CloudConfig


class LabTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        environment = patch.dict('os.environ', {'SFA_CLOUD_CONFIG': self.tmp.name + '/no-cloud-config.json', 'GOOGLE_APPLICATION_CREDENTIALS': ''})
        environment.start()
        self.addCleanup(environment.stop)
        self.app=create_app(self.tmp.name,False)
        self.rt=self.app.state.runtime;self.client=TestClient(self.app);self.client.__enter__()
        self.now=time.time()
        self.command={'id':str(uuid.uuid4()),'temperature':38,'humidity':55,'mq_raw':300,
          'duration_s':90,'allow_push':True,'allow_takeover':False,'status':'pendiente',
          'expires_at':datetime.fromtimestamp(self.now+135,timezone.utc).isoformat()}

    def tearDown(self):
        self.client.__exit__(None,None,None);self.tmp.cleanup()

    def sample(self,t=38,mq=300):return Sample(mq_raw=mq,temperature=t,humidity=55,warmed_up=True)

    def configure_cloud(self):
        self.rt.cloud.config=CloudConfig(url='https://example.supabase.co',
          publishable_key='sb_publishable_test_only_123456789',classroom_id=str(uuid.uuid4()),
          gateway_id=str(uuid.uuid4()),gateway_secret='fake-secret-'+('x'*50))

    def test_temperature_alarm_uses_same_persistence_as_mq(self):
        engine=Engine();rules=Rules(baseline=300,conditioned=True,temperature_enabled=True)
        for n in range(0,12,3):
            self.assertIsNone(engine.evaluate(self.sample(),rules,self.now+n).transition)
        decision=engine.evaluate(self.sample(),rules,self.now+12)
        self.assertEqual(decision.transition,'alerta');self.assertEqual(decision.causes,['temperatura'])

    def test_temperature_spike_and_recovery_hysteresis(self):
        engine=Engine();rules=Rules(baseline=300,conditioned=True,temperature_enabled=True)
        engine.evaluate(self.sample(),rules,0);engine.evaluate(self.sample(25),rules,3)
        self.assertEqual(engine.level,'normal')
        for n in range(6,21,3):engine.evaluate(self.sample(),rules,n)
        self.assertEqual(engine.level,'alerta')
        for n in range(21,60,3):engine.evaluate(self.sample(34),rules,n)
        self.assertEqual(engine.level,'alerta')
        for n in range(60,85,3):engine.evaluate(self.sample(25),rules,n)
        self.assertEqual(engine.level,'normal')

    def test_both_alarm_causes_are_recorded(self):
        self.rt.lab.accept({**self.command,'mq_raw':600})
        for n in range(0,25,3):self.rt.lab.tick(self.rt.lab.started+n)
        incident=self.rt.snapshot()['incidents'][0]
        self.assertEqual(set(json.loads(incident['causes'])),{'temperatura','mq135'})
        self.assertEqual(incident['lab_run_id'],self.command['id'])

    def test_lab_recovers_stops_and_does_not_modify_real_calibration(self):
        saved=self.rt.rules.model_dump();self.rt.lab.accept(self.command);started=self.rt.lab.started
        for n in range(0,91,3):self.rt.lab.tick(started+n)
        self.assertEqual(self.rt.source,'detenido');self.assertIsNone(self.rt.lab.command)
        self.assertEqual(self.rt.rules.model_dump(),saved)
        self.assertEqual(self.rt.store.rows('SELECT state FROM samples ORDER BY id DESC LIMIT 1')[0]['state'],'normal')
        self.assertEqual(self.rt.snapshot()['incidents'][0]['status'],'pendiente')
        self.rt.lab.accept(self.command);self.assertIsNone(self.rt.lab.command)

    def test_usb_takeover_requires_explicit_permission(self):
        self.rt.switch('arduino');self.rt.lab.accept(self.command)
        self.assertEqual(self.rt.source,'arduino');self.assertEqual(self.rt.cloud.lab_report['status'],'error')

    def test_explicit_takeover_closes_usb(self):
        self.rt.switch('arduino');serial=Mock();self.rt.serial=serial
        self.rt.lab.accept({**self.command,'allow_takeover':True})
        serial.write.assert_called_with(b'PARAR\n');serial.close.assert_called_once()
        self.assertEqual(self.rt.source,'simulacion')

    def test_no_legacy_simulation_bypass_in_cloud_mode(self):
        self.configure_cloud()
        result=self.client.post('/api/simulation',headers={'Authorization':'Bearer '+self.rt.token},json={'scenario':'alerta'})
        self.assertEqual(result.status_code,403)

    def test_normal_cloud_sampling_is_one_minute_but_transitions_are_immediate(self):
        self.configure_cloud();self.rt.rules=Rules(baseline=300,conditioned=True)
        self.rt.switch('arduino')
        for n in range(0,64,3):self.rt.ingest(self.sample(25),'arduino',self.now+n)
        self.assertEqual(self.rt.store.rows('SELECT count(*) n FROM samples')[0]['n'],22)
        self.assertEqual(self.rt.cloud.snapshot()['pending'],2)
        for n in range(66,82,3):self.rt.ingest(self.sample(25,600),'arduino',self.now+n)
        self.assertEqual(self.rt.cloud.snapshot()['pending'],3)

    def test_quota_pause_is_not_bypassed_by_new_alarm_packet(self):
        self.configure_cloud();calls=[]
        def quota(req):
            calls.append(req)
            return httpx.Response(400,json={'message':'CUOTA_BASE: pausa preventiva'})
        self.rt.cloud.transport=httpx.MockTransport(quota)
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(self.rt.cloud.state,'pausa_cuota')
        self.rt.switch('arduino');self.rt.ingest(self.sample(25),'arduino')
        self.rt.cloud.sync_once(force=True)
        self.assertEqual(len(calls),1);self.assertEqual(self.rt.cloud.snapshot()['pending'],1)

    def test_pipeline_from_admin_command_to_cloud_push_with_mocked_services(self):
        self.configure_cloud();packets=[];sent=[];last_jobs=[];finished=[]
        self.rt.push.credential='fake-credential-not-read'
        self.rt.push.send=lambda token,data:sent.append(data) or 'fcm/mock-accepted'
        def service(req):
            name=req.url.path.split('/')[-1];body=json.loads(req.content)
            if name=='aire_gateway_poll':return httpx.Response(200,json={'classroom_id':str(self.rt.cloud.config.classroom_id),'incidents':[],'lab':self.command})
            if name=='aire_ingest':
                packet=body['p_packet'];packets.append(packet)
                if packet['incidents'] and not sent:
                    last_jobs.append({'id':str(uuid.uuid4()),'lease_id':str(uuid.uuid4()),'incident_id':packet['incidents'][0]['id'],'source':'simulacion','severity':'alerta','token':'fake-token','installation_id':'fixture-session-binding'})
                return httpx.Response(200,json={'accepted_seq':packet['seq'],'incidents':[]})
            if name=='aire_claim_push':
                jobs=last_jobs[:];last_jobs.clear();return httpx.Response(200,json={'jobs':jobs})
            if name=='aire_finish_push':finished.append(body)
            return httpx.Response(200,json=None)
        self.rt.cloud.transport=httpx.MockTransport(service)
        self.rt.cloud.sync_once(force=True);start=self.rt.lab.started
        for n in range(0,25,3):
            self.rt.lab.tick(start+n);self.rt.cloud.sync_once(force=True)
        self.assertTrue(any(p['observation']['temperature']==38 for p in packets))
        self.assertEqual(sent[0]['channel'],'cloud');self.assertIn('SIMULACIÓN',sent[0]['title'])
        self.assertEqual(finished[0]['p_provider_id'],'fcm/mock-accepted')
        self.assertTrue(all(p['lab_run_id']==self.command['id'] for p in packets))


if __name__=='__main__':unittest.main(verbosity=2)
