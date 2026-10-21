#!/usr/bin/env python3
"""Build/validate a fixed German speech pack OFF the production Pi.

Optional build-only dependencies: ptts==0.4.0, numpy. No audio device is opened.
Never downloads models, installs runtime dependencies or changes app settings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.announcements import PHRASES, PACK_VERSION, load_pack


def build(model, output):
    import numpy as np
    import ptts
    model, output = Path(model).resolve(), Path(output).absolute()
    if output.exists(): raise ValueError('Ziel existiert bereits; neuen Ordner verwenden.')
    for name in ('config.json', 'tokenizer.json', 'model.q8.gguf', 'default-voice.safetensors'):
        if not (model / name).is_file(): raise ValueError('Lokale Modelldatei fehlt: ' + name)
    output.parent.mkdir(parents=True, exist_ok=True)
    ptts.set_num_threads(1)
    tts = ptts.TTS(str(model), lang='de', rewrites='all', device='cpu', quant='q8', seed=42, voice='default')
    if tts.sample_rate != 24000: raise ValueError('Unerwartete Abtastrate.')
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.speech-build-') as temporary:
        folder = Path(temporary) / 'pack'; folder.mkdir()
        manifest = {'version': PACK_VERSION, 'generator': 'ptts 0.4.0 / gradium/phonon-40m-de Q8', 'clips': {}}
        for key, text in PHRASES.items():
            chunks = []
            with tts.stream(text) as stream:
                for chunk in stream:
                    chunks.append(np.asarray(chunk, dtype=np.float32).reshape(-1).copy())
                    if sum(len(c) for c in chunks) > 24000 * 15:
                        raise ValueError('Ansage länger als 15 Sekunden.')
            pcm = np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
            if not pcm.size or not np.isfinite(pcm).all() or float(np.sqrt(np.mean(pcm ** 2))) < 1e-5:
                raise ValueError('Leere oder ungültige Synthese.')
            path = folder / (key + '.wav')
            with wave.open(str(path), 'wb') as audio:
                audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                audio.writeframes((np.clip(pcm, -1, 1) * 32767).astype('<i2').tobytes())
            manifest['clips'][key] = {'text': text, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'seconds': len(pcm) / 24000}
        (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        load_pack(folder)
        # New destination only; a failed build never replaces an existing pack.
        if output.exists(): raise ValueError('Ziel wurde inzwischen angelegt.')
        folder.rename(output)
    return manifest


def install(source, root):
    """Copy only validated fixed clips into a NEW pack; never mutate preferences."""
    clips = load_pack(source)
    root = Path(root).absolute()
    if not root.is_dir(): raise ValueError('App-Datenordner muss bereits existieren.')
    target = root / 'announcements-pack'
    if target.exists() or target.is_symlink(): raise ValueError('Sprachpaket existiert bereits. Beide Ansagen ausschalten und altes Paket zuerst sichern.')
    with tempfile.TemporaryDirectory(dir=root, prefix='.speech-install-') as temporary:
        folder = Path(temporary) / 'pack'; folder.mkdir(mode=0o700)
        manifest = {'version': PACK_VERSION, 'clips': {}}
        for key, data in clips.items():
            path = folder / (key + '.wav'); path.write_bytes(data); path.chmod(0o600)
            manifest['clips'][key] = {'text': PHRASES[key], 'sha256': hashlib.sha256(data).hexdigest()}
        path = folder / 'manifest.json'; path.write_text(json.dumps(manifest, ensure_ascii=False)); path.chmod(0o600)
        load_pack(folder)
        if target.exists(): raise ValueError('Ziel wurde inzwischen angelegt.')
        folder.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('build'); create.add_argument('--model', required=True); create.add_argument('--output', required=True)
    check = sub.add_parser('check'); check.add_argument('pack')
    copy = sub.add_parser('install'); copy.add_argument('pack'); copy.add_argument('--root', required=True)
    args = parser.parse_args()
    if args.command == 'build': print(json.dumps(build(args.model, args.output), ensure_ascii=False, indent=2))
    elif args.command == 'install':
        print(json.dumps({'installed': str(install(args.pack, args.root)), 'settings_changed': False}))
    else:
        clips = load_pack(args.pack)
        print(json.dumps({'valid': True, 'clips': sorted(clips), 'audio_played': False}))


if __name__ == '__main__': main()
