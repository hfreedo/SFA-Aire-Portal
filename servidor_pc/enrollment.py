"""Primera vinculación: identidad local persistente, permiso admin verificado por RPC."""
import secrets
from uuid import UUID
from fastapi import HTTPException
import httpx
from .cloud import CloudConfig

def enroll(rt,connection,room,bearer):
    with rt.lock:
        if rt.cloud.config is not None:raise HTTPException(409,'La PC ya fue vinculada. Actualice el estado.')
        if rt.source!='detenido' or rt.lab.command or rt.cloud.lab_report:raise HTTPException(409,'Detenga la lectura antes de vincular esta PC.')
        if rt.store.rows('select count(*) as n from cloud_outbox')[0]['n']:raise HTTPException(409,'Hay datos pendientes de sincronización.')
        pending=rt.cloud.path.parent/'pc-bindings'/(room+'.json')
        def save(path,cfg):
            path.parent.mkdir(parents=True,exist_ok=True)
            temporary=path.with_suffix('.tmp');temporary.write_text(cfg.model_dump_json(indent=2),encoding='utf-8');temporary.replace(path)
        try:
            target=CloudConfig.model_validate_json(pending.read_text(encoding='utf-8')) if pending.is_file() else CloudConfig(**connection.model_dump(),classroom_id=room,gateway_id=UUID(int=0),gateway_secret=secrets.token_urlsafe(48))
            if target.url!=connection.url or target.publishable_key!=connection.publishable_key or str(target.classroom_id)!=room:raise ValueError('Destino incompatible')
            save(pending,target)
            with httpx.Client(transport=rt.workspace_transport,timeout=12,follow_redirects=False) as client:
                r=client.post(connection.url+'/rest/v1/rpc/aire_enroll_pc',headers={'apikey':connection.publishable_key,'Authorization':'Bearer '+bearer},json={'p_classroom_id':room,'p_origin_id':rt.cloud.origin,'p_secret':target.gateway_secret})
            if r.status_code in (401,403):raise HTTPException(403,'Necesita administración vigente de esta aula.')
            if r.status_code>=400:
                message=r.json().get('message','')
                if message.startswith('CUOTA_'):raise HTTPException(409,'El aula alcanzó su límite preventivo de PC. Revise Administración → PC del aula.')
                raise HTTPException(503,'No se pudo vincular. Reintente; se conserva la identidad de esta PC.')
            result=r.json()
            if result.get('classroom_id')!=room:raise ValueError('Aula incompatible')
            target=CloudConfig.model_validate({**target.model_dump(),'gateway_id':result['gateway_id']})
            save(pending,target)
            with rt.store.transaction() as db:
                db.execute('update incidents set cloud_gateway_id=? where cloud_gateway_id is null',('local:'+rt.cloud.origin,))
            save(rt.cloud.path,target)
        except HTTPException:raise
        except Exception:raise HTTPException(503,'No se pudo guardar la vinculación. Reintente desde esta PC.')
        rt.cloud.config=target;rt.cloud.state='esperando_sincronizacion';rt.cloud.error=None;rt.cloud.next_sync=0
        return {'classroom_id':room,'assigned':True,'current_classroom_id':room}
