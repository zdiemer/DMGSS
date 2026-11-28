#!/usr/bin/env python3
"""Convert a ROM to one script-free HTML document; never emulate its program."""
import argparse
import base64
import hashlib
import html
from pathlib import Path
import re
import tempfile

from rom import ROM
from build import build, build_automatic, build_checkpoint

MAX_ROM = 131072
MAX_RAW = 4096
MODES = {'portable': 'Compatible · 128 instructions', 'automatic': 'Automatic continuation',
         'checkpoint': 'Manual checkpoints', 'streaming': 'Streaming · one instruction per commit'}
CAVEAT = ('Conversion uses Python outside the browser. The generated page executes CPU and memory '
          'transitions in HTML/CSS only: no JavaScript, WebAssembly, server emulation or precomputed trace.')
LIMITS = ('Experimental CPU and peripheral timing: 243 unprefixed and 256 CB-prefixed instructions, 8 KiB RAM C000–DFFF (C000–DDFF mirrored at E000–FDFF), HRAM FF80–FFFE and 8 KiB VRAM 8000–9FFF (one tile is displayed). '
          'Instruction durations, software interrupts and DIV/TIMA/TMA/TAC timer interrupts and disconnected SB/SC serial transfers are supported; LCDC/STAT/LY/LYC, VBlank and STAT interrupts use fixed-duration scanlines. BGP (FF47) stores the four background shade mappings; the tile viewer applies them in CSS. No boot ROM, pixel renderer, cable peer, audio or joypad. ROM-only MBC1 banking supports 32, 64 and 128 KiB; larger cartridges and cartridge RAM are unsupported. Bus timing and serial clock phase are approximate. A serial byte needs multiple batches; the monitor keeps the last 16 completed bytes. '
          'PC starts at 0100; other CPU registers, including SP, start at zero. IF reads E0, SC reads 7E, TAC reads F8 and STAT reads 84 initially; LCDC is off and BGP starts at zero. '
          'Unsupported instructions and unmapped accesses trap. Import does not imply game compatibility.')


class ConversionError(ValueError):
    pass


def load_rom(data, format):
    if format == 'raw':
        if not 1 <= len(data) <= MAX_RAW:
            raise ConversionError('Raw programs must contain 1–4096 bytes, loaded at address 0100.')
        rom = ROM(data, 0x100)
    elif format == 'gb':
        if len(data) not in (32768, 65536, MAX_ROM):
            raise ConversionError('Game Boy images must be exactly 32, 64 or 128 KiB.')
        if data[0x147] not in (0, 1) or data[0x149] != 0:
            raise ConversionError('Only ROM ONLY (type 00) or MBC1 without RAM (type 01, RAM size 00) are supported.')
        if data[0x148] not in (0, 1, 2) or len(data) != 32768 << data[0x148]:
            raise ConversionError('ROM length must match header size 00, 01 or 02 (32, 64 or 128 KiB).')
        if data[0x147] == 0 and data[0x148] != 0:
            raise ConversionError('ROM ONLY cartridges must be 32 KiB; larger images require MBC1.')
        if data[0x143] & 0xC0 == 0xC0:
            raise ConversionError('Game Boy Color-only cartridges are not supported.')
        rom = ROM(data, 0, mbc1=data[0x147] == 1)
    else:
        raise ConversionError('Choose Game Boy ROM or raw test program.')
    return rom


def display_name(name):
    name = str(name).replace('\\', '/').rsplit('/', 1)[-1]
    return ''.join(c for c in name if c.isprintable())[:80] or 'Imported cartridge'


