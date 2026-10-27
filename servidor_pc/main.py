import asyncio

from contextlib import asynccontextmanager

import hmac

import hashlib

import json

import os

from pathlib import Path

import secrets

import threading

import time

import uuid



from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request

from fastapi.responses import FileResponse

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field



from .engine import Engine

from .models import Device, Rules, Sample, SerialConnection, Simulation

from .push import PushSender

from .store import Store

from .cloud import CloudBridge, PublicConnection

from .lab import LabRunner

from .workspace import install_workspace, connect_serial, save_rules



ROOT = Path(__file__).resolve().parents[1]





class Runtime:

    def __init__(self, path):

        self.store = Store(path)

        self.instance_id = str(uuid.uuid4())

        self.shutdown_callback = None

        self.rules = Rules(**self.store.setting('rules', {}))

        self.engine = Engine()

        self.lock = threading.RLock()

        self.source = 'detenido'

        self.scenario = 'normal'

        self.latest = None

        self.serial = None

        self.serial_state = 'desconectado'

        self.error = None

        self.last_valid = 0.0

        self.last_monitor = 0.0

        self.lab_run_id = None

        self.token = os.getenv('SFA_API_TOKEN') or self.store.setting('api_token') or secrets.token_urlsafe(32)

        self.store.save_setting('api_token', self.token)

        self.push = PushSender(self.store)

        self.cloud = CloudBridge(self.store, os.getenv('SFA_CLOUD_CONFIG', ROOT / 'secrets' / 'supabase-pc.json'), self.push)

        self.public_connection = None
        try:
            public_path=Path(os.getenv('SFA_PUBLIC_CONFIG', ROOT/'config/public-config.json'))
            if public_path.is_file():
                self.public_connection=PublicConnection.model_validate_json(public_path.read_text(encoding='utf-8-sig'))
        except (OSError,ValueError):
            pass

        self.lab = LabRunner(self)

        self.cloud.on_lab = self.lab.accept

        if self.cloud.config:

            with self.store.transaction() as db:

                db.execute("UPDATE deliveries SET status='cancelado' WHERE status IN ('pendiente','reintento')")



    def switch(self, source):

        with self.lock:

            if self.serial:

                try:

                    self.serial.write(b'PARAR\n')

                    self.serial.close()

                except Exception:

                    pass

            self.serial = None

            self.serial_state = 'desconectado'

            self.source, self.latest, self.error, self.last_valid = source, None, None, 0.0

            self.engine.reset()



    def ingest(self, sample, source, now=None):

        now = time.time() if now is None else now

        with self.lock:

            if source != self.source:

                raise ValueError('Fuente inactiva; no se mezclan lecturas reales y simuladas')

            rules = self.rules if source == 'arduino' else Rules(baseline=300, conditioned=True,

                warning_ratio=self.rules.warning_ratio, alert_ratio=self.rules.alert_ratio,

                persistence_s=self.rules.persistence_s, recovery_s=self.rules.recovery_s,

                hysteresis=self.rules.hysteresis)

            if self.lab_run_id:

                rules=self.lab.rules()

            gateway = str(self.cloud.config.gateway_id) if self.cloud.config else None

            decision = self.engine.evaluate(sample, rules, now)

            self.latest = {**sample.model_dump(), 'received': now, 'source': source,

                           'state': decision.state, 'ratio': decision.ratio,

                           'causes':decision.causes,'lab_run_id':self.lab_run_id}

            self.last_valid, self.error = now, None

            with self.store.transaction() as db:

                db.execute('INSERT INTO samples(received,source,state,payload,ratio) VALUES (?,?,?,?,?)',

                           (now, source, decision.state, sample.model_dump_json(), decision.ratio))

                # Una muestra cada 3 s: límite de disco de aproximadamente siete días continuos.

                db.execute('DELETE FROM samples WHERE id <= (SELECT MAX(id)-200000 FROM samples)')

                if decision.transition in ('aviso', 'alerta'):

                    row = db.execute("SELECT * FROM incidents WHERE source=? AND status!='resuelto' AND cloud_gateway_id IS ? AND COALESCE(lab_run_id,'')=? ORDER BY opened DESC LIMIT 1", (source,gateway,self.lab_run_id or '')).fetchone()

                    incident = row['id'] if row else str(uuid.uuid4())

                    if not row:

                        db.execute('INSERT INTO incidents(id,source,severity,opened,updated,cloud_gateway_id) VALUES (?,?,?,?,?,?)',

                                   (incident, source, decision.state, now, now,gateway))

                    else:

                        # No reducir la prioridad del incidente pendiente durante una recuperación parcial.

                        severity = 'alerta' if row['severity'] == 'alerta' else decision.state

                        db.execute('UPDATE incidents SET severity=?,updated=? WHERE id=?', (severity, now, incident))

                    db.execute('UPDATE incidents SET causes=?,lab_run_id=? WHERE id=?', (json.dumps(decision.causes),self.lab_run_id,incident))

                    targets = [] if self.cloud.config else db.execute('SELECT * FROM devices WHERE accept_simulations=1 OR ?!=?', (source, 'simulacion')).fetchall()

                    for target in targets:

                        db.execute('INSERT OR IGNORE INTO deliveries(id,incident_id,device_id,severity,next_try,notification_binding) VALUES (?,?,?,?,?,?)',

                                   (str(uuid.uuid4()), incident, target['id'], decision.state, now, target['notification_binding']))

                pending = db.execute("SELECT id,source,severity,opened,causes,lab_run_id FROM incidents WHERE status!='resuelto' AND cloud_gateway_id IS ? AND COALESCE(lab_run_id,'')=?", (gateway,self.lab_run_id or '')).fetchall()

                self.cloud.enqueue(db, self.latest, pending)

            return self.latest



    def snapshot(self):

        with self.lock:

            age = time.time() - self.last_valid if self.last_valid else None

            state = ('detenido' if self.source == 'detenido' else 'sin_datos'

                     if age is None or age > 10 else self.latest['state'])

            return {'attention_contract': 2, 'receiver_id': self.store.receiver_id, 'source': self.source, 'state': state, 'age_s': age, 'latest': self.latest,

                    'scenario': self.scenario, 'serial': self.serial_state, 'error': self.error,

                    'cloud': self.cloud.snapshot(),

                    'rules': self.rules.model_dump(), 'push': self.push.state,

                    'devices': self.store.rows('SELECT id,name,accept_simulations,updated FROM devices'),

                    'incidents': self.store.rows('SELECT * FROM incidents ORDER BY opened DESC LIMIT 60'),

                    'deliveries': self.store.rows('SELECT id,incident_id,device_id,severity,status,attempts,error,received,opened FROM deliveries ORDER BY rowid DESC LIMIT 100')}



    def serial_tick(self):

        with self.lock:

            if not self.serial or self.source != 'arduino':

                return

            try:

                if not self.last_valid and time.time() - self.last_monitor > 2:

                    self.serial.write(b'MONITOR\n')

                    self.last_monitor = time.time()

                # Acotado para que un emisor defectuoso no bloquee el servidor.

                for _ in range(8):

                    if not self.serial.in_waiting:

                        break

                    raw = self.serial.readline(1024).decode('utf-8').strip()

                    if raw.startswith('{'):

                        self.ingest(Sample.model_validate_json(raw), 'arduino')

                self.serial_state = 'conectado'

            except (ValueError, UnicodeError):

                self.error = 'Trama inválida: revisar firmware y 115200 baudios'

            except Exception:

                self.serial_state, self.error = 'error', 'Conexión serie interrumpida'

                if self.serial:

                    self.serial.close()

                self.serial = None





