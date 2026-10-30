from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class Sample(BaseModel):
    device_id: Literal['aula-01'] = 'aula-01'
    serial_contract: Literal[1,2] = 1
    simulated: bool = Field(default=False, strict=True)
    mq_raw: int = Field(ge=0, le=1023)
    temperature: float | None = Field(default=None, ge=-40, le=80, allow_inf_nan=False)
    humidity: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    dht_ok: bool = True
    warmed_up: bool = False

    @model_validator(mode='after')
    def validate_dht(self):
        if self.simulated and self.serial_contract != 2:
            raise ValueError('La simulación USB requiere contrato serial 2')
        if self.dht_ok and (self.temperature is None or self.humidity is None):
            raise ValueError('DHT válido requiere temperatura y humedad')
        return self


class Rules(BaseModel):
    baseline: float | None = Field(default=None, ge=10, le=900, allow_inf_nan=False)
    conditioned: bool = False
    warning_ratio: float = Field(default=1.3, ge=1.1, le=4, allow_inf_nan=False)
    alert_ratio: float = Field(default=1.6, ge=1.2, le=5, allow_inf_nan=False)
    persistence_s: float = Field(default=12, ge=4, le=300, allow_inf_nan=False)
    recovery_s: float = Field(default=20, ge=4, le=600, allow_inf_nan=False)
    hysteresis: float = Field(default=0.1, ge=0.02, le=0.3, allow_inf_nan=False)
    temperature_enabled: bool = False
    temperature_warning: float = Field(default=30, ge=10, le=55, allow_inf_nan=False)
    temperature_alert: float = Field(default=35, ge=15, le=65, allow_inf_nan=False)
    temperature_hysteresis: float = Field(default=2, ge=.5, le=5, allow_inf_nan=False)

    @model_validator(mode='after')
    def validate_order(self):
        if self.alert_ratio <= self.warning_ratio:
            raise ValueError('El umbral de alerta debe superar el de aviso')
        if self.temperature_alert <= self.temperature_warning:
            raise ValueError('La temperatura de alerta debe superar la de aviso')
        if self.warning_ratio - self.hysteresis <= 1:
            raise ValueError('La recuperación debe quedar por encima de la base')
        return self


class Device(BaseModel):
    installation_id: str = Field(min_length=8, max_length=120, pattern=r'^[a-zA-Z0-9_-]+$')
    token: str = Field(min_length=20, max_length=4096)
    name: str = Field(default='Android', min_length=1, max_length=80)
    accept_simulations: bool = False
    notification_binding: UUID | None = None
    receiver_id: UUID | None = None


class SerialConnection(BaseModel):
    port: str = Field(min_length=1, max_length=100)


class Simulation(BaseModel):
    scenario: Literal['normal', 'aviso', 'alerta', 'fallo_dht', 'calentamiento', 'sin_datos']
