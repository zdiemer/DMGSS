"""Original full VRAM contracts. Encode fixed inputs; never execute instructions."""
import json
from pathlib import Path
from cpu import machine
from portable import storage
from rom import ROM
from work_memory import pack_initial


def cases():
    result=[]
    def add(name, code, initial, expect, run=1):
        result.append(dict(name=name,initial={'pc':65408,**initial,
            **{f'm{65408+i}':b for i,b in enumerate(code)}},expect=expect,run=run))
    for address in (0x8000,0x800F,0x8010,0x87FF,0x8800,0x8FFF,0x9000,0x97FF,0x9800,0x9BFF,0x9C00,0x9FFF):
        add(f'read-{address:x}',[0xFA,address&255,address>>8],{f'm{address}':165},
            {'a':165,'ticks':1,'fault':0,f'm{address}':165})
    for address in (0x8000,0x80FF,0x8FFF,0x97FF,0x9BFF,0x9FFE):
        add(f'word-{address:x}',[0x08,address&255,address>>8],{'sp':0x1234,f'm{address}':255,f'm{address+1}':255},
            {f'm{address}':52,f'm{address+1}':18,'ticks':1,'fault':0})
    add('cb-high',[0xCB,0x36],{'h':159,'l':255,'m40959':18},{'m40959':33,'f':0,'ticks':1})
    add('read-increment-end',[0x2A],{'h':159,'l':255,'m40959':90},{'a':90,'h':160,'l':0,'fault':0})
    add('stack-last-word',[0xC5],{'sp':0xA000,'b':171,'c':205},{'sp':0x9FFE,'m40958':205,'m40959':171,'fault':0})
    add('pop-cross-page',[0xD1],{'sp':0x8FFF,'m36863':52,'m36864':18},{'sp':0x9001,'d':18,'e':52,'fault':0})
    for address in (0x7FFF,0x9FFF):
        add(f'word-trap-{address:x}',[0x08,address&255,address>>8],{'sp':0x1234,'m32768':90,'m40959':165},
            {'sp':0x1234,'m32768':90,'m40959':165,'pc':65408,'ticks':0,'tcycles':0,'fault':1})
    add('stack-trap',[0xC5],{'sp':0xA001,'m40959':165},{'sp':0xA001,'m40959':165,'ticks':0,'fault':1})
    add('fetch-cross-page',[],{'pc':0x8FFF,'m36863':0x3E,'m36864':42},{'pc':0x9001,'a':42,'ticks':1,'fault':0})
    add('fetch-last-byte',[],{'pc':0x9FFF,'m40959':0x76},{'pc':0xA000,'halted':1,'ticks':1,'fault':0})
    add('fetch-truncated',[],{'pc':0x9FFF,'m40959':0xCB},{'pc':0x9FFF,'ticks':0,'fault':1})
    add('no-echo',[0xEA,0,0xE0],{'a':90,'m32768':165},{'m32768':165,'m49152':90,'fault':0})
    for name,seed,run in [('pause',{},0),('fault',{'fault':1},1)]:
        add(name,[0xEA,0xFF,0x9F],{'a':90,'m40959':165,**seed},{'m40959':165,'ticks':0},run)
    return result


def build(out, build_automatic):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'cases.json').write_text(json.dumps(cases()))
    for decoder in ('math','native'):
        # Full production map, including all 4,096 VRAM words; no accelerator
        # in the math version so Chromium exercises the same fallback as WebKit.
        css=machine(ROM([0]),storage,arithmetic=decoder=='math',accelerated=False).replace('\n.machine {','\n.pipeline-read {')
        css+='\n.case{--run:0} #power:checked ~ .cases .active{--run:1}\n'
        rows=[]
        for case in cases():
            initial=''.join(f'--next-{key}:{value};' for key,value in pack_initial(case['initial']).items())
            active=' active' if case['run'] else ''
            rows.append(f'<section class="case{active}" style="{initial}"><div class="pipeline-read"><div class="pipeline-execute"><div class="pipeline-read result" id="{case["name"]}"></div></div></div></section>')
        (out/f'{decoder}.css').write_text(css)
        (out/f'{decoder}.html').write_text(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{decoder}.css"><label for="power">Run</label><input id="power" type="checkbox"><div class="cases">'+''.join(rows)+'</div>')
    initial={f'm{0x8000+i}':(i*43+(i>>8)*31+7)&255 for i in range(8192)}
    initial.update({'m49152':165,'m57343':90})
    code=[]
    for page in range(32):
        code += [0x31,page+17,page+1,0x08,0x7F,0x80+page]
    code += [0]*64+[0xFA,0x7F,0x80,0x47,0xFA,0x80,0x9F,0x4F,0x76]
    build_automatic(code,out/'all-bytes',initial=initial)
    for seed in (0,0x3412):
        code=[]
        for value in (65535,seed,seed,0xABCD):
            code += [0x31,value&255,value>>8,0x08,0xFE,0x9F]+[0]*126
        code += [0xFA,0xFE,0x9F,0x47,0xFA,0xFF,0x9F,0x76]
        build_automatic(code,out/f'reactivate-{seed}',initial={'m40958':seed&255,'m40959':seed>>8})