def create_app(data_dir=None, background=True):

    directory = Path(data_dir or os.getenv('SFA_DATA_DIR', ROOT / 'data'))

    directory.mkdir(parents=True, exist_ok=True)

    rt = Runtime(directory / 'aire.sqlite3')

    stop = asyncio.Event()



    async def worker():

        tick = 0

        while not stop.is_set():

            rt.lab.tick()

            if not rt.lab.command and rt.source == 'simulacion' and tick % 6 == 0 and rt.scenario != 'sin_datos':

                values = {'normal': 300, 'aviso': 420, 'alerta': 560, 'fallo_dht': 300, 'calentamiento': 300}

                rt.ingest(Sample(mq_raw=values[rt.scenario], temperature=25, humidity=55,

                    dht_ok=rt.scenario != 'fallo_dht', warmed_up=rt.scenario != 'calentamiento'), 'simulacion')

            await asyncio.to_thread(rt.serial_tick)

            tick += 1

            try:

                await asyncio.wait_for(stop.wait(), .5)

            except asyncio.TimeoutError:

                pass



    async def network_worker(callback):

        while not stop.is_set():

            await asyncio.to_thread(callback)

            try:

                await asyncio.wait_for(stop.wait(), 5)

            except asyncio.TimeoutError:

                pass



    @asynccontextmanager

    async def lifespan(app):

        tasks = [asyncio.create_task(worker()), asyncio.create_task(network_worker(rt.push.process_once)),

                 asyncio.create_task(network_worker(rt.cloud.sync_once))] if background else []

        yield

        stop.set()

        if tasks:

            await asyncio.gather(*tasks)

        rt.switch('detenido')

        rt.store.db.close()



    app = FastAPI(title='SFA Aire · Integración de prototipo', version='0.6.1', lifespan=lifespan)

    app.state.runtime = rt

    bearer = HTTPBearer(auto_error=False)



    def auth(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):

        if not credentials or not hmac.compare_digest(credentials.credentials, rt.token):

            raise HTTPException(401, 'Clave de conexión incorrecta')



    @app.get('/health')

    def health():

        return {'ok': True, 'version': '0.6.1','app':'sfa-aire',

                'workspace':hashlib.sha256(str(ROOT).encode()).hexdigest()[:12],

                'instance_id':rt.instance_id,'can_shutdown':callable(rt.shutdown_callback)}



    class ShutdownRequest(BaseModel):

        instance_id: str = Field(min_length=36,max_length=36)



    @app.post('/api/maintenance/shutdown', dependencies=[Depends(auth)])

    def shutdown_server(body:ShutdownRequest, request:Request):

        host=request.client.host if request.client else ''

        if host not in ('127.0.0.1','::1') and not (not background and host=='testclient'):

            raise HTTPException(403,'La detención del servicio se realiza desde esta PC.')

        if body.instance_id!=rt.instance_id:

            raise HTTPException(409,'La instancia cambió. Actualice el estado del servidor.')

        if not callable(rt.shutdown_callback):

            raise HTTPException(409,'El servidor no se inició desde el panel de esta instalación.')

        callback=rt.shutdown_callback

        threading.Timer(.3,callback).start()

        return {'state':'stopping'}



    @app.get('/api/public-config')

    def public_config():

        # Misma configuración pública distribuida al cliente Android. Nunca vínculo PC.

        config = rt.cloud.config or rt.public_connection

        return {'configured':bool(config), **({'url':config.url,'key':config.publishable_key} if config else {})}



    @app.get('/api/cloud/status', dependencies=[Depends(auth)])

    def cloud_status():

        return rt.cloud.snapshot()



    @app.get('/api/state', dependencies=[Depends(auth)])

    def state():

        return rt.snapshot()



    @app.get('/api/history', dependencies=[Depends(auth)])

    def history():

        return rt.store.rows('SELECT id,received,source,state,ratio,payload FROM samples ORDER BY id DESC LIMIT 120')



    @app.get('/api/ports', dependencies=[Depends(auth)])

    def ports():

        from serial.tools import list_ports

        return [{'port': p.device, 'description': p.description} for p in list_ports.comports()]



    @app.post('/api/serial/connect', dependencies=[Depends(auth)])

    def connect(body: SerialConnection):

        connect_serial(rt, body.port)

        return {'ok': True}



    @app.post('/api/stop', dependencies=[Depends(auth)])

    def stop_source():

        if rt.lab.command:

            rt.lab.stop('cancelado')

        rt.switch('detenido')

        return {'ok': True}



    @app.post('/api/simulation', dependencies=[Depends(auth)])

    def simulate(body: Simulation):

        if rt.cloud.config:

            raise HTTPException(403,'Las simulaciones cloud se autorizan en el laboratorio de administradores del portal remoto')

        with rt.lock:

            if rt.source != 'simulacion':

                rt.switch('simulacion')

            rt.scenario = body.scenario

        return {'ok': True, 'source': 'simulacion'}



    @app.put('/api/rules', dependencies=[Depends(auth)])

    def configure(body: Rules):

        save_rules(rt, body)

        return body



    @app.post('/api/devices', dependencies=[Depends(auth)])

    def register(body: Device):

        binding = str(body.notification_binding) if body.notification_binding is not None else None

        if (body.receiver_id is not None and str(body.receiver_id) != rt.store.receiver_id

                or binding is not None and body.receiver_id is None):

            raise HTTPException(409, 'El receptor cambió. Verifique la conexión y vuelva a registrar el teléfono.')

        with rt.store.transaction() as db:

            # Un token trasladado o un vínculo reemplazado nunca hereda sus trabajos.

            db.execute("""UPDATE deliveries SET status='cancelado' WHERE status IN ('pendiente','reintento')

                       AND device_id IN (SELECT id FROM devices WHERE token=? AND id!=?)""",

                       (body.token, body.installation_id))

            current = db.execute('SELECT notification_binding FROM devices WHERE id=?', (body.installation_id,)).fetchone()

            if current is not None and current['notification_binding'] != binding:

                db.execute("UPDATE deliveries SET status='cancelado' WHERE device_id=? AND status IN ('pendiente','reintento')", (body.installation_id,))

            db.execute('DELETE FROM devices WHERE token=? AND id!=?', (body.token, body.installation_id))

            db.execute('''INSERT INTO devices(id,token,name,accept_simulations,updated,notification_binding)

                       VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET token=excluded.token,name=excluded.name,

                       accept_simulations=excluded.accept_simulations,updated=excluded.updated,notification_binding=excluded.notification_binding''',

                       (body.installation_id, body.token, body.name, body.accept_simulations, time.time(), binding))

        return {'ok': True}



    @app.delete('/api/devices/{device_id}', dependencies=[Depends(auth)])

    def unregister(device_id: str):

        with rt.store.transaction() as db:

            db.execute('DELETE FROM devices WHERE id=?', (device_id,))

            db.execute("UPDATE deliveries SET status='cancelado' WHERE device_id=? AND status IN ('pendiente','reintento')", (device_id,))

        return {'ok': True}



    class Receipt(BaseModel):

        installation_id: str

        action: str = Field(pattern='^(recibido|abierto)$')

        notification_binding: uuid.UUID | None = None

        receiver_id: uuid.UUID | None = None



    @app.post('/api/deliveries/{delivery_id}/receipt', dependencies=[Depends(auth)])

    def receipt(delivery_id: str, body: Receipt):

        with rt.store.transaction() as db:

            row = db.execute('SELECT * FROM deliveries WHERE id=? AND device_id=?', (delivery_id, body.installation_id)).fetchone()

            if not row:

                raise HTTPException(404, 'Entrega no encontrada')

            device = db.execute('SELECT notification_binding FROM devices WHERE id=?', (body.installation_id,)).fetchone()

            if device is None or device['notification_binding'] != row['notification_binding']:

                raise HTTPException(409, 'La entrega pertenece a un registro anterior del teléfono.')

            if (body.receiver_id is not None and str(body.receiver_id) != rt.store.receiver_id

                    or row['notification_binding'] is not None and (

                        body.receiver_id is None or body.notification_binding is None

                        or str(body.notification_binding) != row['notification_binding'])

                    or row['notification_binding'] is None and body.notification_binding is not None):

                raise HTTPException(409, 'El contexto de la entrega no corresponde al registro actual.')

            column = 'received' if body.action == 'recibido' else 'opened'

            db.execute(f"UPDATE deliveries SET {column}=COALESCE({column},?),status=CASE WHEN status='cancelado' THEN status ELSE 'recibido_app' END WHERE id=?", (time.time(), delivery_id))

            if body.action == 'abierto':

                db.execute('UPDATE deliveries SET received=COALESCE(received,?) WHERE id=?', (time.time(), delivery_id))

        return {'ok': True}



    class Attention(BaseModel):

        action: str = Field(pattern='^(atender|resolver)$')

        note: str = Field(default='', max_length=500)



    @app.post('/api/incidents/{incident_id}/attention', dependencies=[Depends(auth)])

    def attention(incident_id: str, body: Attention):

        if rt.cloud.config:

            raise HTTPException(409, 'Este receptor sincroniza con la nube. Atienda desde Acceso remoto para conservar una sola atención compartida.')

        with rt.lock, rt.store.transaction() as db:

            row = db.execute('SELECT * FROM incidents WHERE id=?', (incident_id,)).fetchone()

            if not row:

                raise HTTPException(404, 'Incidente no encontrado')

            if row['status'] == 'resuelto':

                raise HTTPException(409, 'El incidente ya está resuelto')

            db.execute('UPDATE incidents SET status=?,note=?,updated=?,resolved=? WHERE id=?',

                       ('resuelto' if body.action == 'resolver' else 'en_atencion', ('AVISO ATENDIDO · No confirma normalización del ambiente. ' if body.action == 'resolver' else '') + body.note.strip(), time.time(),

                        time.time() if body.action == 'resolver' else None, incident_id))

        return {'ok': True}



    @app.websocket('/ws')

    async def websocket(ws: WebSocket):

        await ws.accept()

        try:

            payload = await asyncio.wait_for(ws.receive_json(), 5)

            if not hmac.compare_digest(str(payload.get('token', '')), rt.token):

                await ws.close(code=1008)

                return

            while True:

                await ws.send_json(rt.snapshot())

                await asyncio.sleep(2)

        except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):

            pass



    dist = ROOT / 'interfaz_web' / 'dist'

    if dist.exists():

        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')



    @app.get('/')

    def index():

        if not (dist / 'index.html').exists():

            raise HTTPException(503, 'Construya la interfaz con npm run build en interfaz_web')

        return FileResponse(dist / 'index.html')



    @app.get('/invitacion')
    @app.get('/remoto')

    @app.get('/remoto.html')

    def remote_index():

        if not (dist / 'remoto.html').exists():

            raise HTTPException(503, 'Reconstruya la interfaz para habilitar el portal remoto')

        return FileResponse(dist / 'remoto.html')



    install_workspace(app, rt)

    return app

