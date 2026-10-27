import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager


class Store:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS samples (
          id INTEGER PRIMARY KEY, received REAL, source TEXT, state TEXT, payload TEXT, ratio REAL);
        CREATE TABLE IF NOT EXISTS incidents (
          id TEXT PRIMARY KEY, source TEXT, severity TEXT, opened REAL, updated REAL,
          status TEXT DEFAULT 'pendiente', note TEXT DEFAULT '', resolved REAL);
        CREATE TABLE IF NOT EXISTS devices (
          id TEXT PRIMARY KEY, token TEXT UNIQUE, name TEXT, accept_simulations INTEGER, updated REAL);
        CREATE TABLE IF NOT EXISTS deliveries (
          id TEXT PRIMARY KEY, incident_id TEXT, device_id TEXT, severity TEXT,
          status TEXT DEFAULT 'pendiente', attempts INTEGER DEFAULT 0, next_try REAL,
          provider_id TEXT, error TEXT, received REAL, opened REAL,
          UNIQUE(incident_id,device_id,severity));
        CREATE INDEX IF NOT EXISTS sample_time ON samples(received);
        CREATE TABLE IF NOT EXISTS cloud_outbox (
          seq INTEGER PRIMARY KEY AUTOINCREMENT, gateway_id TEXT NOT NULL,
          payload TEXT NOT NULL, created REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
          next_try REAL NOT NULL DEFAULT 0);
        ''')
        columns={row[1] for row in self.db.execute('PRAGMA table_info(incidents)')}
        for name,kind in [('causes',"TEXT NOT NULL DEFAULT '[]'"),('lab_run_id','TEXT'),('cloud_gateway_id','TEXT')]:
            if name not in columns:
                self.db.execute(f'ALTER TABLE incidents ADD COLUMN {name} {kind}')
        # Campos aditivos: NULL distingue registros/entregas de la APK v1.
        for table in ('devices', 'deliveries'):
            columns = {row[1] for row in self.db.execute(f'PRAGMA table_info({table})')}
            if 'notification_binding' not in columns:
                self.db.execute(f'ALTER TABLE {table} ADD COLUMN notification_binding TEXT')
        self.db.execute('INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)',
                        ('receiver_id', json.dumps(str(uuid.uuid4()))))
        encoded = self.db.execute('SELECT value FROM settings WHERE key=?', ('receiver_id',)).fetchone()[0]
        identity = json.loads(encoded)
        if not isinstance(identity, str) or str(uuid.UUID(identity)) != identity:
            raise ValueError('La identidad persistida del receptor no es válida')
        self.receiver_id = identity
        self.db.commit()

    @contextmanager
    def transaction(self):
        with self.lock:
            try:
                yield self.db
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(row) for row in self.db.execute(sql, args).fetchall()]

    def setting(self, key, default=None):
        rows = self.rows('SELECT value FROM settings WHERE key=?', (key,))
        return json.loads(rows[0]['value']) if rows else default

    def save_setting(self, key, value):
        with self.transaction() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))
