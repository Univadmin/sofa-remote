import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from server.browser_install import install_browser

class BrowserInstallTests(unittest.TestCase):
    def test_replace_and_recover(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'bundle';source.mkdir();state=root/'state';state.mkdir()
            (source/'manifest.json').write_text(json.dumps({'manifest_version':3,'version':'0.4.4'}))
            (source/'background.js').write_text('new')
            target=state/'browser';target.mkdir();(target/'old.js').write_text('old')
            self.assertEqual(install_browser(source,state),'0.4.4')
            self.assertEqual((target/'background.js').read_text(),'new')
            self.assertFalse((target/'old.js').exists())
            target.rename(state/'browser.previous')
            install_browser(source,state)
            self.assertTrue((target/'manifest.json').exists())
            self.assertFalse((state/'browser.previous').exists())

    def test_failed_swap_restores_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'bundle';source.mkdir();state=root/'state';state.mkdir()
            (source/'manifest.json').write_text(json.dumps({'manifest_version':3,'version':'0.4.4'}))
            target=state/'browser';target.mkdir();(target/'old.js').write_text('old')
            rename=Path.rename
            def fail(path,destination):
                if path.name=='browser.pending': raise OSError('locked')
                return rename(path,destination)
            with patch.object(Path,'rename',fail),self.assertRaises(OSError): install_browser(source,state)
            self.assertEqual((target/'old.js').read_text(),'old')
