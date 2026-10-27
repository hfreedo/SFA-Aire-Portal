"""Elección local de la primera contraseña. Nunca imprime ni conserva la nueva clave."""
from datetime import datetime, timezone
import json
from pathlib import Path
import threading

import httpx

ROOT = Path(__file__).resolve().parents[1]


def write_private(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def change_password(root, password, repeated, transport=None):
    if password != repeated:
        raise ValueError('Las dos contraseñas no coinciden.')
    if len(password) < 8:
        raise ValueError('Usa al menos 8 caracteres; puedes elegir una frase fácil de recordar.')
    directory = Path(root) / 'secrets'
    config = json.loads((directory / 'supabase-public.json').read_text(encoding='utf-8'))
    account_path = directory / 'acceso-inicial-admin.json'
    account = json.loads(account_path.read_text(encoding='utf-8'))
    if (config['url'] != 'https://' + config['project_id'] + '.supabase.co'
            or config['url'] != account['url'] or config['project_id'] != account['project_id']
            or not config['publishable_key'].startswith('sb_publishable_')):
        raise ValueError('La configuración no corresponde a la cuenta del proyecto.')
    if not account.get('password'):
        raise ValueError('La contraseña inicial ya fue reemplazada. Usa la nueva para entrar al portal.')
    headers = {'apikey': config['publishable_key'], 'Content-Type': 'application/json'}
    base = config['url'] + '/auth/v1'
    with httpx.Client(timeout=15, transport=transport, follow_redirects=False) as client:
        session = client.post(base + '/token?grant_type=password', headers=headers,
                              json={'email': account['email'], 'password': account['password']})
        if not session.is_success:
            raise ValueError('No se pudo iniciar la sesión de la cuenta. El cambio no se realizó.')
        session_data = session.json()
        if session_data.get('user', {}).get('email', '').lower() != account['email'].lower():
            raise ValueError('La sesión no corresponde a esta cuenta.')
        response = client.put(base + '/user', headers={**headers,
                              'Authorization': 'Bearer ' + session_data['access_token']},
                              json={'password': password})
        if not response.is_success:
            try:
                code = response.json().get('error_code') or response.json().get('code')
            except ValueError:
                code = None
            messages = {'same_password': 'Elige una contraseña diferente a la inicial.',
                        'weak_password': 'Supabase solicita una contraseña más fuerte. Prueba una frase más larga.',
                        'reauthentication_needed': 'Supabase solicita una nueva verificación de identidad.'}
            raise ValueError(messages.get(code, 'Supabase no aceptó el cambio. La contraseña inicial sigue vigente.'))
        # Tras aceptar el proveedor, eliminar la copia de la contraseña inicial.
        # La contraseña elegida solo vive en memoria durante esta operación.
        metadata = {k: v for k, v in account.items() if k != 'password'}
        metadata.update(password_changed_by_user=True,
                        password_changed_at=datetime.now(timezone.utc).isoformat(),
                        note='Contraseña definida por su titular. No se conserva una copia aquí.')
        write_private(account_path, metadata)
        try:
            verified = client.post(base + '/token?grant_type=password', headers=headers,
                                   json={'email': account['email'], 'password': password})
            login_verified = verified.is_success and verified.json().get('user', {}).get('email', '').lower() == account['email'].lower()
        except (httpx.HTTPError, ValueError):
            verified, login_verified = None, False
        result = {'changed': True, 'login_verified': login_verified}
        if login_verified:
            fresh = verified.json()
            write_private(directory / 'admin-auth-session.json',
                          {k: fresh[k] for k in ('access_token', 'refresh_token', 'expires_in', 'token_type') if k in fresh})
        write_private(directory / 'resultado-cambio-clave.json', result)
        return result


def main():
    import tkinter as tk
    from tkinter import ttk
    window = tk.Tk()
    window.title('SFA Aire · Elige tu contraseña')
    window.geometry('530x390')
    window.resizable(False, False)
    content = ttk.Frame(window, padding=24)
    content.pack(fill='both', expand=True)
    ttk.Label(content, text='Elige una contraseña que puedas recordar',
              font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 10))
    account = json.loads((ROOT / 'secrets/acceso-inicial-admin.json').read_text(encoding='utf-8'))
    ttk.Label(content, text=account['email']).pack(anchor='w')
    ttk.Label(content, text='Se actualizará en Supabase. No se mostrará en el chat\nni se guardará una copia de tu contraseña nueva.').pack(anchor='w', pady=12)
    first, second = tk.StringVar(), tk.StringVar()
    for label, variable in [('Nueva contraseña', first), ('Repite la contraseña', second)]:
        ttk.Label(content, text=label).pack(anchor='w')
        entry = ttk.Entry(content, textvariable=variable, show='●', width=62)
        entry.pack(fill='x', pady=(3, 10))
    status = tk.StringVar(value='Puedes usar una frase fácil de recordar, de al menos 8 caracteres.')
    ttk.Label(content, textvariable=status, wraplength=470).pack(anchor='w', pady=(0, 12))

    def finished(message, success=False):
        status.set(message)
        first.set('')
        second.set('')
        if success:
            button.configure(text='Cerrar', command=window.destroy, state='normal')
        else:
            button.configure(state='normal')

    def submit():
        password, repeated = first.get(), second.get()
        if password != repeated or len(password) < 8:
            status.set('Escribe la misma contraseña en ambos campos, de al menos 8 caracteres.')
            return
        button.configure(state='disabled')
        status.set('Guardando en Supabase y comprobando el acceso…')

        def work():
            try:
                result = change_password(ROOT, password, repeated)
                message = ('Contraseña cambiada y acceso comprobado. Ya puedes usarla en SFA Aire.'
                           if result['login_verified'] else 'Contraseña cambiada. Falta comprobar el acceso en el portal.')
                window.after(0, lambda: finished(message, True))
            except ValueError as error:
                window.after(0, lambda message=str(error): finished(message))
            except Exception:
                window.after(0, lambda: finished('No se pudo completar la comprobación. Revisaré el estado antes de reintentar.'))
        threading.Thread(target=work, daemon=True).start()

    button = ttk.Button(content, text='Guardar mi contraseña', command=submit)
    button.pack(fill='x')
    print('Ventana de cambio de contraseña preparada. No se registran contraseñas.', flush=True)
    window.mainloop()


if __name__ == '__main__':
    main()
