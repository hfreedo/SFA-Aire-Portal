"""Controles de la PC dentro del portal cloud; permisos comprobados en Supabase."""

import hashlib

import json

import threading

import time

import secrets

from pathlib import Path

from typing import Literal

from uuid import UUID



import httpx

from fastapi import Depends, HTTPException, Request

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic import BaseModel, Field

from .models import Rules

from .cloud import CloudConfig
from .enrollment import enroll



def connect_serial(rt, port):

    from serial.tools import list_ports

    import serial

    if rt.lab.command:

        raise HTTPException(409, 'Detenga la prueba activa antes de conectar el Arduino.')

    info = next((p for p in list_ports.comports() if p.device == port),None)
    if info is None:

        raise HTTPException(400, 'Puerto no disponible. Refresque la lista.')

    with rt.lock:

        rt.switch('arduino')

        try:

            rt.serial = serial.Serial(port, 115200, timeout=.1, write_timeout=1)

            rt.serial_target = port
            rt.serial_identity = tuple(getattr(info,k,None) for k in ('vid','pid','serial_number'))
            rt.last_monitor = time.time()
            rt.serial.write(b'MONITOR\n')

            rt.serial_state = 'esperando_arduino'

        except Exception:

            rt.switch('detenido')

            raise HTTPException(400, 'No se pudo abrir el puerto. Cierre el monitor serie u otra aplicación que lo esté usando.')



