"""Ejecución acotada de comandos firmados por la autorización Supabase del administrador."""
import time
from datetime import datetime
from pydantic import BaseModel, Field
from .models import Sample, Rules


class LabCommand(BaseModel):
    id: str
    temperature: float = Field(ge=-20, le=60, allow_inf_nan=False)
    humidity: float = Field(ge=0, le=100, allow_inf_nan=False)
    mq_raw: int = Field(ge=1, le=1022)
    duration_s: int = Field(ge=60, le=180)
    allow_push: bool = False
    allow_takeover: bool = False
    expires_at: datetime
    status: str


class LabRunner:
    def __init__(self, runtime):
        self.rt = runtime
        self.command = None
        self.started = None
        self.completed = set()
        self.last_tick = 0

    def accept(self, data):
        with self.rt.lock:
            if not data:
                if self.command:
                    self.stop('cancelado')
                return
            command = LabCommand(**data)
            if command.status not in ('pendiente','ejecutando') or command.expires_at.timestamp()<=time.time():
                if self.command:
                    self.stop('finalizado')
                return
            if command.id in self.completed or (self.command and self.command.id==command.id):
                return
            if self.rt.source=='arduino' and not command.allow_takeover:
                self.rt.cloud.lab_report={'id':command.id,'status':'error','message':'USB activo; no se autorizó reemplazarlo'}
                self.completed.add(command.id)
                return
            if self.command:
                self.stop('cancelado')
            self.rt.switch('simulacion')
            self.rt.lab_run_id = command.id
            self.command, self.started, self.last_tick = command, time.time(), 0
            self.rt.cloud.lab_active=True
            self.rt.cloud.lab_report={'id':command.id,'status':'ejecutando','message':'Receptor ejecutando plan acotado'}

    def tick(self, now=None):
        with self.rt.lock:
            now=time.time() if now is None else now
            command=self.command
            if not command:
                return
            age=now-self.started
            if age>=command.duration_s or now>=command.expires_at.timestamp():
                self.stop('finalizado')
                return
            if now-self.last_tick<3:
                return
            self.last_tick=now
            # 6 s normales, exposición sostenida y 27 s finales de recuperación.
            exposed=6<=age<command.duration_s-27
            self.rt.ingest(Sample(mq_raw=command.mq_raw if exposed else 300,
                temperature=command.temperature if exposed else 25,
                humidity=command.humidity if exposed else 55,warmed_up=True), 'simulacion', now)

    def stop(self, status):
        command=self.command
        if not command:
            return
        self.completed.add(command.id)
        self.rt.cloud.lab_report={'id':command.id,'status':status,'message':'Prueba detenida; reconecte USB explícitamente si corresponde'}
        self.command=None
        self.rt.cloud.lab_active=False
        self.rt.switch('detenido')
        self.rt.lab_run_id=None

    def rules(self):
        return Rules(baseline=300,conditioned=True,temperature_enabled=True)
