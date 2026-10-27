"""La entrega conserva módulos de código sin abrir datos de ejecución o secretos."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('packaging_policy',Path(__file__).resolve().parents[1]/'herramientas/empaquetar.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PackagingPolicy(unittest.TestCase):
    def test_source_data_package_is_included(self):
        for source in ['main','test','androidTest']:
            self.assertTrue(module.allowed(module.ROOT/f'android_app/app/src/{source}/java/org/sfa/aire/data/network/Policy.kt'))
    def test_runtime_data_stays_excluded(self):
        for name in ['data/aire.db','nested/data/session.json','android_app/app/src/main/assets/data/private.json']:
            self.assertFalse(module.allowed(module.ROOT/name))
    def test_exception_does_not_allow_secrets_or_build_outputs(self):
        for name in ['android_app/app/src/main/java/org/sfa/aire/data/.env','android_app/app/src/main/java/org/sfa/aire/data/secrets/key.json','android_app/app/src/main/java/org/sfa/aire/data/session/private.keystore','android_app/app/build/Session.kt','secrets/firebase-cloud-account.json']:
            self.assertFalse(module.allowed(module.ROOT/name))

    def test_all_production_kotlin_sources_survive_packaging(self):
        sources=list((module.ROOT/'android_app/app/src/main/java').rglob('*.kt'))
        self.assertTrue(sources)
        excluded=[p.relative_to(module.ROOT).as_posix() for p in sources if not module.allowed(p)]
        self.assertEqual([],excluded)

    def test_all_frontend_sources_survive_packaging(self):
        sources=[p for p in (module.ROOT/'interfaz_web/src').rglob('*') if p.is_file() and p.suffix in {'.ts','.tsx','.css'}]
        self.assertTrue(sources)
        self.assertEqual([],[p.relative_to(module.ROOT).as_posix() for p in sources if not module.allowed(p)])
        self.assertFalse(module.allowed(module.ROOT/'interfaz_web/src/data/secrets/key.json'))
