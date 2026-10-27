"""Inicio local o LAN. No necesita servicios de nube para simulación/USB."""
import argparse
import os
import hashlib
import socket
from pathlib import Path
import threading
import webbrowser
import uvicorn
from servidor_pc.main import create_app


def reserve_listener(host,port):
    listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        listener.bind((host,port))
        listener.listen(128)
        listener.set_inheritable(True)
        return listener
    except OSError:
        listener.close()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lan', action='store_true', help='Escuchar en 0.0.0.0 para la app Android en la misma red')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--remote', action='store_true', help='Abrir portal remoto, sin necesitar la clave del panel local')
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    host='0.0.0.0' if args.lan else '127.0.0.1'
    # Reservar ANTES de abrir SQLite o procesar comandos del laboratorio.
    try:
        listener=reserve_listener(host,args.port)
    except OSError:
        import httpx
        try:
            health=httpx.get(f'http://127.0.0.1:{args.port}/health',timeout=2).json()
            own=hashlib.sha256(str(Path(__file__).resolve().parent).encode()).hexdigest()[:12]
            if health.get('app')=='sfa-aire' and health.get('workspace')==own:
                print('SFA Aire ya está funcionando. Se conserva el receptor existente.')
                if not args.no_browser:
                    existing_key=(Path(os.getenv('SFA_DATA_DIR',Path(__file__).parent/'data'))/'clave_conexion.txt').read_text(encoding='utf-8').strip()
                    webbrowser.open(f'http://127.0.0.1:{args.port}/remoto' if args.remote else f'http://127.0.0.1:{args.port}/#token={existing_key}')
                raise SystemExit(0)
        except (httpx.HTTPError,ValueError,OSError):
            pass
        raise SystemExit(f'Puerto {args.port} ocupado. No se inició otro receptor ni se modificaron sus datos.')
    app = create_app()
    rt = app.state.runtime
    key_file = Path(os.getenv('SFA_DATA_DIR', Path(__file__).parent / 'data')) / 'clave_conexion.txt'
    key_file.write_text(rt.token, encoding='utf-8')
    print(f'Clave de conexión del prototipo: {key_file.resolve()}')
    if args.lan:
        print('Modo LAN: use en Android la IP de esta PC y el puerto indicado. Red privada de pruebas.')
    if not args.no_browser:
        url = f'http://127.0.0.1:{args.port}/remoto' if args.remote else f'http://127.0.0.1:{args.port}/#token={rt.token}'
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    try:
        server=uvicorn.Server(uvicorn.Config(app,host=host,port=args.port))
        rt.shutdown_callback=lambda:setattr(server,'should_exit',True)
        server.run(sockets=[listener])
    finally:
        listener.close()
