#!/usr/bin/env python3
"""Generate static HTML/CSS. Never precompute runtime execution."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def storage(states):
    """Two paused animation banks retain values between alternating clock phases."""
    declarations, current, latch, execute = [], [], [], []
    for name, (initial, expression) in states.items():
        declarations.append(f'@property --next-{name} {{ syntax: "<integer>"; inherits: true; initial-value: {initial}; }}')
        current.append(f'--{name}: var(--bank-{name}, {initial}); --next-{name}: {expression};')
        latch.append(f'--bank-{name}: var(--result-{name}, {initial});')
        execute.append(f'--result-{name}: var(--next-{name});')
    return '\n'.join(declarations) + '\n.machine {' + ''.join(current) + '}\n' + \
        '@keyframes latch {0%,100% {' + ''.join(latch) + '}}\n' + \
        '@keyframes execute {0%,100% {' + ''.join(execute) + '}}\n'


def build():
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    for file in (ROOT / 'src').iterdir():
        if file.is_file():
            shutil.copyfile(file, out / file.name)
    (out / 'machine.css').write_text(storage({'ticks': (0, 'calc(var(--ticks) + 1)')}))


if __name__ == '__main__':
    build()
