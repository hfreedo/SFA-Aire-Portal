"""Referencia experimental MQ135: captura real, perfil e historial locales."""
import statistics
import time
import uuid
from fastapi import HTTPException

OBSERVED={'usual_min':70,'usual_max':100,'peak_min':270,'peak_max':315,'trials':10,'suggested_baseline':85,'provisional':True}

class MQCalibration:
    def __init__(self,rt):
        self.rt=rt
        self.capture=None

    def context(self):
        return str(self.rt.cloud.config.classroom_id) if self.rt.cloud.config else 'local'

    def keys(self):
        return 'mq_profile:'+self.context(),'mq_history:'+self.context()

    def reason(self):
        rt=self.rt
        if rt.source!='arduino' or not rt.serial or not rt.latest or not rt.last_valid or time.time()-rt.last_valid>10:
            return 'Conecte el Arduino con lecturas reales recientes.'
        if rt.latest.get('usb_simulation') or rt.latest.get('source')!='arduino':
            return 'La captura necesita sensores reales; el firmware actual transmite una simulación.'
        if not rt.latest.get('warmed_up'):
            return 'Espere la estabilización indicada por el firmware. No sustituye el acondicionamiento del fabricante.'
        return None

    def start(self,duration):
        if self.capture and self.capture['status']=='capturing':
            raise HTTPException(409,'Ya hay una captura en curso.')
        reason=self.reason()
        if reason:raise HTTPException(409,reason)
        self.capture={'id':str(uuid.uuid4()),'context':self.context(),'status':'capturing','started_at':time.time(),'duration_s':duration,'values':[],'rejected':0}

    def cancel(self,reason='Captura cancelada.'):
        if self.capture and self.capture['status']=='capturing':
            self.capture.update(status='cancelled',message=reason)

    def observe(self,sample,now):
        cap=self.capture
        if not cap or cap['status']!='capturing':return
        if cap['context']!=self.context():
            self.cancel('Cambió el aula de esta PC.');return
        if now>=cap['started_at']+cap['duration_s']:
            self.finish();return
        if sample.simulated or not sample.warmed_up or not 10<=sample.mq_raw<=900:
            cap['rejected']+=1;return
        # El firmware real aporta cada muestra; no se cuentan consultas de pantalla.
        cap['values'].append(sample.mq_raw)

    def finish(self):
        cap=self.capture
        if not cap or cap['status']!='capturing':return
        values=sorted(cap['values']);n=len(values)
        if n<20:
            cap.update(status='insufficient',message='Faltan muestras válidas: se requieren al menos 20. Revise conexión y señal.');return
        median=statistics.median(values)
        low=values[round((n-1)*.1)];high=values[round((n-1)*.9)]
        cap.update(status='ready',finished_at=time.time(),result={'baseline':round(median,1),'min':values[0],'max':values[-1],'p10':low,'p90':high,'count':n,'spread_percent':round((high-low)/median*100,1)})

    def proposed(self):
        self.snapshot()
        cap=self.capture
        if not cap or cap['context']!=self.context() or cap['status']!='ready':
            raise HTTPException(409,'Complete una captura real válida antes de aplicar la referencia.')
        return cap['result']

    def record(self,db,rules,origin='manual',metadata=None):
        profile_key,history_key=self.keys()
        old=self.rt.store.setting(profile_key)
        history=self.rt.store.setting(history_key,[])
        history.insert(0,{'id':str(uuid.uuid4()),'baseline':self.rt.rules.baseline,'conditioned':self.rt.rules.conditioned,'profile':old,'saved_at':time.time()})
        profile={'baseline':rules.baseline,'conditioned':rules.conditioned,'origin':origin,'updated_at':time.time(),'metadata':metadata or {}}
        import json
        for key,value in [(profile_key,profile),(history_key,history[:5])]:
            db.execute('INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value)))

    def previous(self,identity):
        _,history_key=self.keys()
        item=next((x for x in self.rt.store.setting(history_key,[]) if x['id']==identity),None)
        if not item:raise HTTPException(409,'La referencia anterior ya no está disponible. Actualice el panel.')
        return item

    def snapshot(self):
        profile_key,history_key=self.keys()
        cap=self.capture
        if cap and cap['context']!=self.context():cap=None
        if cap and cap['status']=='capturing' and time.time()>=cap['started_at']+cap['duration_s']:self.finish()
        public=None
        if cap:
            public={k:v for k,v in cap.items() if k not in ('values','context')}
            public['count']=len(cap['values'])
            public['elapsed_s']=min(cap['duration_s'],max(0,round(time.time()-cap['started_at'])))
        return {'observed':OBSERVED,'profile':self.rt.store.setting(profile_key),'history':self.rt.store.setting(history_key,[]),'capture':public,'capture_reason':self.reason()}
