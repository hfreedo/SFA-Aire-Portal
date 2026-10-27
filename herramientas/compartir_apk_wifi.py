"""Descarga temporal de UNA APK propia. No expone carpetas, cuentas ni el receptor."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from apk_release import load_release

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',required=True)
    parser.add_argument('--port',type=int,default=8870)
    args=parser.parse_args()
    release=load_release(ROOT)
    apk=release['path'];version=release['version']
    payload=apk.read_bytes()
    token=secrets.token_urlsafe(18)
    base='/'+token
    digest=hashlib.sha256(payload).hexdigest()
    page=('''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Instalar SFA Aire</title><body style="font-family:system-ui;max-width:600px;margin:40px auto;padding:20px;background:#f4f6f2;color:#193d35">
<h1>SFA Aire</h1><p>App Android v'''+version+'''</p><p><a style="display:inline-block;padding:18px;background:#255c4b;color:white;border-radius:10px" href="'''+base+'''/apk">Descargar APK</a></p>
<p>Abre el archivo descargado e instala SFA Aire. Si Android lo solicita, permite a tu navegador instalar esta aplicación.</p>
<p>Después abre <b>SFA Aire</b> e inicia sesión. La conexión del proyecto ya está preconfigurada.</p>
<p>Esta página no solicita contraseñas. La descarga estará disponible durante treinta minutos.</p></body></html>''').encode('utf-8')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):self.respond(False)
        def do_HEAD(self):self.respond(True)
        def respond(self,head):
            path=self.path.split('?',1)[0]
            if path in (base,base+'/'):body,kind=page,'text/html; charset=utf-8'
            elif path==base+'/apk':body,kind=payload,'application/vnd.android.package-archive'
            else:self.send_error(404);return
            self.send_response(200)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            if path.endswith('/apk'):self.send_header('Content-Disposition','attachment; filename="'+apk.name+'"')
            self.end_headers()
            if not head:
                try:self.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError):pass
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    url=f'http://{args.host}:{args.port}{base}'
    (ROOT/'data/apk-wifi.json').write_text(json.dumps({'url':url,'sha256':digest,'version':version,'expires_after_minutes':30}),encoding='utf-8')
    print('Descarga temporal preparada: '+url,flush=True)
    print('Solo se comparte la APK. No se modifican reglas de firewall.',flush=True)
    threading.Timer(1800,server.shutdown).start()
    try:server.serve_forever()
    finally:server.server_close()


if __name__=='__main__':main()
