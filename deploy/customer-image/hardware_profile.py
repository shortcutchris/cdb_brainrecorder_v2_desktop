"""Apply explicit hardware choices to a fresh factory root only."""
import json
from pathlib import Path

PCIE = '\n# CDB Pi 5 with Waveshare PCIe USB board (Gen 1 acceptance profile)\n[pi5]\ndtparam=pciex1\ndtparam=pciex1_tperst_clk_ms=100\ndtparam=pciex1_gen=1\n[all]\n'


def install(root):
    root = Path(root)
    if not (root / '.cdb-image-build').is_file():
        raise ValueError('Refusing: not a fresh factory root')
    config = json.loads((root / 'etc/cdb-factory-image.json').read_text())
    if not config.get('pcie_usb_board'):
        return False
    path = root / 'boot/firmware/config.txt'
    original = path.read_text()
    if PCIE in original:
        return False
    # Never silently override an independently configured PCIe profile.
    if any(line.strip().startswith('dtparam=pciex1') for line in original.splitlines()):
        raise ValueError('Existing PCIe configuration requires review')
    path.write_text(original.rstrip() + '\n' + PCIE)
    return True


if __name__ == '__main__':
    install('/')
