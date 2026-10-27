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
    def __init__(self,root):self.root=root;self.children=[]

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
    from tkinter import ttk,messagebox
    from herramientas.qr_wifi import png_qr
    c=Controller(root);window=tk.Tk();window.title('SFA Aire · Panel de inicio');window.geometry(f'{min(940,window.winfo_screenwidth()-60)}x{min(740,window.winfo_screenheight()-80)}');window.minsize(min(820,window.winfo_screenwidth()-60),min(650,window.winfo_screenheight()-80))
    bg='#F4F6F2';ink='#244D43';muted='#62796E';window.configure(bg=bg)
    style=ttk.Style();style.theme_use('clam')
    style.configure('Go.TButton',font=('Segoe UI',11,'bold'),foreground='white',background=ink,padding=(16,12),borderwidth=0)
    style.map('Go.TButton',background=[('active','#326756'),('disabled','#97A99E')])
    outer=tk.Frame(window,bg=bg);outer.pack(fill='both',expand=True,padx=24,pady=18)
    header=tk.Frame(outer,bg=bg);header.pack(fill='x')
    logo=root/'Branding/logo/sfa-aire-verde-transparente.png'
    if logo.exists():
        image=tk.PhotoImage(file=str(logo));image=image.subsample(max(1,image.width()//54));window.brand_image=image
        tk.Label(header,image=image,bg=bg).pack(side='left',padx=(0,16))
    title=tk.Frame(header,bg=bg);title.pack(side='left')
    tk.Label(title,text='SFA Aire',font=('Segoe UI',23,'bold'),fg=ink,bg=bg).pack(anchor='w')
    tk.Label(title,text='Panel de control de esta instalación',font=('Segoe UI',11),fg=muted,bg=bg).pack(anchor='w')
    ttk.Button(header,text='Guía de uso',command=lambda:webbrowser.open((root/'docs/GUIA_USO.html').as_uri())).pack(side='right')
    tk.Label(outer,text='Un solo entorno para tu aula',font=('Segoe UI',18,'bold'),fg=ink,bg=bg).pack(anchor='w',pady=(16,5))
    tk.Label(outer,text='Configura aulas, personas y Arduino desde el sistema. Usa los controles para gestionar este servidor.',font=('Segoe UI',11),fg=muted,bg=bg).pack(anchor='w',pady=(0,18))
    controls=tk.Frame(outer,bg='white',highlightbackground='#DCE5DC',highlightthickness=1,padx=12,pady=10);controls.pack(fill='x',pady=(0,14))
    grid=tk.Frame(outer,bg=bg);grid.pack(fill='both',expand=True);buttons=[]
    server_state=tk.StringVar(value='Servidor: comprobando…')
    tk.Label(controls,textvariable=server_state,bg='white',fg=ink,font=('Segoe UI',10,'bold')).pack(side='left')
    closed=threading.Event()
    def close_panel():closed.set();window.destroy()
    window.protocol('WM_DELETE_WINDOW',close_panel)
    status=tk.StringVar(value='Listo para iniciar. La demostración no envía notificaciones.')

    def done(result,error,callback):
        for b in buttons:b.state(['!disabled'])
        if error:status.set('No se completó la acción.');messagebox.showerror('SFA Aire',str(error),parent=window)
        else:callback(result)

    def work(action,callback):
        for b in buttons:b.state(['disabled'])
        status.set('Preparando el modo seleccionado…')
        def worker():
            try:result=action();error=None
            except Exception as exc:result=None;error=exc
            if not closed.is_set():
                try:window.after(0,lambda:done(result,error,callback))
                except (RuntimeError,tk.TclError):pass
        threading.Thread(target=worker,daemon=True).start()

    def open_mode(mode):
        def opened(url):webbrowser.open(url);status.set('Modo abierto en el navegador. El panel puede permanecer aquí.')
        work(lambda:c.mode_url(mode),opened)

    def show_qr(result):
        data,minutes=result;status.set('Descarga Wi-Fi preparada. Solo se comparte la APK.')
        folder=root/'artifacts';folder.mkdir(exist_ok=True);qr=folder/'QR_instalar_SFA_Aire_wifi.png';qr.write_bytes(png_qr(data['url']))
        dialog=tk.Toplevel(window);dialog.title('Instalar SFA Aire por Wi-Fi');dialog.configure(bg=bg);dialog.resizable(False,False)
        tk.Label(dialog,text='Instalar app Android v'+data.get('version','0.6.2'),font=('Segoe UI',17,'bold'),bg=bg,fg=ink).pack(padx=25,pady=(20,10))
        photo=tk.PhotoImage(file=str(qr));dialog.qr=photo;tk.Label(dialog,image=photo,bg='white').pack(padx=25,pady=8)
        tk.Label(dialog,text='Celular y PC en la misma red. Escanee el QR.',font=('Segoe UI',11),bg=bg,fg=ink).pack(padx=20,pady=5)
        tk.Label(dialog,text=f'Disponible aproximadamente {minutes} min. No requiere USB.',font=('Segoe UI',10),bg=bg,fg=muted).pack(pady=5)
        entry=ttk.Entry(dialog,width=65);entry.insert(0,data['url']);entry.state(['readonly']);entry.pack(padx=20,pady=12)
        def copy():window.clipboard_clear();window.clipboard_append(data['url'])
        ttk.Button(dialog,text='Copiar enlace',style='Go.TButton',command=copy).pack(pady=(0,20))

    def show_server(value):
        server_state.set('Servidor en ejecución · puerto '+str(value['port']) if value['running'] else 'Servidor detenido')
        status.set('Estado del servidor actualizado.')
    def check_server():work(c.runtime_status,show_server)
    def start_server():
        def started(value):show_server(value);status.set('Servidor iniciado. Puede abrir SFA Aire.')
        def prepare():c.ensure('cloud');return c.runtime_status()
        work(prepare,started)
    def stop_server():
        def stopped(result):show_server(result[1]);status.set(result[0])
        work(lambda:(c.stop(),c.runtime_status()),stopped)
    for text,command in [('Comprobar',check_server),('Iniciar',start_server),('Detener servidor',stop_server)]:
        control=ttk.Button(controls,text=text,command=command);control.pack(side='right',padx=4);buttons.append(control)
    window.after(200,check_server)

    modes=[('SISTEMA SFA AIRE','Monitoreo y configuración','Aulas, personas, Arduino USB, simulaciones y notificaciones en el mismo portal.','Abrir SFA Aire',lambda:open_mode('cloud')),
        ('ARDUINO EN EL PORTAL','Conexión de la maqueta','Abre el sistema y entra a Conexión Arduino: buscar COM, conectar y detener la lectura.','Configurar Arduino',lambda:work(lambda:c.mode_url('cloud')+'?view=arduino',lambda url:webbrowser.open(url))),
        ('DEMOSTRACIÓN','Explorar sin nube','Recorrer pantallas con datos ficticios. Entorno separado, sin mensajes reales.','Abrir demostración',lambda:open_mode('demo')),
        ('APP ANDROID','Instalar por Wi-Fi','Descargar la APK en el celular con un QR temporal, usando la misma red.','Mostrar descarga',lambda:work(c.share,show_qr))]
    for index,(eyebrow,heading,description,label,command) in enumerate(modes):
        row,col=divmod(index,2);grid.columnconfigure(col,weight=1);grid.rowconfigure(row,weight=1)
        card=tk.Frame(grid,bg='white',highlightbackground='#DCE5DC',highlightthickness=1,padx=17,pady=13);card.grid(row=row,column=col,sticky='nsew',padx=(0,12) if col==0 else (0,0),pady=(0,12))
        tk.Label(card,text=eyebrow,font=('Segoe UI',9,'bold'),fg=muted,bg='white').pack(anchor='w')
        tk.Label(card,text=heading,font=('Segoe UI',15,'bold'),fg=ink,bg='white').pack(anchor='w',pady=(6,3))
        tk.Label(card,text=description,font=('Segoe UI',10),fg=muted,bg='white',wraplength=340,justify='left').pack(anchor='w',pady=(0,9))
        button=ttk.Button(card,text=label,style='Go.TButton',command=command);button.pack(fill='x',side='bottom');buttons.append(button)
    tk.Label(outer,textvariable=status,font=('Segoe UI',10),fg=ink,bg='#E7EFE5',anchor='w',padx=12,pady=10).pack(fill='x',pady=(5,8))
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
