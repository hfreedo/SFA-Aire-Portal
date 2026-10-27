"""Reglas de demostración relativas al ADC; no son un índice sanitario."""
from dataclasses import dataclass, field
from .models import Rules, Sample


@dataclass
class Decision:
    state: str
    ratio: float | None
    transition: str | None = None
    causes: list[str] = field(default_factory=list)


class Engine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.level = 'normal'
        self.candidate = None
        self.since = 0.0
        self.last = None

    def evaluate(self, sample: Sample, rules: Rules, now: float) -> Decision:
        if self.last is not None and now - self.last > 10:
            self.candidate = None
        self.last = now
        ratio = sample.mq_raw / rules.baseline if rules.baseline else None
        health = ('fallo_sensor' if not sample.dht_ok or sample.mq_raw in (0, 1023)
                  else 'calentando' if not sample.warmed_up
                  else 'sin_calibrar' if not rules.conditioned or ratio is None else None)
        if health:
            self.candidate = None
            return Decision(health, ratio)
        target = ('alerta' if ratio >= rules.alert_ratio else
                  'aviso' if ratio >= rules.warning_ratio else 'normal')
        temp_level = ('alerta' if rules.temperature_enabled and sample.temperature >= rules.temperature_alert else
                      'aviso' if rules.temperature_enabled and sample.temperature >= rules.temperature_warning else 'normal')
        order = {'normal': 0, 'aviso': 1, 'alerta': 2}
        causes = (['mq135'] if target != 'normal' else []) + (['temperatura'] if temp_level != 'normal' else [])
        if order[temp_level] > order[target]:
            target = temp_level
        if order[target] < order[self.level]:
            threshold = rules.alert_ratio if self.level == 'alerta' else rules.warning_ratio
            if ratio > threshold - rules.hysteresis:
                target = self.level
            temp_threshold = rules.temperature_alert if self.level == 'alerta' else rules.temperature_warning
            if rules.temperature_enabled and sample.temperature > temp_threshold-rules.temperature_hysteresis:
                target = self.level
        if target == self.level:
            self.candidate = None
            return Decision(self.level, ratio, causes=causes)
        if target != self.candidate:
            self.candidate, self.since = target, now
        delay = rules.persistence_s if order[target] > order[self.level] else rules.recovery_s
        if now - self.since >= delay:
            self.level, self.candidate = target, None
            return Decision(target, ratio, target, causes)
        return Decision(self.level, ratio, causes=causes)