def convert(data, name='Imported cartridge', format='gb', mode='portable', online=False):
    if mode not in MODES:
        raise ConversionError('Choose a supported execution mode.')
    rom = load_rom(data, format)
    if mode == 'streaming' and rom.paged:
        raise ConversionError('Dense ROMs require Compatible, Automatic or Manual checkpoints. Streaming supports only sparse ROMs (at most 1024 bytes differing from the most common byte).')
    name = display_name(name)
    # Existing builders write generated assets only in this disposable directory.
    # In the service /tmp is tmpfs. Neither input filenames nor ROM instructions
    # ever become filesystem paths or code executed by the converter.
    with tempfile.TemporaryDirectory(prefix='dmgss-convert-') as folder:
        out = Path(folder) / 'page'
        if mode == 'automatic':
            build_automatic(rom, out, cartridge='imported')
        elif mode == 'checkpoint':
            build_checkpoint(rom, out, cartridge='imported')
        else:
            build(rom, out, bounded=mode == 'portable')
        document = (out / 'index.html').read_text()
        document = re.sub(r'<link rel="stylesheet" href="([\w.-]+)">',
                          lambda m: '<style>' + (out / m[1]).read_text() + '</style>', document)
    safe_name = html.escape(name)
    document = document.replace('DMGSS · Dot Matrix Styles', f'{safe_name} · DMGSS')
    document = document.replace('SYSTEM DIAGNOSTIC', 'IMPORTED CARTRIDGE')
    document = document.replace('Old hardware.<br> New rules.', 'Your ROM.<br> CSS runtime.')
    document = re.sub(r'<nav class="cartridges".*?</nav>', '<nav class="cartridges imported-name" aria-label="Cartridge">' + safe_name + '</nav>', document)
    document = re.sub(r'<p class="(?:mode-switch|automatic-link|checkpoint-link)">.*?</p>', '', document)
    document = re.sub(r'<aside id="about">.*?</aside>', lambda _: (
        '<aside id="about"><h2>Converted cartridge</h2>'
        f'<p class="conversion-caveat">{CAVEAT}</p><p>{LIMITS}</p>'
        f'<p><strong>{safe_name}</strong><br>{len(data):,} bytes · {html.escape(MODES[mode])}</p>'
        f'<details><summary>ROM fingerprint</summary><code>{hashlib.sha256(data).hexdigest()}</code></details>'
        + ('<p>Reset converts the embedded bytes again on the server. Run and Pause make no server requests. '
           'Use Download HTML in the loader for an offline copy.</p><p><a href="/convert/">Load another ROM</a></p>' if online else
           '<p>This file includes its ROM and styles. Keep it together as one HTML file; no server is needed. Reset reloads this file.</p>')
        + '</aside>'), document, flags=re.S)
    # A user's program writing A5 is not our diagnostic's success signal.
    document = document.replace('<span class="passed">TEST PASSED</span>', '')
    document = document.replace('</head>', '<style>.halt-message .stopped{display:inline-block!important}'
        '.imported-name{display:block;overflow-wrap:anywhere;min-height:30px}'
        'code{overflow-wrap:anywhere;font-size:11px}.conversion-caveat{border-left:2px solid #b1c37e;padding-left:12px}'
        '.import-reset{display:contents}.import-reset button{border:0;background:transparent;cursor:pointer;color:inherit;font:inherit}'
        '</style></head>')
    # Self-contained fallback instructions must not silently switch to built-in ROMs.
    document = re.sub(r'<a class="portable-link" href="[^"]+">.*?</a>', '<span>Convert this ROM in Compatible mode.</span>', document)
    document = document.replace('<a href="/checkpoint/">manual checkpoints</a>', 'manual checkpoints')
    document = document.replace('<a href="/portable/">compatible mode</a>', 'compatible mode')
    document = document.replace('<a href="/portable/">Try compatible mode</a>', 'Convert in Compatible mode')
    document = document.replace('<a href="/portable/">Compatible mode</a>', 'Compatible mode')
    document = document.replace('href="./"', 'href=""')
    document = document.replace('<a class="wordmark" href="">', '<a class="wordmark" href="#about">')
    if online:
        fields = {'payload': base64.urlsafe_b64encode(data).decode(), 'name': name, 'format': format, 'mode': mode, 'delivery': 'open'}
        inputs = ''.join(f'<input type="hidden" name="{k}" value="{html.escape(v, quote=True)}">' for k, v in fields.items())
        document = document.replace('<a class="reset" href="">RESET</a>',
            '<form class="import-reset" method="post" action="/convert/">' + inputs + '<button class="reset" type="submit">RESET</button></form>')
        document = document.replace("form-action 'none'", "form-action 'self'")
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('-o', '--output', type=Path, required=True, help='New HTML file (existing files are never overwritten)')
    parser.add_argument('--format', choices=['gb', 'raw'], default='gb')
    parser.add_argument('--mode', choices=MODES, default='portable')
    args = parser.parse_args()
    try:
        if not args.rom.is_file():
            raise ConversionError('Input must be a regular ROM file.')
        with args.rom.open('rb') as source:
            data = source.read(MAX_ROM + 1)
        document = convert(data, args.rom.name, args.format, args.mode)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(document)
    except (OSError, ConversionError) as error:
        parser.exit(2, f'Conversion failed: {error}\n')
    print(f'Created {args.output}. {CAVEAT}')


if __name__ == '__main__':
    main()
