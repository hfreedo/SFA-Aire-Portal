"""Aceptado por FCM no equivale a recibido ni leído por una persona."""
from datetime import timedelta
import os
import time
import threading


class PushSender:
    def __init__(self, store):
        self.store = store
        self.app = None
        self.state = 'sin_credencial'
        self.credential = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        self.init_lock = threading.Lock()
        self.process_lock = threading.Lock()

    def send(self, token, data):
        import firebase_admin
        from firebase_admin import credentials, messaging
        with self.init_lock:
            if not self.app:
                self.app = firebase_admin.initialize_app(credentials.Certificate(self.credential), options={'httpTimeout':8}, name='sfa-aire')
        # La app registra FirebaseMessaging.token; no confundirlo con un FID.
        # Admin 7.7 conserva token (deprecated). Migrar destino requiere migrar clientes.
        return messaging.send(messaging.Message(
            token=token, data=data,
            android=messaging.AndroidConfig(priority='high', ttl=timedelta(minutes=5))), app=self.app)

    def _current_job(self, delivery_id, now):
        # Releer justo antes de cada intento: la lista inicial puede quedar obsoleta.
        with self.store.transaction() as db:
            row = db.execute("""SELECT d.*, t.token, t.notification_binding AS current_binding,
                t.accept_simulations, i.source, i.status AS incident_status FROM deliveries d
                LEFT JOIN devices t ON t.id=d.device_id LEFT JOIN incidents i ON i.id=d.incident_id
                WHERE d.id=?""", (delivery_id,)).fetchone()
            if row is None or row['status'] not in ('pendiente', 'reintento'):
                return None
            if (row['token'] is None or row['source'] is None
                    or row['notification_binding'] != row['current_binding']
                    or row['source'] == 'simulacion' and not row['accept_simulations']):
                db.execute("UPDATE deliveries SET status='cancelado' WHERE id=?", (delivery_id,))
                return None
            if now - row['next_try'] > 300 and row['attempts'] == 0:
                db.execute("UPDATE deliveries SET status='vencido' WHERE id=?", (delivery_id,))
                return None
            return dict(row)

    def _payload(self, job):
        data = {'channel': 'local', 'receiver_id': self.store.receiver_id,
                'delivery_id': job['id'], 'incident_id': job['incident_id'],
                'source': job['source'], 'severity': job['severity'],
                'title': ('SIMULACIÓN · ' if job['source'] == 'simulacion' else '') + 'SFA Aire · Revisar aula',
                'body': 'Se detectó una variación sostenida. Abra la app para revisar el incidente.'}
        if job['notification_binding'] is not None:
            data.update(local_contract='2', notification_binding=job['notification_binding'])
        return data

    def process_once(self, send=None):
        if send is None and not self.credential:
            self.state = 'sin_credencial'
            return
        # Un solo procesador por Runtime; no retener el lock SQLite durante la red.
        if not self.process_lock.acquire(blocking=False):
            return
        try:
            self.state = 'configurado'
            jobs = self.store.rows("""SELECT id FROM deliveries
                WHERE status IN ('pendiente','reintento') AND next_try<=? ORDER BY next_try,id LIMIT 20""", (time.time(),))
            for candidate in jobs:
                now = time.time()
                job = self._current_job(candidate['id'], now)
                if job is None:
                    continue
                try:
                    provider_id = (send or self.send)(job['token'], self._payload(job))
                    with self.store.transaction() as db:
                        # Un registro, retiro o resolución durante FCM puede haber cancelado.
                        # Conservar ese estado; guardar solo el resultado del intento real.
                        db.execute("""UPDATE deliveries SET status=CASE
                            WHEN status NOT IN ('pendiente','reintento') THEN status
                            WHEN received IS NULL THEN 'aceptado_fcm' ELSE 'recibido_app' END,
                            provider_id=?, attempts=attempts+1, error=NULL WHERE id=?""", (provider_id, job['id']))
                except Exception as error:
                    attempts = job['attempts'] + 1
                    terminal = type(error).__name__ in ('UnregisteredError', 'SenderIdMismatchError') or attempts >= 5
                    with self.store.transaction() as db:
                        db.execute("""UPDATE deliveries SET status=CASE WHEN status IN ('pendiente','reintento')
                            THEN ? ELSE status END, attempts=attempts+1, next_try=?, error=? WHERE id=?""",
                            ('error' if terminal else 'reintento', now + min(300, 2 ** attempts * 5),
                             type(error).__name__, job['id']))
                    self.state = 'error_envio'
        finally:
            self.process_lock.release()
