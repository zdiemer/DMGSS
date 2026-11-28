"""Original BGP contracts and exhaustive renderer inputs, never ROM execution."""
import json
from pathlib import Path
from cpu import machine, tile_css
from portable import storage
from rom import ROM


def cases():
    result = []
    def add(name, code, initial, expect, run=1):
        result.append(dict(name=name, initial={'pc':65408, **initial,
                      **{f'm{65408+i}':b for i,b in enumerate(code)}}, expect=expect, run=run))
    add('reset-read', [0xF0,0x47], {}, {'a':0,'m65351':0,'ticks':1,'fault':0})
    add('ldh-read', [0xF0,0x47], {'m65351':228}, {'a':228,'m65351':228,'tcycles':12})
    add('ldh-write', [0xE0,0x47], {'a':27,'m65351':228}, {'m65351':27,'ticks':1})
    add('c-read', [0xF2], {'c':71,'m65351':255}, {'a':255,'m65351':255})
    add('c-write', [0xE2], {'c':71,'a':85}, {'m65351':85})
    add('absolute-write', [0xEA,0x47,0xFF], {'a':170}, {'m65351':170,'tcycles':16})
    add('inc-wrap', [0x34], {'h':255,'l':71,'m65351':255}, {'m65351':0,'f':160})
    add('dec-wrap', [0x35], {'h':255,'l':71}, {'m65351':255,'f':96})
    add('swap', [0xCB,0x36], {'h':255,'l':71,'m65351':27}, {'m65351':177,'f':0})
    add('bit-read-only', [0xCB,0x46], {'h':255,'l':71,'m65351':170}, {'m65351':170,'f':160})
    add('set', [0xCB,0xC6], {'h':255,'l':71,'m65351':170}, {'m65351':171})
    add('res', [0xCB,0xBE], {'h':255,'l':71,'m65351':255}, {'m65351':127})
    add('post-increment', [0x2A], {'h':255,'l':71,'m65351':90}, {'a':90,'h':255,'l':72})
    for address in (0xFF46,0xFF47):
        add(f'word-trap-{address:04x}', [0x08,address&255,255], {'sp':0x1234,'m65351':228},
            {'m65351':228,'sp':0x1234,'ticks':0,'tcycles':0,'fault':1})
    add('paused-write', [0xE0,0x47], {'a':27,'m65351':228}, {'m65351':228,'ticks':0}, run=0)
    add('faulted-write', [0xE0,0x47], {'a':27,'m65351':228,'fault':1}, {'m65351':228,'ticks':0})
    add('fetch-register', [], {'pc':0xFF47}, {'pc':0xFF48,'ticks':1,'fault':0})
    add('truncated-fetch', [], {'pc':0xFF47,'m65351':0xCB}, {'pc':0xFF47,'m65351':0xCB,'ticks':0,'fault':1})
    return result


def build(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    (out/'cases.json').write_text(json.dumps(cases()))
    for decoder in ('math','native'):
        css = machine(ROM([0]),storage,arithmetic=decoder=='math').replace('\n.machine {','\n.pipeline-read {')
        css += '\n.case{--run:0} #power:checked ~ .cases .active{--run:1}\n'
        rows=[]
        for case in cases():
            initial=''.join(f'--next-{k}:{v};' for k,v in case['initial'].items())
            active=' active' if case['run'] else ''
            rows.append(f'<section class="case{active}" style="{initial}"><div class="pipeline-read"><div class="pipeline-execute"><div class="pipeline-read result" id="{case["name"]}"></div></div></div></section>')
        (out/f'{decoder}.css').write_text(css)
        (out/f'{decoder}.html').write_text(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{decoder}.css"><label for="power">Run</label><input id="power" type="checkbox"><div class="cases">'+''.join(rows)+'</div>')
        # Four fixed bitplane IDs, every possible BGP byte. Expected shades
        # live in the test, derived from the documented two-bit field layout.
        rows = [f'<div class="tile-grid" data-palette="{value}" style="--m65351:{value}">'+
                ''.join(f'<i class="pixel-{i}"></i>' for i in range(4))+'</div>' for value in range(256)]
        css = tile_css(arithmetic=decoder=='math') + '\n.tile-grid{--m32768:80;--m32769:48;display:flex}.tile-grid i{display:block;width:4px;height:4px}'
        (out/f'colors-{decoder}.html').write_text('<!doctype html><meta charset="utf-8"><style>'+css+'</style>'+''.join(rows))
