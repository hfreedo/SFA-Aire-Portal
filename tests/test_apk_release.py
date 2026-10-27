import hashlib,json,tempfile,unittest
from pathlib import Path
from herramientas.apk_release import load_release

class ApkRelease(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.folder=self.root/'Entregas';self.folder.mkdir()
  self.payload=b'fixture apk, not installable';(self.folder/'current.apk').write_bytes(self.payload)
  self.manifest={'file':'current.apk','version':'0.7.0','sha256':hashlib.sha256(self.payload).hexdigest()}
 def save(self): (self.folder/'ANDROID_ACTUAL.json').write_text(json.dumps(self.manifest))
 def test_exact_file_and_digest(self):
  self.save();self.assertEqual(load_release(self.root)['path'],(self.folder/'current.apk').resolve())
 def test_does_not_serve_changed_apk(self):
  self.save();(self.folder/'current.apk').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'no coincide'):load_release(self.root)
 def test_never_accepts_other_paths(self):
  for name in ['../private.apk','C:/private.apk','folder/private.apk','secret.json']:
   self.manifest['file']=name;self.save()
   with self.assertRaises(ValueError):load_release(self.root)
