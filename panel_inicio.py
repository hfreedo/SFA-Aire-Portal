"""Panel ejecutable de esta instalación. No contiene claves ni un receptor duplicado."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser


def project_root():
    base=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    for candidate in (base,base.parent):
        if (candidate/'iniciar.py').is_file() and (candidate/'servidor_pc/main.py').is_file():return candidate.resolve()
    raise RuntimeError('Coloque el panel dentro de la carpeta completa de SFA Aire, junto a iniciar.py.')


class Controller:
    def __init__(self,root):self.root=root;self.children=[];self.wifi_children=[]

    def port_candidates(self,demo):
        default=8872 if demo else 8766
        try:
            saved=json.loads((self.root/'data/panel/runtime-ports.json').read_text(encoding='utf-8')).get('demo' if demo else 'receiver')
        except (OSError,ValueError,AttributeError):saved=None
        candidates=([saved] if type(saved) is int and default<=saved<=default+20 else [])
        return list(dict.fromkeys([*candidates,*range(default,default+21)]))

    def remember_port(self,demo,port):
        target=self.root/'data/panel/runtime-ports.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        try:
            saved=json.loads(target.read_text(encoding='utf-8'))
            if not isinstance(saved,dict):saved={}
        except (OSError,ValueError):saved={}
        if saved.get('demo' if demo else 'receiver')==port:return
        saved['demo' if demo else 'receiver']=port
        temporary=target.with_suffix(f'.{os.getpid()}.{threading.get_ident()}.tmp')
        temporary.write_text(json.dumps(saved),encoding='utf-8');temporary.replace(target)

    @staticmethod
    def port_available(port):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as probe:
            try:probe.bind(('127.0.0.1',port));return True
            except OSError:return False

    @staticmethod
    def fetch(url):
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url,timeout=2) as r:return json.load(r)

    def child(self,script,args,env,log_name):
        python=self.root/'.venv/Scripts/python.exe'
        worker=self.root/'SFA_Aire_Receptor.exe'
        if getattr(sys,'frozen',False) and worker.is_file():
            modes={'iniciar.py':'receiver','herramientas/compartir_apk_wifi.py':'apk-wifi'}
            if script not in modes:raise RuntimeError('Componente portable no permitido.')
            command=[str(worker),modes[script],*args]
        else:
            if not python.is_file():raise RuntimeError('Falta preparar el entorno de esta instalación. Ejecute preparar_entorno.bat.')
            command=[str(python),str(self.root/script),*args]
        folder=self.root/'data/panel';folder.mkdir(parents=True,exist_ok=True)
        with (folder/log_name).open('a',encoding='utf-8') as log:
            proc=subprocess.Popen(command,cwd=self.root,env=env,
                stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.children.append(proc);return proc

    def ensure(self,mode):
        demo=mode=='demo'
        fingerprint=hashlib.sha256(str(self.root).encode()).hexdigest()[:12]
        def ready(port):
            base=f'http://127.0.0.1:{port}'
            h=self.fetch(base+'/health')
            if not isinstance(h,dict) or h.get('app')!='sfa-aire' or h.get('workspace')!=fingerprint:return None
            if demo and self.fetch(base+'/api/public-config').get('configured'):raise RuntimeError('El puerto de demostración tiene una conexión cloud activa. No se utiliza como demo.')
            self.remember_port(demo,port)
            return base
        candidates=self.port_candidates(demo)
        # Reutilizar primero el receptor propio, incluso si otro puerto está libre.
        for candidate in candidates:
            if self.port_available(candidate):continue
            try:
                existing=ready(candidate)
                if existing:return existing
            except (OSError,urllib.error.URLError,TimeoutError,ValueError):pass
        port=next((candidate for candidate in candidates if self.port_available(candidate)),None)
        if port is None:raise RuntimeError('No hay un puerto local disponible para esta instalación. Cierre una instancia que ya no utilice y vuelva a intentar.')
        env=os.environ.copy()
        if demo:
            isolated=self.root/'artifacts/panel-demo';isolated.mkdir(parents=True,exist_ok=True)
            absent=self.root/'artifacts/panel-demo-sin-cloud.json'
            if absent.exists():raise RuntimeError('El destino reservado sin nube no debe contener un archivo de configuración.')
            env.update(SFA_DATA_DIR=str(isolated),SFA_CLOUD_CONFIG=str(absent),SFA_PUBLIC_CONFIG=str(absent),GOOGLE_APPLICATION_CREDENTIALS='')
            env.pop('SFA_API_TOKEN',None)
        proc=self.child('iniciar.py',['--no-browser','--port',str(port)],env,'demo.log' if demo else 'receptor.log')
        for _ in range(40):
            try:
                existing=ready(port)
                if existing:return existing
                raise RuntimeError('El puerto seleccionado acaba de ocuparse. Vuelva a intentar; se conservará la otra aplicación.')
            except (OSError,urllib.error.URLError,TimeoutError):
                if proc.poll() is not None:raise RuntimeError('No arrancó el receptor. Consulte data/panel/'+('demo.log' if demo else 'receptor.log'))
                time.sleep(.25)
        raise RuntimeError('El receptor no respondió dentro del plazo. Revise el diagnóstico y no abra otra instancia.')

    def runtime_status(self,mode='cloud'):
        demo=mode=='demo'
        fingerprint=hashlib.sha256(str(self.root).encode()).hexdigest()[:12]
        for port in self.port_candidates(demo):
            if self.port_available(port):continue
            try:
                health=self.fetch(f'http://127.0.0.1:{port}/health')
                if isinstance(health,dict) and health.get('app')=='sfa-aire' and health.get('workspace')==fingerprint:
                    return {'running':True,'url':f'http://127.0.0.1:{port}','port':port,'instance_id':health.get('instance_id'),'can_shutdown':health.get('can_shutdown',False)}
            except (OSError,ValueError,TimeoutError,urllib.error.URLError):pass
        return {'running':False}

    def stop(self,mode='cloud'):
        state=self.runtime_status(mode)
        if not state['running']:return 'El servidor de esta instalación ya está detenido.'
        if not state.get('instance_id') or not state.get('can_shutdown'):
            raise RuntimeError('La instancia abierta es anterior al control de detención. Reinicie el receptor para usar esta función.')
        directory=self.root/'artifacts/panel-demo' if mode=='demo' else self.root/'data'
        token=(directory/'clave_conexion.txt').read_text(encoding='utf-8').strip()
        request=urllib.request.Request(state['url']+'/api/maintenance/shutdown',method='POST',
            data=json.dumps({'instance_id':state['instance_id']}).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=3) as response:
            if response.status!=200:raise RuntimeError('No se confirmó la detención.')
        for _ in range(60):
            time.sleep(.25)
            try:
                health=self.fetch(state['url']+'/health')
                if health.get('instance_id')!=state['instance_id']:
                    return 'Se detuvo la instancia anterior; otra instancia ya está activa.'
            except (OSError,ValueError,TimeoutError,urllib.error.URLError):
                return 'Servidor detenido. La configuración y el historial se conservaron.'
        return 'Detención solicitada. Hay operaciones terminando; vuelva a comprobar el estado.'

    def mode_url(self,mode):
        base=self.ensure(mode)
        if mode=='demo':return base+'/remoto?demo=1'
        if mode=='cloud':return base+'/remoto'
        token=(self.root/'data/clave_conexion.txt').read_text(encoding='utf-8').strip()
        return base+'/#token='+token

    def stop_monitoring(self):
        """Detiene sólo servicios cuya identidad corresponde a esta carpeta."""
        for mode in ('cloud','demo'):
            self.stop(mode)
            if self.runtime_status(mode)['running']:
                raise RuntimeError('El monitoreo todavía está terminando. Espere y vuelva a intentar antes de salir.')
        for proc in self.wifi_children:
            if proc.poll() is None:
                if os.name=='nt':
                    # El ejecutable onefile tiene un proceso hijo: cerrar sólo el
                    # bootloader dejaría la descarga temporal funcionando.
                    result=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if result.returncode and proc.poll() is None:
                        raise RuntimeError('No se pudo cerrar la descarga temporal iniciada desde este panel.')
                else:proc.terminate()
                proc.wait(timeout=5)

    @staticmethod
    def lan_ip():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.connect(('8.8.8.8',80));host=sock.getsockname()[0]
        ip=ipaddress.ip_address(host)
        if not ip.is_private or ip.is_loopback:raise RuntimeError('Conecte la PC a una red local para compartir la APK.')
        return host

    def share(self):
        from herramientas.apk_release import load_release
        host=self.lan_ip();meta=self.root/'data/apk-wifi.json'
        release=load_release(self.root);expected=release['sha256']
        def ready():
            data=json.loads(meta.read_text(encoding='utf-8'))
            if not data['url'].startswith(f'http://{host}:8870/') or data.get('sha256')!=expected:return None
            request=urllib.request.Request(data['url'],method='HEAD')
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=2) as response:
                if response.status==200:return data
            return None
        try:
            data=ready()
            if data:return data,max(1,int((1800-(time.time()-meta.stat().st_mtime))/60))
        except (OSError,urllib.error.URLError,ValueError,TimeoutError):pass
        proc=self.child('herramientas/compartir_apk_wifi.py',['--host',host],os.environ.copy(),'apk-wifi.log')
        self.wifi_children.append(proc)
        for _ in range(40):
            try:
                data=ready()
                if data:return data,30
            except (OSError,urllib.error.URLError,ValueError,TimeoutError):pass
            if proc.poll() is not None:raise RuntimeError('No se pudo abrir la descarga. Revise data/panel/apk-wifi.log y el puerto 8870.')
            time.sleep(.25)
        raise RuntimeError('La descarga no respondió. No se modificó el firewall.')


def gui(root):
    import tkinter as tk
    from tkinter import ttk, messagebox
    from herramientas.qr_wifi import png_qr
    if sys.platform=='win32' and getattr(sys,'frozen',False):
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('SFA.Aire.Panel')
    c=Controller(root)
    window=tk.Tk();window.title('SFA Aire · Inicio')
    height=min(630,window.winfo_screenheight()-100)
    window.geometry(f'900x{max(580,height)}');window.minsize(820,min(610,max(580,height)))
    bg='#F2F5EF';ink='#244D43';muted='#52665C';line='#D8E2D6'
    window.configure(bg=bg)
    style=ttk.Style(window);style.theme_use('clam')
    style.configure('TButton',font=('Segoe UI',11),padding=(14,9),background='#EBF0E7',foreground=ink,borderwidth=0)
    style.map('TButton',background=[('active','#DCE7D7'),('pressed','#CFDDC9')],foreground=[('disabled','#7E8C82')])
    style.configure('Primary.TButton',font=('Segoe UI',12,'bold'),background=ink,foreground='white',padding=(22,13))
    style.map('Primary.TButton',background=[('disabled','#A1B2A5'),('pressed','#183B31'),('active','#326756')],foreground=[('disabled','#F7F9F5')])
    style.configure('Exit.TButton',foreground='#824A3C')
    logo=root/'Branding/logo/sfa-aire-verde-transparente.png'
    if logo.exists():
        image=tk.PhotoImage(file=str(logo));window.brand_image=image
        window.iconphoto(True,image)
        window.small_logo=image.subsample(max(1,image.width()//42))
    ico=root/'Branding/logo/sfa-aire.ico'
    if ico.exists():window.iconbitmap(str(ico))
    outer=tk.Frame(window,bg=bg);outer.pack(fill='both',expand=True,padx=24,pady=14)
    header=tk.Frame(outer,bg=bg);header.pack(fill='x',pady=(0,6))
    if hasattr(window,'small_logo'):tk.Label(header,image=window.small_logo,bg=bg).pack(side='left',padx=(0,14))
    title=tk.Frame(header,bg=bg);title.pack(side='left')
    tk.Label(title,text='SFA Aire',font=('Segoe UI',21,'bold'),fg=ink,bg=bg).pack(anchor='w')
    tk.Label(title,text='Monitoreo ambiental de aulas',font=('Segoe UI',11),fg=muted,bg=bg).pack(anchor='w')
    tk.Label(header,text='WINDOWS · 0.8.0',font=('Segoe UI',9,'bold'),fg=muted,bg=bg).pack(side='right')
    status=tk.StringVar(value='Preparado. Abrir SFA Aire inicia el servidor automáticamente.')
    server=tk.StringVar(value='Comprobando el monitoreo de esta PC…')
    demo=tk.StringVar(value='')
    buttons=[];busy=False;closed=threading.Event();exit_dialog=None
    def center(dialog):
        dialog.update_idletasks()
        x=max(0,min(window.winfo_rootx()+(window.winfo_width()-dialog.winfo_reqwidth())//2,window.winfo_screenwidth()-dialog.winfo_reqwidth()-20))
        y=max(0,min(window.winfo_rooty()+(window.winfo_height()-dialog.winfo_reqheight())//2,window.winfo_screenheight()-dialog.winfo_reqheight()-70))
        dialog.geometry(f'+{x}+{y}')
    def label(parent,text,size=11,bold=False,color=muted,wrap=0):
        item=tk.Label(parent,text=text,font=('Segoe UI',size,'bold' if bold else 'normal'),fg=color,bg=parent['bg'],justify='left',anchor='w',wraplength=wrap)
        item.pack(anchor='w',fill='x');return item
    def button(parent,text,command,primary=False,**pack):
        item=ttk.Button(parent,text=text,command=command,style='Primary.TButton' if primary else 'TButton')
        item.pack(**pack);buttons.append(item);return item
    def work(action,callback):
        nonlocal busy
        if busy:return
        busy=True
        for item in buttons:item.state(['disabled'])
        status.set('Un momento, preparando la acción…')
        def finish(result,error):
            nonlocal busy
            busy=False
            for item in buttons:
                if item.winfo_exists():item.state(['!disabled'])
            if error:
                status.set('No se pudo completar. Revise el mensaje para continuar.')
                messagebox.showerror('SFA Aire',str(error),parent=exit_dialog or window)
            else:callback(result)
        def worker():
            try:result=action();error=None
            except Exception as exc:result=None;error=exc
            if not closed.is_set():
                try:window.after(0,lambda:finish(result,error))
                except (RuntimeError,tk.TclError):pass
        threading.Thread(target=worker,daemon=True).start()
    def show_state(states):
        real,example=states
        server.set('● Monitoreo activo en esta PC' if real['running'] else '○ Monitoreo detenido')
        demo.set('Demostración abierta · datos ficticios' if example['running'] else 'Demostración detenida')
    def states():return c.runtime_status(),c.runtime_status('demo')
    def refresh():work(states,lambda value:(show_state(value),status.set('Estado actualizado.')))
    def open_system(mode='cloud',arduino=False):
        def prepare():
            url=c.mode_url(mode)
            if arduino:url+='?view=arduino'
            return url,states()
        def opened(value):
            webbrowser.open(value[0]);show_state(value[1])
            status.set('SFA Aire abierto en el navegador. El monitoreo continúa mientras el servidor esté activo.' if mode=='cloud' else 'Demostración abierta: datos ficticios y sin notificaciones reales.')
        work(prepare,opened)
    def stop():
        def stopped(value):show_state(value);status.set('Monitoreo y demostración detenidos. Su configuración e historial se conservan.')
        work(lambda:(c.stop_monitoring(),states())[1],stopped)
    def destroy():closed.set();window.destroy()
    def request_close():
        nonlocal exit_dialog
        if busy:
            status.set('Espere a que termine la acción antes de cerrar.');return
        if exit_dialog is not None:exit_dialog.lift();return
        dialog=tk.Toplevel(window);exit_dialog=dialog;dialog.title('Salir de SFA Aire');dialog.configure(bg=bg);dialog.resizable(False,False);dialog.transient(window)
        if ico.exists():dialog.iconbitmap(str(ico))
        body=tk.Frame(dialog,bg=bg,padx=24,pady=24);body.pack(fill='both',expand=True)
        label(body,'¿Cómo desea salir?',17,True,ink)
        label(body,'Puede dejar el monitoreo funcionando o detenerlo antes de salir.',11,wrap=460).pack_configure(pady=(10,16))
        def cancel():
            nonlocal exit_dialog
            if busy:return
            dialog.grab_release();dialog.destroy();exit_dialog=None
        button(body,'Detener monitoreo y salir',lambda:work(c.stop_monitoring,lambda _:destroy()),primary=True,fill='x',pady=(0,10))
        button(body,'Cerrar panel y mantener monitoreo',destroy,fill='x',pady=(0,10))
        button(body,'Volver',cancel,fill='x')
        dialog.protocol('WM_DELETE_WINDOW',cancel);dialog.bind('<Escape>',lambda _:cancel());dialog.grab_set()
        center(dialog)
    window.protocol('WM_DELETE_WINDOW',request_close)
    hero=tk.Frame(outer,bg='white',highlightbackground=line,highlightthickness=1,padx=20,pady=10);hero.pack(fill='x')
    label(hero,'SU AULA, EN UN SOLO LUGAR',9,True)
    label(hero,'Medir, revisar y recibir avisos',19,True,ink).pack_configure(pady=(7,7))
    label(hero,'Aulas, personas, sensores y pruebas desde el mismo sistema.',11)
    actions=tk.Frame(hero,bg='white');actions.pack(fill='x',pady=(9,0))
    button(actions,'Abrir SFA Aire',open_system,primary=True,side='left')
    button(actions,'Conectar Arduino',lambda:open_system(arduino=True),side='left',padx=(12,0))
    label(hero,'El servidor se inicia al abrir. Para Arduino: seleccione el aula y el puerto USB.',10,wrap=700).pack_configure(pady=(8,0))
    services=tk.Frame(outer,bg=bg);services.pack(fill='x',pady=(8,8))
    description=tk.Frame(services,bg=bg);description.pack(side='left',fill='x',expand=True)
    tk.Label(description,textvariable=server,font=('Segoe UI',11,'bold'),fg=ink,bg=bg,anchor='w').pack(fill='x')
    tk.Label(description,textvariable=demo,font=('Segoe UI',10),fg=muted,bg=bg,anchor='w').pack(fill='x',pady=(4,0))
    button(services,'Actualizar estado',refresh,side='left',padx=(0,8))
    button(services,'Detener monitoreo',stop,side='left')
    label(outer,'HERRAMIENTAS',9,True).pack_configure(pady=(0,9))
    tools=tk.Frame(outer,bg=bg);tools.pack(fill='both',expand=True)
    def show_qr(value):
        data,minutes=value;status.set('Descarga temporal preparada. Sólo se comparte la aplicación Android.')
        folder=root/'artifacts';folder.mkdir(exist_ok=True);qr=folder/'QR_instalar_SFA_Aire_wifi.png';qr.write_bytes(png_qr(data['url']))
        dialog=tk.Toplevel(window);dialog.title('SFA Aire · Instalar Android');dialog.configure(bg=bg);dialog.transient(window);dialog.resizable(False,False)
        if ico.exists():dialog.iconbitmap(str(ico))
        body=tk.Frame(dialog,bg=bg,padx=24,pady=20);body.pack()
        label(body,'Instalar en Android',18,True,ink)
        label(body,'App '+data['version']+' · PC y celular en la misma Wi-Fi',11).pack_configure(pady=(5,12))
        photo=tk.PhotoImage(file=str(qr));dialog.qr=photo;tk.Label(body,image=photo,bg='white').pack(pady=8)
        label(body,f'Enlace temporal · aproximadamente {minutes} minutos',10).pack_configure(pady=8)
        entry=ttk.Entry(body,width=55,font=('Segoe UI',10));entry.insert(0,data['url']);entry.state(['readonly']);entry.pack(fill='x',pady=8)
        def copy():window.clipboard_clear();window.clipboard_append(data['url'])
        ttk.Button(body,text='Copiar enlace',command=copy).pack(fill='x',pady=5)
        center(dialog)
    for col,(heading,description,text,command) in enumerate([
        ('Explorar una demostración','Datos ficticios, sin avisos reales.','Abrir demostración',lambda:open_system('demo')),
        ('App para Android','Descarga por QR en la misma Wi-Fi.','Instalar por Wi-Fi',lambda:work(c.share,show_qr))]):
        tools.columnconfigure(col,weight=1,uniform='cards');tools.rowconfigure(0,weight=1)
        card=tk.Frame(tools,bg='white',highlightbackground=line,highlightthickness=1,padx=19,pady=10);card.grid(row=0,column=col,sticky='nsew',padx=(0,12) if col==0 else (0,0))
        label(card,heading,14,True,ink)
        label(card,description,11,wrap=330).pack_configure(pady=(5,6))
        button(card,text,command,side='bottom',fill='x')
    footer=tk.Frame(outer,bg=bg);footer.pack(side='bottom',before=header,fill='x',pady=(10,0))
    button(footer,'Guía de uso',lambda:webbrowser.open((root/'docs/GUIA_USO.html').as_uri()),side='left')
    button(footer,'Salir…',request_close,side='right')
    tk.Label(outer,textvariable=status,font=('Segoe UI',10),fg=ink,bg=bg,anchor='w',justify='left',wraplength=800).pack(side='bottom',before=header,fill='x',pady=(5,0))
    window.after(200,refresh)
    window.mainloop()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-check',action='store_true')
    parser.add_argument('--mode',choices=['cloud','local','demo'])
    args=parser.parse_args()
    root=project_root()
    if args.self_check:
        c=Controller(root);started=[]
        try:
            before=len(c.children);cloud=c.ensure('cloud')
            if len(c.children)>before:started.append('cloud')
            before=len(c.children);demo=c.ensure('demo')
            if len(c.children)>before:started.append('demo')
            assert not c.fetch(demo+'/api/public-config')['configured']
            assert c.fetch(cloud+'/health')['app']=='sfa-aire'
            import tkinter as tk
            from tkinter import ttk
            from herramientas.qr_wifi import png_qr
            screen=tk.Tk();screen.withdraw()
            try:
                ttk.Style(screen).theme_use('clam');ttk.Button(screen,text='Prueba').pack()
                logo=tk.PhotoImage(file=str(root/'Branding/logo/sfa-aire-verde-transparente.png'))
                qr_path=root/'artifacts/panel-demo/qr-self-check.png';qr_path.write_bytes(png_qr('http://127.0.0.1/test'))
                qr=tk.PhotoImage(file=str(qr_path));assert logo.width()>0 and qr.width()>0;screen.update_idletasks()
            finally:screen.destroy()
            report={'executable':bool(getattr(sys,'frozen',False)),'isolated_demo_without_cloud':True,'tk_assets_verified':True,'browser_opened':False,'push_sent':False}
            (root/'artifacts/panel-self-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        finally:
            for mode in reversed(started):
                try:c.stop(mode)
                except (OSError,RuntimeError,ValueError):pass
            for child in c.children:
                if child.poll() is None:child.terminate();child.wait(timeout=10)
    elif args.mode:
        webbrowser.open(Controller(root).mode_url(args.mode))
    else:gui(root)


if __name__=='__main__':main()
