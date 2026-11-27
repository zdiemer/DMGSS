#!/usr/bin/env python3
"""Copy pinned Mooneye bank tables verbatim; never derive expected results."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN = '31510e12eea6286d36eea060a6adde755e1067aa'
NAMES = ('rom_512kb', 'rom_1Mb')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mooneye', type=Path, required=True)
    args = parser.parse_args()
    revision = subprocess.check_output(['git', '-C', str(args.mooneye), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != PIN:
        parser.error(f'Mooneye must be checked out at {PIN}')
    output = Path(__file__).resolve().parents[1] / 'tests/vendor/mooneye/mbc1'
    output.mkdir(exist_ok=True)
    manifest = {'commit': PIN, 'files': {}}
    for name in NAMES:
        path = f'emulator-only/mbc1/{name}.s'
        # Read committed bytes even if a local worktree file was modified.
        data = subprocess.check_output(['git', '-C', str(args.mooneye), 'show', f'{PIN}:{path}'])
        (output / f'{name}.s').write_bytes(data)
        manifest['files'][path] = hashlib.sha256(data).hexdigest()
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
