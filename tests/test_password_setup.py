import json
from pathlib import Path
import tempfile
import unittest

import httpx
from herramientas.cambiar_clave_admin import change_password


class PasswordSetup(unittest.TestCase):
    def test_change_verifies_login_without_persisting_new_password(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'secrets').mkdir()
            config = {'project_id': 'example', 'url': 'https://example.supabase.co', 'publishable_key': 'sb_publishable_test'}
            account = {'project_id': 'example', 'url': config['url'], 'email': 'test@example.test', 'password': 'old-test-password'}
            (root / 'secrets/supabase-public.json').write_text(json.dumps(config))
            path = root / 'secrets/acceso-inicial-admin.json'
            path.write_text(json.dumps(account))
            calls = []

            def respond(request):
                calls.append(request.method)
                data = json.loads(request.content)
                if request.method == 'PUT':
                    self.assertEqual(data['password'], 'new-test-password')
                    self.assertEqual(request.headers['Authorization'], 'Bearer fake-test-token')
                    return httpx.Response(200, json={'id': 'test-user'})
                return httpx.Response(200, json={'access_token': 'fake-test-token', 'user': {'email': account['email']}})

            result = change_password(root, 'new-test-password', 'new-test-password', httpx.MockTransport(respond))
            self.assertTrue(result['login_verified'])
            self.assertEqual(calls, ['POST', 'PUT', 'POST'])
            self.assertNotIn('password', json.loads(path.read_text()))
            self.assertFalse(any('new-test-password' in p.read_text() for p in (root / 'secrets').iterdir()))

    def test_mismatch_never_contacts_provider(self):
        with self.assertRaisesRegex(ValueError, 'no coinciden'):
            change_password(Path('not-needed'), 'first-test-password', 'second-test-password')

    def test_rejected_change_preserves_initial_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'secrets').mkdir()
            config = {'project_id': 'example', 'url': 'https://example.supabase.co', 'publishable_key': 'sb_publishable_test'}
            account = {**config, 'email': 'test@example.test', 'password': 'old-test-password'}
            (root / 'secrets/supabase-public.json').write_text(json.dumps(config))
            path = root / 'secrets/acceso-inicial-admin.json'
            path.write_text(json.dumps(account))

            def respond(request):
                if request.method == 'PUT':
                    return httpx.Response(422, json={'code': 'weak_password'})
                return httpx.Response(200, json={'access_token': 'fake-test-token', 'user': {'email': account['email']}})

            with self.assertRaisesRegex(ValueError, 'más fuerte'):
                change_password(root, 'new-test-password', 'new-test-password', httpx.MockTransport(respond))
            self.assertEqual(json.loads(path.read_text())['password'], 'old-test-password')
