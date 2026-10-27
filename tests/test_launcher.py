import unittest
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from iniciar import reserve_listener
from panel_inicio import Controller


class Launcher(unittest.TestCase):
    def test_reservation_prevents_duplicate_receiver(self):
        first=reserve_listener('127.0.0.1',0)
        try:
            port=first.getsockname()[1]
            with self.assertRaises(OSError):reserve_listener('127.0.0.1',port)
        finally:first.close()

    def test_reservation_can_be_released(self):
        first=reserve_listener('127.0.0.1',0)
        port=first.getsockname()[1];first.close()
        second=reserve_listener('127.0.0.1',port);second.close()


class PanelPorts(unittest.TestCase):
    def setUp(self):
        self.directory=TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.controller=Controller(self.root)
        self.identity=hashlib.sha256(str(self.root).encode()).hexdigest()[:12]

    def test_other_installation_uses_another_port_and_is_preserved(self):
        running={8766:'another-installation'}
        def fetch(url):
            port=int(url.split(':')[2].split('/')[0])
            return {'app':'sfa-aire','workspace':running[port]}
        def launch(script,args,env,log):
            self.assertEqual(script,'iniciar.py')
            self.assertEqual(args,['--no-browser','--port','8767'])
            running[8767]=self.identity
            return Mock()
        with patch.object(self.controller,'port_candidates',return_value=[8766,8767]),patch.object(self.controller,'port_available',side_effect=lambda p:p not in running),patch.object(self.controller,'fetch',side_effect=fetch),patch.object(self.controller,'child',side_effect=launch) as child:
            self.assertEqual(self.controller.ensure('cloud'),'http://127.0.0.1:8767')
            self.assertEqual(self.controller.ensure('local'),'http://127.0.0.1:8767')
            child.assert_called_once()
        self.assertEqual(running[8766],'another-installation')
        self.assertEqual(json.loads((self.root/'data/panel/runtime-ports.json').read_text())['receiver'],8767)
        self.assertEqual(self.controller.port_candidates(False)[0],8767)

    def test_existing_owned_port_is_reused_before_starting_another(self):
        with patch.object(self.controller,'port_candidates',return_value=[8766,8767]),patch.object(self.controller,'port_available',side_effect=lambda p:p==8766),patch.object(self.controller,'fetch',return_value={'app':'sfa-aire','workspace':self.identity}),patch.object(self.controller,'child') as child:
            self.assertEqual(self.controller.ensure('cloud'),'http://127.0.0.1:8767')
            child.assert_not_called()

    def test_all_occupied_never_starts_or_stops_other_processes(self):
        with patch.object(self.controller,'port_candidates',return_value=[8766]),patch.object(self.controller,'port_available',return_value=False),patch.object(self.controller,'fetch',return_value={'app':'other'}),patch.object(self.controller,'child') as child:
            with self.assertRaisesRegex(RuntimeError,'No hay un puerto'):
                self.controller.ensure('cloud')
            child.assert_not_called()

    def test_untrusted_saved_port_cannot_select_remote_or_arbitrary_destination(self):
        path=self.root/'data/panel/runtime-ports.json';path.parent.mkdir(parents=True)
        for value in ['http://example.invalid',True,80,65535]:
            path.write_text(json.dumps({'receiver':value}))
            self.assertEqual(self.controller.port_candidates(False),list(range(8766,8787)))

    def test_demo_still_rejects_an_owned_cloud_runtime(self):
        def fetch(url):
            return {'configured':True} if url.endswith('public-config') else {'app':'sfa-aire','workspace':self.identity}
        with patch.object(self.controller,'port_candidates',return_value=[8872]),patch.object(self.controller,'port_available',return_value=False),patch.object(self.controller,'fetch',side_effect=fetch),patch.object(self.controller,'child') as child:
            with self.assertRaisesRegex(RuntimeError,'conexión cloud activa'):
                self.controller.ensure('demo')
            child.assert_not_called()

    def test_status_and_stop_preserve_foreign_installation(self):
        with patch.object(self.controller,'port_candidates',return_value=[8766]),patch.object(self.controller,'port_available',return_value=False),patch.object(self.controller,'fetch',return_value={'app':'sfa-aire','workspace':'foreign'}),patch.object(self.controller,'child') as child:
            self.assertEqual(self.controller.runtime_status(),{'running':False})
            self.assertIn('ya está detenido',self.controller.stop())
            child.assert_not_called()

    def test_old_runtime_cannot_be_force_killed(self):
        with patch.object(self.controller,'runtime_status',return_value={'running':True,'can_shutdown':False}):
            with self.assertRaisesRegex(RuntimeError,'anterior al control'):
                self.controller.stop()
