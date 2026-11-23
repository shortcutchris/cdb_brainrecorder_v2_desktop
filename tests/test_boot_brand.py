import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('boot_brand', ROOT / 'deploy/boot-brand/install.py')
boot = importlib.util.module_from_spec(spec); spec.loader.exec_module(boot)


class BootBrandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.original = ('[pi5]\ndtoverlay=vc4-kms-v3d\n[all]\nauto_initramfs=1\n',
                         'console=tty1 root=PARTUUID=abc-02 rootwait quiet splash\n',
                         '# retained comment\n[Daemon]\nTheme=pix\nShowDelay=0\n')
        for name, text in zip(boot.CONFIGS, self.original):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)

    def tearDown(self): self.temp.cleanup()

    def test_check_is_read_only_and_keeps_desktop_rotation(self):
        runner = Mock()
        result = boot.install(self.root, runner=runner, check=True)
        self.assertEqual(result['status'], 'checked-no-changes')
        runner.assert_not_called()
        self.assertFalse((self.root / boot.THEME).exists())
        self.assertFalse((self.root / 'var').exists())
        self.assertEqual(tuple((self.root / p).read_text() for p in boot.CONFIGS), self.original)

    def test_install_repeat_and_rollback_preserve_existing_boot_options(self):
        runner = Mock()
        result = boot.install(self.root, runner=runner)
        self.assertFalse(result['reboot_performed'])
        self.assertIn('root=PARTUUID=abc-02', (self.root / boot.CONFIGS[1]).read_text())
        self.assertIn('console=tty1', (self.root / boot.CONFIGS[1]).read_text())
        self.assertIn('dtoverlay=vc4-kms-v3d', (self.root / boot.CONFIGS[0]).read_text())
        self.assertIn('ShowDelay=0', (self.root / boot.CONFIGS[2]).read_text())
        self.assertNotIn('video=', (self.root / boot.CONFIGS[1]).read_text())
        runner.assert_called_once_with(['/usr/sbin/update-initramfs', '-u', '-k', 'all'], check=True, timeout=300)
        again = boot.install(self.root, runner=runner)
        self.assertEqual(again['status'], 'already-installed'); self.assertEqual(runner.call_count, 1)
        boot.restore(self.root, Path(result['backup']), runner)
        self.assertEqual(tuple((self.root / p).read_text() for p in boot.CONFIGS), self.original)
        self.assertFalse((self.root / boot.THEME).exists())
        self.assertFalse((self.root / boot.STATE).exists())

    def test_failed_initramfs_rebuild_restores_configuration_and_rebuilds_original(self):
        runner = Mock(side_effect=[subprocess.CalledProcessError(1, 'update-initramfs'), None])
        with self.assertRaises(subprocess.CalledProcessError): boot.install(self.root, runner=runner)
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(tuple((self.root / p).read_text() for p in boot.CONFIGS), self.original)
        self.assertFalse((self.root / boot.THEME).exists())
        self.assertFalse((self.root / boot.STATE).exists())

    def test_reinstallation_can_restore_an_earlier_cdb_theme(self):
        first = boot.install(self.root, runner=Mock(), rotation=90)
        old = {p.name: p.read_bytes() for p in (self.root / boot.THEME).iterdir()}
        second = boot.install(self.root, runner=Mock(), rotation=270)
        boot.restore(self.root, Path(second['backup']), Mock())
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / boot.THEME).iterdir()}, old)
        self.assertEqual(json.loads((self.root / boot.STATE).read_text()), first)

    def test_invalid_cmdline_and_linked_configuration_are_rejected_without_changes(self):
        path = self.root / boot.CONFIGS[1]; path.write_text('root=a\nsecond-line\n')
        with self.assertRaises(ValueError): boot.install(self.root, runner=Mock())
        path.unlink(); path.symlink_to(self.root / boot.CONFIGS[0])
        with self.assertRaises(ValueError): boot.install(self.root, runner=Mock())
        self.assertFalse((self.root / 'var').exists())

    def test_native_portrait_and_landscape_assets_are_present_and_selected(self):
        for rotation in (90, 270):
            assets = boot.payload(boot.SOURCE, rotation)
            self.assertNotIn(b'@ROTATION@', assets['cdb-pios.script'])
            for mode in ('startup', 'shutdown'):
                for view, size in [('landscape', (1280, 720)), ('portrait', (720, 1280))]:
                    png = assets[f'{mode}-{view}.png']
                    self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
                    self.assertEqual(struct.unpack('>II', png[16:24]), size)
        from fleet.releases import allowed
        self.assertFalse(allowed('deploy/boot-brand/install.py'))
