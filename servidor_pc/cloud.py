"""Puente opcional Supabase: cola durable y credencial limitada a un receptor."""
import base64
import json
from pathlib import Path
import time
import threading
import uuid
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, model_validator


class PublicConnection(BaseModel):
    url: str
    publishable_key: str = Field(min_length=20)


    @model_validator(mode='after')
    def limited_key(self):
        parsed = urlparse(self.url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            raise ValueError('Supabase requiere una URL base HTTPS válida')
        key = self.publishable_key
        if key.startswith('sb_secret_'):
            raise ValueError('No coloque una clave secreta de Supabase en este receptor')
        if key.startswith('eyJ'):
            try:
                claims = json.loads(base64.urlsafe_b64decode(key.split('.')[1] + '==='))
            except Exception as error:
                raise ValueError('Clave pública JWT inválida') from error
            if claims.get('role') != 'anon':
                raise ValueError('Solo se admite la clave anon pública, no service_role')
        elif not key.startswith('sb_publishable_'):
            raise ValueError('Use publishable key o la clave anon pública')
        self.url = self.url.rstrip('/')
        return self


class CloudConfig(PublicConnection):    classroom_id: uuid.UUID    gateway_id: uuid.UUID    gateway_secret: str = Field(min_length=40, max_length=200)class CloudBridge:
    def __init__(self, store, config_path, sender):
        self.store, self.sender = store, sender
        self.config_lock = threading.RLock()
        self.config = None
        self.state, self.error, self.last_sync = 'sin_configurar', None, None
        self.transport = None  # Solo para las pruebas de transporte HTTP.
        self.on_lab = None
        self.lab_active = False
        self.lab_report = None
        self.next_sync = 0.0
        self.pause_until = 0.0
        self.next_poll_s = 30
        self.budget = None
        self.push_transport = 'pc'
        self.push_worker = None
        self.origin = store.setting('cloud_origin') or str(uuid.uuid4())
        store.save_setting('cloud_origin', self.origin)
        self.path = Path(config_path)
        try:
            if self.path.exists():
                self.config = CloudConfig.model_validate_json(self.path.read_text(encoding='utf-8-sig'))
                self.state = 'esperando_sincronizacion'
                with store.transaction() as db:
                    db.execute('UPDATE incidents SET cloud_gateway_id=? WHERE cloud_gateway_id IS NULL', (str(self.config.gateway_id),))
        except Exception:
            self.state, self.error = 'configuracion_invalida', 'Revise secrets/supabase-pc.json; no se muestran sus valores'

    def enqueue(self, db, latest, incidents):
        if self.config is None:
            return
        last = db.execute('SELECT value FROM settings WHERE key=?', ('cloud_last_'+latest['source'],)).fetchone()
        previous=json.loads(last[0]) if last else None
        # Detalle local cada 3 s. Nube normal cada 60 s; transición y laboratorio inmediatos.
        force = latest.get('lab_run_id') or previous is None or previous['state']!=latest['state']
        if not force and latest['received']-previous['received']<60:
            return
        if db.execute('SELECT count(*) FROM cloud_outbox').fetchone()[0]>=5000:
            self.state,self.error='pausa_cuota_local','Cola cloud llena; mediciones conservadas en SQLite'
            return
        packet = {'origin_id': self.origin, 'source': latest['source'], 'state': latest['state'],
                  'sample_at': latest['received'], 'observation': latest,
                  'incidents': [dict(i) for i in incidents if i['source'] == latest['source']]}
        for incident in packet['incidents']:
            if isinstance(incident.get('causes'),str):
                incident['causes']=json.loads(incident['causes'])
        packet['lab_run_id']=latest.get('lab_run_id')
        db.execute('INSERT INTO cloud_outbox(gateway_id,payload,created) VALUES (?,?,?)',
                   (str(self.config.gateway_id), json.dumps(packet, allow_nan=False), time.time()))
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('cloud_last_'+latest['source'],json.dumps(latest)))
        if force:
            self.next_sync=0

    def rpc(self, name, payload):
        config = self.config
        headers = {'apikey': config.publishable_key, 'Content-Type': 'application/json'}
        # La publishable key moderna no es un JWT de sesión.
        if config.publishable_key.startswith('eyJ'):
            headers['Authorization'] = 'Bearer ' + config.publishable_key
        with httpx.Client(timeout=8, transport=self.transport, follow_redirects=False) as client:
            response = client.post(config.url + '/rest/v1/rpc/' + name, headers=headers, json=payload)
            response.raise_for_status()
            return response.json() if response.content else None

    def credentials(self):
        return {'p_gateway_id': str(self.config.gateway_id), 'p_secret': self.config.gateway_secret}

    def sync_once(self, force=False):
        with self.config_lock:
            self._sync_once(force)

    def _sync_once(self, force=False):
        if self.config is None:
            return
        now=time.time()
        if now<self.pause_until:
            return
        if not force and now<self.next_sync:
            return
        self.next_sync=now+(5 if self.lab_active else self.next_poll_s)
        rows = self.store.rows('SELECT * FROM cloud_outbox WHERE gateway_id=? ORDER BY seq LIMIT 20', (str(self.config.gateway_id),))
        try:
            pending_ids=[r['id'] for r in self.store.rows("SELECT id FROM incidents WHERE status!='resuelto' AND cloud_gateway_id=? ORDER BY updated DESC LIMIT 20", (str(self.config.gateway_id),))]
            status = self.rpc('aire_gateway_poll', {**self.credentials(), 'p_push_configured':bool(self.sender.credential),'p_incident_ids':pending_ids})
            if status['classroom_id'] != str(self.config.classroom_id):
                raise ValueError('La configuración no corresponde al aula del receptor')
            self.merge_attention(status.get('incidents', []))
            self.budget=status.get('budget')
            self.push_transport=status.get('push_transport','pc')
            self.push_worker=status.get('push_worker')
            if self.on_lab:
                self.on_lab(status.get('lab'))
            if self.lab_active:
                self.next_sync=min(self.next_sync,now+5)
            if self.lab_report:
                self.rpc('aire_lab_report',{**self.credentials(),'p_run_id':self.lab_report['id'],
                    'p_status':self.lab_report['status'],'p_message':self.lab_report['message']})
                self.lab_report=None
            self.last_sync = time.time()
            for row in rows:
                if row['next_try'] > time.time():
                    break  # Conservar orden y no adelantar paquetes durante un reintento.
                packet = json.loads(row['payload'])
                packet['seq'] = row['seq']
                result = self.rpc('aire_ingest', {**self.credentials(), 'p_packet': packet})
                if isinstance(result.get('budget'),dict):
                    self.budget=result['budget']
                if result.get('accepted_seq', 0) < row['seq']:
                    raise ValueError('Cloud no confirmó el paquete')
                with self.store.transaction() as db:
                    for incident in result.get('incidents', []):
                        self.merge_incident(db, incident)
                    db.execute('DELETE FROM cloud_outbox WHERE seq=?', (row['seq'],))
                self.last_sync = time.time()
            self.state, self.error = 'conectado', None
            self.send_cloud_push()
        except Exception as error:
            self.state, self.error = 'error_sincronizacion', type(error).__name__
            if isinstance(error,httpx.HTTPStatusError):
                try:
                    if error.response.json().get('message','').startswith('CUOTA_'):
                        self.state,self.error='pausa_cuota','Límite preventivo cloud; registro local continúa'
                        self.next_sync=now+900
                        self.pause_until=now+900
                except (ValueError,AttributeError):
                    pass
            if rows:
                with self.store.transaction() as db:
                    remaining = db.execute('SELECT seq,attempts FROM cloud_outbox WHERE gateway_id=? ORDER BY seq LIMIT 1', (str(self.config.gateway_id),)).fetchone()
                    if remaining:
                        db.execute('UPDATE cloud_outbox SET attempts=attempts+1,next_try=? WHERE seq=?',
                                   (time.time()+min(300,2**min(8,remaining['attempts']+1)*5), remaining['seq']))

    @staticmethod
    def merge_incident(db, incident):
        if incident['status'] not in ('pendiente','en_atencion','resuelto'):
            raise ValueError('Estado cloud inválido')
        db.execute('UPDATE incidents SET status=?,note=? WHERE id=?', (incident['status'],incident['note'],incident['id']))

    def merge_attention(self, incidents):
        with self.store.transaction() as db:
            for incident in incidents:
                self.merge_incident(db, incident)

    def send_cloud_push(self):
        if self.push_transport == 'cloud' or not self.sender.credential:
            return
        jobs = self.rpc('aire_claim_push', self.credentials())['jobs']
        for job in jobs:
            provider, error = None, None
            try:
                provider = self.sender.send(job['token'], {'notification_contract':'2','installation_id':job['installation_id'], 'channel':'cloud', 'delivery_id':job['id'],
                    'incident_id':job['incident_id'],'source':job['source'],'severity':job['severity'],
                    'classroom_id':str(job.get('classroom_id') or self.config.classroom_id),
                    'lab_run_id':str(job.get('lab_run_id') or ''),'causes':','.join(job.get('causes') or []),
                    'event_id':str(job.get('event_id') or ''),'event_kind':str(job.get('event_kind') or ''),
                    'title':('SIMULACIÓN · ' if job['source']=='simulacion' else '')+('SFA Aire · Coordinación' if job.get('event_id') else 'SFA Aire · Revisar aula'),
                    'body':('Cambio de coordinación: '+self.event_label(job.get('event_kind'))+'. Abra la app y verifique la indicación vigente.' if job.get('event_id') else 'Variación sostenida registrada. Abra la app para consultar el aula.')})
            except Exception as failure:
                error = type(failure).__name__
            self.rpc('aire_finish_push', {**self.credentials(), 'p_delivery_id':job['id'],
                     'p_lease_id':job['lease_id'], 'p_provider_id':provider, 'p_error':error})

    @staticmethod
    def event_label(kind):
        return {'indicacion':'nueva indicación','confirmada':'comprensión confirmada','impedimento':'se solicita apoyo','aclaracion':'se solicita aclaración','realizada':'resultado completo','parcial':'resultado parcial','coordinacion':'responsable actualizado','atender':'contexto registrado','resolver':'revisión y cierre'}.get(kind,'actualización registrada')

    def snapshot(self):
        return {'state':self.state,'error':self.error,'last_sync':self.last_sync,
                'configured':self.config is not None,
                'classroom_id':str(self.config.classroom_id) if self.config else None,
                'pending':self.store.rows('SELECT count(*) AS n FROM cloud_outbox')[0]['n'],
                'next_poll_s':self.next_poll_s,'lab_active':self.lab_active,'budget':self.budget,
                'push': 'emisor_cloud' if self.push_transport == 'cloud' else ('emisor_pc' if self.sender.credential else 'sin_credencial_fcm'),
                'push_worker':self.push_worker}