def save_rules(rt, rules, expected=None, origin='manual', metadata=None):

    with rt.lock:

        revision = rt.store.setting('rules_revision', 0)

        if expected is not None and revision != expected:

            raise HTTPException(409, 'Las reglas cambiaron en esta PC. Actualice antes de guardar.')

        with rt.store.transaction() as db:
            if rt.rules.baseline!=rules.baseline or rt.rules.conditioned!=rules.conditioned or origin!='manual':
                rt.mq_calibration.record(db,rules,origin,metadata)

            for key,value in [('rules', rules.model_dump()), ('rules_revision', revision+1)]:

                db.execute('INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(value)))

        rt.rules = rules

        rt.engine.reset()



class WorkspaceCommand(BaseModel):

    classroom_id: UUID

    action: Literal['state','ports','connect','stop','rules','assignment','assign','start_usb_lab','stop_usb_lab','calibration_start','calibration_cancel','calibration_apply','calibration_provisional','calibration_restore']

    duration_s: int = Field(default=180,ge=60,le=600)
    conditioned: bool = False
    history_id: str | None = Field(default=None,max_length=40)

    run_id: UUID | None = None
    allow_push: bool = True
    free_plan_confirmed: bool = False

    port: str | None = Field(default=None, max_length=100)

    rules: Rules | None = None

    rules_revision: int | None = Field(default=None, ge=0)

    model_config = {'extra':'forbid'}



def install_workspace(app, rt):

    bearer=HTTPBearer(auto_error=False)

    permissions={}

    guard=threading.Lock()

    rt.workspace_transport=None



    @app.post('/api/workspace/local')

    def command(body:WorkspaceCommand, request:Request, credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
        # La sincronización mantiene config_lock durante solicitudes de red.
        # Consultar el puerto/lecturas no debe esperar a esa red; las mutaciones
        # conservan el bloqueo y el snapshot vuelve a comprobar la asignación.
        if body.action in ('state','ports','assignment'):
            return execute(body,request,credentials)
        with rt.cloud.config_lock:
            return execute(body,request,credentials)

    def execute(body,request,credentials):

        if credentials is None or len(credentials.credentials)>8192:

            raise HTTPException(401, 'Inicie sesión en el portal.')

        cfg=rt.cloud.config

        connection=cfg or rt.public_connection
        if connection is None:
            raise HTTPException(409, 'Falta la conexión pública de esta instalación.')

        room=str(body.classroom_id)

        key=(hashlib.sha256(credentials.credentials.encode()).hexdigest(),room)

        readonly=body.action in ('state','ports','assignment')

        with guard:

            cached=permissions.get(key)

        if readonly and cached and cached[0]>time.monotonic():

            caps=cached[1]

        else:

            try:

                with httpx.Client(transport=rt.workspace_transport, timeout=8, follow_redirects=False) as client:

                    response=client.post(connection.url+'/rest/v1/rpc/aire_admin_capabilities',

                        headers={'apikey':connection.publishable_key,'Authorization':'Bearer '+credentials.credentials},

                        json={'p_classroom_id':room})

                if response.status_code in (401,403):

                    raise HTTPException(403, 'Solo administradores de esta aula pueden controlar el Arduino.')

                response.raise_for_status()

                caps=response.json()

            except HTTPException:

                raise

            except Exception:

                raise HTTPException(503, 'No se pudieron verificar los permisos. Compruebe la conexión a internet.')

            if not isinstance(caps,dict) or caps.get('classroom_id')!=room or caps.get('can_manage_gateways') is not True:

                raise HTTPException(403, 'No tiene administración sobre esta aula.')

            with guard:

                if len(permissions)>=128:

                    permissions.clear()

                permissions[key]=(time.monotonic()+20,caps)

        if cfg is None:
            if request.client is None or request.client.host not in ('127.0.0.1','::1','testclient'):
                raise HTTPException(403,'Vincule el aula desde el portal de esta PC.')
            if body.action=='assignment':return {'classroom_id':room,'assigned':False,'current_classroom_id':None}
            if body.action=='assign':
                result=enroll(rt,connection,room,credentials.credentials)
                with guard:permissions.clear()
                return result
            raise HTTPException(409,'Primero asigne esta PC al aula seleccionada.')

        if body.action in ('assignment','assign'):

            enabled=any(g.get('id')==str(cfg.gateway_id) and g.get('enabled') is True for g in caps.get('gateways',[]) if isinstance(g,dict))

            if request.client is None or request.client.host not in ('127.0.0.1','::1','testclient'):

                raise HTTPException(403, 'Asigne el aula desde el portal abierto en esta PC: http://127.0.0.1:8767/remoto')

            if body.action=='assign' and room==str(cfg.classroom_id) and not enabled:
                result=enroll(rt,connection,room,credentials.credentials,replace_revoked=True)
                with guard:permissions.clear()
                return result

            if body.action=='assign' and room!=str(cfg.classroom_id):

                with rt.cloud.config_lock, rt.lock:

                    if rt.cloud.config is not cfg:

                        raise HTTPException(409, 'La asignación cambió. Compruebe de nuevo.')

                    if rt.source!='detenido' or rt.lab.command or rt.cloud.lab_report:

                        raise HTTPException(409, 'Detenga la lectura o la prueba actual antes de cambiar de aula.')

                    if rt.store.rows('SELECT count(*) AS n FROM cloud_outbox')[0]['n']:

                        raise HTTPException(409, 'Espere a que se sincronicen los datos pendientes antes de cambiar de aula.')

                    folder=rt.cloud.path.parent/'pc-bindings'

                    def save(path,config):

                        path.parent.mkdir(parents=True,exist_ok=True)

                        temporary=path.with_suffix('.tmp')

                        temporary.write_text(config.model_dump_json(indent=2),encoding='utf-8')

                        temporary.replace(path)

                    try:

                        # Guardar primero permite reintentar incluso si se pierde la respuesta cloud.

                        save(folder/(str(cfg.classroom_id)+'.json'),cfg)

                        target_path=folder/(room+'.json')

                        target=CloudConfig.model_validate_json(target_path.read_text(encoding='utf-8')) if target_path.exists() else cfg.model_copy(update={'classroom_id':body.classroom_id,'gateway_secret':secrets.token_urlsafe(48)})

                        if target.url!=cfg.url or target.publishable_key!=cfg.publishable_key or str(target.classroom_id)!=room:

                            raise ValueError('Configuración de aula incompatible')

                        save(target_path,target)

                        with httpx.Client(transport=rt.workspace_transport,timeout=12,follow_redirects=False) as client:

                            response=client.post(cfg.url+'/rest/v1/rpc/aire_assign_pc',

                                headers={'apikey':cfg.publishable_key,'Authorization':'Bearer '+credentials.credentials},

                                json={'p_classroom_id':room,'p_origin_id':rt.cloud.origin,'p_secret':target.gateway_secret,

                                      'p_previous_gateway_id':str(cfg.gateway_id),'p_previous_secret':cfg.gateway_secret})

                        if response.status_code>=400:

                            message=response.json().get('message','')

                            if message.startswith('CUOTA_RECEPTORES:'):

                                raise HTTPException(409,'Esta aula tiene 10 PC habilitadas. Retire solo equipos que ya no utilice en Administración → PC del aula.')

                            if message.startswith('CUOTA_BASE:'):
                                raise HTTPException(409,'El almacenamiento alcanzó la guarda del plan gratuito. Revise el consumo; retirar una PC no libera el historial.')

                            if response.status_code in (401,403):

                                raise HTTPException(403,'Necesita ser administrador del aula actual y del aula elegida.')

                            raise HTTPException(503,'No se pudo asignar esta PC. Puede reintentar sin duplicar el registro.')

                        result=response.json()

                        if result.get('classroom_id')!=room:

                            raise ValueError('Respuesta de aula incompatible')

                        target=CloudConfig.model_validate({**target.model_dump(),'gateway_id':result['gateway_id']})

                        save(target_path,target)

                        # El historial antiguo mantiene su origen; nunca se reenvía a la nueva aula.

                        with rt.store.transaction() as db:

                            db.execute('UPDATE incidents SET cloud_gateway_id=? WHERE cloud_gateway_id IS NULL',(str(cfg.gateway_id),))

                            db.execute("DELETE FROM settings WHERE key IN ('cloud_last_arduino','cloud_last_simulacion')")

                        save(rt.cloud.path,target)

                    except HTTPException:

                        raise

                    except Exception:

                        raise HTTPException(503,'No se pudo guardar la asignación. La PC conserva el aula anterior; reintente.')

                    rt.cloud.config=target

                    rt.cloud.state,rt.cloud.error='esperando_sincronizacion',None

                    rt.cloud.next_sync=rt.cloud.pause_until=0

                    rt.cloud.last_sync=rt.cloud.budget=rt.cloud.push_worker=None

                    rt.cloud.push_transport='pc'

                    rt.latest=None;rt.last_valid=0;rt.engine.reset()

                    cfg=target

                    with guard:

                        permissions.clear()

                return {'classroom_id':room,'assigned':True,'current_classroom_id':room}

            enabled=any(g.get('id')==str(cfg.gateway_id) and g.get('enabled') is True for g in caps.get('gateways',[]) if isinstance(g,dict))

            return {'classroom_id':room,'assigned':room==str(cfg.classroom_id) and enabled,'current_classroom_id':str(cfg.classroom_id)}

        if room!=str(cfg.classroom_id):

            raise HTTPException(409, 'Esta PC está vinculada a otra aula. Seleccione el aula de esta PC para conectar su Arduino.')

        if not any(g.get('id')==str(cfg.gateway_id) and g.get('enabled') is True for g in caps.get('gateways',[]) if isinstance(g,dict)):

            raise HTTPException(409, 'El acceso de esta PC no está habilitado. Revise PC del aula en Administración.')

        if body.action.startswith('calibration_'):
            with rt.lock:
                if rt.lab.command:
                    raise HTTPException(409,'Finalice el ensayo antes de ajustar la referencia real.')
                if body.action=='calibration_start':rt.mq_calibration.start(body.duration_s)
                elif body.action=='calibration_cancel':rt.mq_calibration.cancel()
                else:
                    if body.rules_revision is None:raise HTTPException(400,'Falta la revisión de las reglas.')
                    if body.action=='calibration_apply':
                        stats=rt.mq_calibration.proposed()
                        next_rules=Rules(**{**rt.rules.model_dump(),'baseline':stats['baseline'],'conditioned':body.conditioned})
                        save_rules(rt,next_rules,body.rules_revision,'captura',stats)
                    elif body.action=='calibration_provisional':
                        next_rules=Rules(**{**rt.rules.model_dump(),'baseline':85,'conditioned':False})
                        save_rules(rt,next_rules,body.rules_revision,'provisional',{'observed':rt.mq_calibration.snapshot()['observed']})
                    elif body.action=='calibration_restore':
                        previous=rt.mq_calibration.previous(body.history_id)
                        next_rules=Rules(**{**rt.rules.model_dump(),'baseline':previous['baseline'],'conditioned':previous['conditioned']})
                        save_rules(rt,next_rules,body.rules_revision,'restauracion',(previous.get('profile') or {}).get('metadata',{}))

        if body.action in ('start_usb_lab','stop_usb_lab'):
            if body.run_id is None:
                raise HTTPException(400,'Falta el identificador del ensayo.')
            if body.action=='start_usb_lab':
                with rt.lock:
                    if rt.source!='arduino' or not rt.serial or not rt.latest or not rt.latest.get('usb_simulation') or time.time()-rt.last_valid>10:
                        raise HTTPException(409,'Conecte el UNO con el firmware de simulación y lecturas recientes.')
                payload={'p_classroom_id':room,'p_gateway_id':str(cfg.gateway_id),'p_run_id':str(body.run_id),
                         'p_allow_push':body.allow_push,'p_free_plan_confirmed':body.free_plan_confirmed}
                rpc='aire_lab_start_usb'
            else:
                if not rt.lab.command or rt.lab.command.id!=str(body.run_id) or rt.lab.command.input_source!='usb':
                    raise HTTPException(409,'Este ensayo USB ya no está activo en esta PC.')
                payload={'p_run_id':str(body.run_id)}
                rpc='aire_lab_stop'
            try:
                with httpx.Client(transport=rt.workspace_transport,timeout=10,follow_redirects=False) as client:
                    result=client.post(cfg.url+'/rest/v1/rpc/'+rpc,
                        headers={'apikey':cfg.publishable_key,'Authorization':'Bearer '+credentials.credentials},json=payload)
                if result.status_code>=400:
                    detail=result.json().get('message','No se pudo autorizar el ensayo.')
                    raise HTTPException(409,detail)
            except HTTPException:raise
            except Exception:raise HTTPException(503,'No se pudo confirmar el ensayo en nube. Compruebe conexión y reintente.')
            if body.action=='stop_usb_lab':
                with rt.lock:rt.lab.stop('cancelado')
            rt.cloud.next_sync=0
            rt.cloud.sync_once(force=True)

        if body.action=='connect':

            if not body.port:

                raise HTTPException(400, 'Seleccione un puerto COM.')

            connect_serial(rt,body.port)

        elif body.action=='stop':

            with rt.lock:

                if rt.lab.command:

                    rt.lab.stop('cancelado')

                rt.switch('detenido')

        elif body.action=='rules':

            if body.rules is None or body.rules_revision is None:

                raise HTTPException(400, 'Faltan las reglas o su versión.')

            save_rules(rt,body.rules,body.rules_revision)

        if body.action=='ports':

            from serial.tools import list_ports

            return {'ports':[{'port':p.device,'description':p.description} for p in list_ports.comports()]}

        with rt.lock:

            if rt.cloud.config is not cfg:
                raise HTTPException(409, 'La asignación cambió. Compruebe de nuevo.')

            state=rt.snapshot()

            return {k:state[k] for k in ['receiver_id','source','state','age_s','latest','serial','error','rules','cloud','usb_lab']} | {

                'classroom_id':room,'gateway_id':str(cfg.gateway_id),

                'rules_revision':rt.store.setting('rules_revision',0),
                'calibration':rt.mq_calibration.snapshot(),

                'port':rt.serial.port if rt.serial else rt.serial_target}

