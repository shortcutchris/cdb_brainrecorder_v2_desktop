"""Install a pinned official model atomically; keep weights out of Git."""
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from services.wake_phrase import MODEL_NAME, MODEL_URL, MODEL_SHA256, model_path, model_ready, PhraseDetector


def main():
    target = model_path()
    if not model_ready():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as directory:
            staging = Path(directory)
            archive = staging/'model.zip'
            with urllib.request.urlopen(MODEL_URL, timeout=60) as source, archive.open('wb') as output:
                shutil.copyfileobj(source, output)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != MODEL_SHA256:
                raise ValueError('Wake-Modell: Prüfsumme stimmt nicht überein.')
            with zipfile.ZipFile(archive) as bundle:
                for name in bundle.namelist():
                    if not (staging/name).resolve().is_relative_to(staging.resolve()):
                        raise ValueError('Wake-Modell: unsicherer Archivpfad.')
                bundle.extractall(staging)
            if target.exists(): raise ValueError('Unvollständiges Modell vorhanden. Bitte vor Neuinstallation prüfen: '+str(target))
            (staging/MODEL_NAME).rename(target)
    PhraseDetector()
    print('Hey Brain: lokale Erkennung bereit.')


if __name__ == '__main__': main()
