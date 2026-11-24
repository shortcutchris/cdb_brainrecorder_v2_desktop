import importlib.util
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('usb_audio_helper', SOURCE / 'deploy/usb-audio-recovery/cdb-usb-audio-recover.py')
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


class UsbAudioHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sys = self.root / 'sys'
        for name in ('bus/pci/devices', 'bus/usb/devices', 'class/block', 'class/net', 'bus/pci/drivers/xhci_hcd'):
            (self.sys / name).mkdir(parents=True, exist_ok=True)
        self.driver = self.sys / 'bus/pci/drivers/xhci_hcd'
        for name in ('bind', 'unbind'):
            (self.driver / name).write_text('')
        self.controller = self.pci('0001:01:00.0')
        self.now = 0
        self.writes = []
        self.helper = HELPER.Recovery(self.sys, write=self.write,
                                      sleep=self.sleep, monotonic=lambda: self.now, settle_seconds=1)

    def tearDown(self):
        self.tmp.cleanup()

    def sleep(self, seconds):
        self.now += seconds

    def write(self, path, value):
        self.writes.append((path.name, value))

    def pci(self, bdf, *, parent=None, identity=HELPER.PCI_ID):
        path = (parent or self.sys / 'devices') / bdf
        path.mkdir(parents=True)
        for name, value in zip(('vendor', 'device', 'class'), identity):
            (path / name).write_text(value)
        (path / 'driver').symlink_to(self.driver)
        (self.sys / 'bus/pci/devices' / bdf).symlink_to(path)
        return path

    def usb(self, name, vendor, product, kind, *, parent=None, interface=None):
        parent = parent or self.controller
        path = parent / name
        path.mkdir()
        for key, value in [('idVendor', vendor), ('idProduct', product), ('bDeviceClass', kind)]:
            (path / key).write_text(value)
        (self.sys / 'bus/usb/devices' / name).symlink_to(path)
        if interface:
            self.interface(path, name + ':1.0', interface)
        return path

    def interface(self, device, name, kind):
        path = device / name
        path.mkdir()
        (path / 'bInterfaceClass').write_text(kind)
        (self.sys / 'bus/usb/devices' / name).symlink_to(path)
        return path

    def normal_tree(self):
        root = self.usb('usb3', '1d6b', '0002', '09', interface='09')
        hub = self.usb('3-1', '2109', '3431', '09', parent=root, interface='09')
        sound = self.usb('3-1.1', '0020', '0b21', '00', parent=hub, interface='01')
        self.interface(sound, '3-1.1:1.2', '03')
        return root, hub, sound

    def assert_blocked(self):
        result = self.helper.recover()
        self.assertFalse(result['available'], result)
        self.assertFalse(result['recovered'], result)
        self.assertEqual(self.writes, [])
        return result

    def test_known_soundbar_and_hub_are_safe(self):
        self.normal_tree()
        result = self.helper.check()
        self.assertTrue(result['supported'])
        self.assertTrue(result['available'])
        self.assertTrue(result['device_present'])
        self.assertEqual(result['controller'], '0001:01:00.0')

    def test_single_rebind_and_exact_target(self):
        self.normal_tree()
        result = self.helper.recover()
        self.assertTrue(result['recovered'])
        self.assertEqual(self.writes, [('unbind', '0001:01:00.0'), ('bind', '0001:01:00.0')])

    def test_dead_controller_without_children_is_allowed_but_not_false_success(self):
        self.assertTrue(self.helper.check()['available'])
        result = self.helper.recover()
        self.assertFalse(result['recovered'])
        self.assertFalse(result['device_present'])
        self.assertEqual(len(self.writes), 2)
        self.assertGreaterEqual(self.now, 1)
        self.assertLessEqual(self.now, 1.5)

    def test_dead_controller_can_reenumerate_soundbar(self):
        def write(path, value):
            self.writes.append((path.name, value))
            if path.name == 'bind':
                self.normal_tree()
        self.helper.write = write
        self.assertTrue(self.helper.recover()['recovered'])
        self.assertEqual(len(self.writes), 2)

    def test_unknown_usb_blocks_even_if_not_storage(self):
        self.usb('3-2', '1234', 'abcd', '03')
        self.assert_blocked()

    def test_known_id_with_storage_interface_blocks(self):
        _, _, sound = self.normal_tree()
        self.interface(sound, '3-1.1:1.3', '08')
        self.assert_blocked()

    def test_known_id_with_network_interface_blocks(self):
        _, _, sound = self.normal_tree()
        self.interface(sound, '3-1.1:1.3', '02')
        self.assert_blocked()

    def test_unmounted_block_device_blocks(self):
        block = self.controller / 'orphaned/block/sda'
        block.mkdir(parents=True)
        (self.sys / 'class/block/sda').symlink_to(block)
        self.assert_blocked()

    def test_network_device_blocks(self):
        net = self.controller / 'orphaned/net/eth1'
        net.mkdir(parents=True)
        (self.sys / 'class/net/eth1').symlink_to(net)
        self.assert_blocked()

    def test_external_storage_and_network_are_untouched(self):
        self.normal_tree()
        for category, name in [('block', 'sda'), ('net', 'eth0')]:
            other = self.sys / 'devices/platform' / name
            other.mkdir(parents=True)
            (self.sys / 'class' / category / name).symlink_to(other)
        self.assertTrue(self.helper.recover()['recovered'])
        self.assertEqual(len(self.writes), 2)

    def test_pci_child_blocks(self):
        self.pci('0001:02:00.0', parent=self.controller, identity=('0x1234', '0x5678', '0x020000'))
        self.assert_blocked()

    def test_multiple_matching_controllers_block(self):
        self.pci('0002:01:00.0')
        self.assert_blocked()

    def test_wrong_pci_class_is_not_supported(self):
        (self.controller / 'class').write_text('0x060400')
        result = self.assert_blocked()
        self.assertFalse(result['supported'])

    def test_incomplete_topology_blocks(self):
        self.normal_tree()
        (self.sys / 'bus/usb/devices/3-1.1').resolve().joinpath('idVendor').unlink()
        self.assert_blocked()

    def test_sysfs_escape_blocks(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.sys / 'bus/usb/devices/unexpected').symlink_to(outside)
        self.assert_blocked()

    def test_changed_topology_before_unbind_blocks(self):
        self.normal_tree()
        check = self.helper.check
        calls = []
        def racing_check():
            if calls:
                self.usb('3-2', '1234', 'abcd', '00')
            calls.append(True)
            return check()
        self.helper.check = racing_check
        self.assert_blocked()

    def test_bind_failure_is_reported_without_repeated_reset(self):
        self.normal_tree()
        def failing_write(path, value):
            self.writes.append((path.name, value))
            if path.name == 'bind':
                raise OSError('bind failed')
        self.helper.write = failing_write
        result = self.helper.recover()
        self.assertFalse(result['available'])
        self.assertFalse(result['recovered'])
        self.assertEqual(len(self.writes), 2)

    def test_timeout_during_unbind_still_attempts_bind(self):
        self.normal_tree()
        def failing_write(path, value):
            self.writes.append((path.name, value))
            if path.name == 'unbind':
                raise HELPER.Refused('Zeitlimit')
        self.helper.write = failing_write
        result = self.helper.recover()
        self.assertFalse(result['available'])
        self.assertFalse(result['recovered'])
        self.assertEqual(self.writes, [('unbind', '0001:01:00.0'), ('bind', '0001:01:00.0')])

    def test_cli_uses_exclusive_lock_and_bounded_alarm(self):
        import contextlib
        import io
        from unittest.mock import patch
        lock = self.root / 'helper.lock'
        with patch.object(HELPER, 'verify_installation'), patch.object(HELPER, 'LOCK_PATH', lock), patch.object(HELPER.os, 'fstat') as info, patch.object(HELPER.fcntl, 'flock') as flock, patch.object(HELPER.signal, 'signal', return_value=0), patch.object(HELPER.signal, 'alarm') as alarm, patch.object(HELPER.Recovery, 'check', return_value={'available': True}), contextlib.redirect_stdout(io.StringIO()):
            info.return_value.st_mode = 0o100600
            info.return_value.st_uid = 0
            self.assertEqual(HELPER.main(['check']), 0)
            self.assertEqual(flock.call_args.args[1], HELPER.fcntl.LOCK_EX | HELPER.fcntl.LOCK_NB)
            self.assertEqual(alarm.call_args_list[0].args, (35,))
            self.assertEqual(alarm.call_args_list[-1].args, (0,))

    def test_cli_refuses_concurrent_recovery(self):
        import contextlib
        import io
        from unittest.mock import patch
        lock = self.root / 'helper.lock'
        with patch.object(HELPER, 'verify_installation'), patch.object(HELPER, 'LOCK_PATH', lock), patch.object(HELPER.os, 'fstat') as info, patch.object(HELPER.fcntl, 'flock', side_effect=BlockingIOError), patch.object(HELPER.signal, 'signal', return_value=0), patch.object(HELPER.signal, 'alarm'), patch.object(HELPER.Recovery, 'recover') as recover, contextlib.redirect_stdout(io.StringIO()):
            info.return_value.st_mode = 0o100600
            info.return_value.st_uid = 0
            self.assertEqual(HELPER.main(['recover']), 2)
            recover.assert_not_called()

    def test_term_and_int_during_unbind_still_finish_cleanup_bind(self):
        import contextlib
        import io
        from unittest.mock import patch
        self.normal_tree()
        for signum in (HELPER.signal.SIGTERM, HELPER.signal.SIGINT):
            with self.subTest(signal=signum):
                self.writes.clear()
                handlers = {}
                lock = self.root / ('lock-' + str(signum))
                def register(number, handler):
                    handlers[number] = handler
                    return 0
                def interrupted_write(path, value):
                    self.writes.append((path.name, value))
                    if path.name == 'unbind':
                        handlers[signum](signum, None)
                self.helper.write = interrupted_write
                with patch.object(HELPER, 'verify_installation'), patch.object(HELPER, 'LOCK_PATH', lock), patch.object(HELPER.os, 'fstat') as info, patch.object(HELPER.fcntl, 'flock'), patch.object(HELPER.signal, 'signal', side_effect=register), patch.object(HELPER.signal, 'alarm'), patch.object(HELPER, 'Recovery', return_value=self.helper), contextlib.redirect_stdout(io.StringIO()):
                    info.return_value.st_mode = 0o100600
                    info.return_value.st_uid = 0
                    self.assertEqual(HELPER.main(['recover']), 2)
                self.assertEqual(self.writes, [('unbind', '0001:01:00.0'), ('bind', '0001:01:00.0')])

    def test_cli_rejects_extra_arguments_and_arbitrary_commands(self):
        import contextlib
        import io
        for args in ([], ['check', '/tmp'], ['recover', '0001:01:00.0'], ['reset'], ['--sysfs=/tmp']):
            with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(HELPER.main(args), 2)

    def test_installer_grants_only_two_fixed_commands(self):
        text = (SOURCE / 'scripts/install-usb-audio-recovery.sh').read_text()
        self.assertIn('/usr/local/sbin/cdb-usb-audio-recover check, /usr/local/sbin/cdb-usb-audio-recover recover', text)
        self.assertIn('visudo -cf', text)
        self.assertIn('NOSETENV:', text)
        self.assertIn('-o root -g root -m 0755', text)
        self.assertNotIn('systemctl restart', text)


if __name__ == '__main__':
    unittest.main()
