"""Original, hand-specified LCD boundary cases; emit inputs, never emulate them.

These are contract tests of the documented fixed-duration model, not an upstream
PPU-suite pass. One full-memory CPU step uses opcodes seeded in executable HRAM.
"""
import json
from pathlib import Path
from cpu import machine
from portable import storage
from rom import ROM


def seed(line=0, dot=0, mode=2, control=0, lyc=255, signal=0, **extra):
    # Establish a coherent initial register image without running any clocks.
    ly = 0 if line == 153 and dot >= 4 else line
    return {'m65344':128, 'm65345':128+control+mode+4*(ly==lyc),
            'm65348':ly,'m65349':lyc,'lcd-line':line,'lcd-dot':dot,
            'lcd-stat':signal, **extra}


def cases():
    result=[]
    def add(name, initial, expect, code=(0,), run=1):
        result.append(dict(name=name,initial={'pc':65408,**initial,
                      **{f'm{65408+i}':byte for i,byte in enumerate(code)}},
                      expect=expect,run=run))
    add('disabled',{}, {'m65344':0,'m65345':132,'m65348':0,'lcd-line':0,'lcd-dot':0,'lcd-stat':0,'m65295':224,'ticks':1})
    add('mode-2-last',seed(dot=72),{'lcd-dot':76,'m65345':130,'m65295':224})
    add('mode-3-start',seed(dot=76),{'lcd-dot':80,'m65345':131,'m65295':224})
    add('mode-3-last',seed(dot=244,mode=3,control=8),{'lcd-dot':248,'m65345':139,'m65295':224})
    add('hblank-edge',seed(dot=248,mode=3,control=8),{'lcd-dot':252,'m65345':136,'lcd-stat':1,'m65295':226})
    add('hblank-held',seed(dot=252,mode=0,control=8,signal=1),{'lcd-dot':256,'lcd-stat':1,'m65295':224})
    add('next-visible-line',seed(dot=452,mode=0,control=32),{'lcd-line':1,'lcd-dot':0,'m65348':1,'m65345':162,'lcd-stat':1,'m65295':226})
    add('mode-0-2-blocking',seed(dot=452,mode=0,control=40,signal=1),{'lcd-line':1,'m65345':170,'lcd-stat':1,'m65295':224})
    add('vblank-edge',seed(line=143,dot=452,mode=0,control=16),{'lcd-line':144,'lcd-dot':0,'m65348':144,'m65345':145,'lcd-stat':1,'m65295':227})
    add('vblank-held',seed(line=144,dot=0,mode=1,control=16,signal=1),{'lcd-dot':4,'m65345':145,'m65295':224})
    add('mode-0-1-blocking',seed(line=143,dot=452,mode=0,control=24,signal=1),{'lcd-line':144,'m65345':153,'lcd-stat':1,'m65295':225})
    add('vblank-next-line',seed(line=144,dot=452,mode=1,control=16,signal=1),{'lcd-line':145,'lcd-dot':0,'m65348':145,'m65345':145,'m65295':224})
    add('lyc-edge',seed(line=1,dot=452,mode=0,control=64,lyc=2),{'m65348':2,'m65345':198,'lcd-stat':1,'m65295':226})
    add('lyc-held',seed(line=2,dot=76,control=64,lyc=2,signal=1),{'m65345':199,'lcd-stat':1,'m65295':224})
    add('lyc-leaves',seed(line=2,dot=452,mode=0,control=64,lyc=2,signal=1),{'m65348':3,'m65345':194,'lcd-stat':0,'m65295':224})
    add('line-153-entry',seed(line=152,dot=452,mode=1,control=64,lyc=153),{'lcd-line':153,'lcd-dot':0,'m65348':153,'m65345':197,'m65295':226})
    add('ly-153-early-zero',seed(line=153,mode=1,control=64,lyc=0),{'lcd-line':153,'lcd-dot':4,'m65348':0,'m65345':197,'lcd-stat':1,'m65295':226})
    add('frame-wrap-blocking',seed(line=153,dot=452,mode=1,control=96,lyc=0,signal=1),{'lcd-line':0,'lcd-dot':0,'m65348':0,'m65345':230,'lcd-stat':1,'m65295':224})
    add('frame-wrap-mode-2',seed(line=153,dot=452,mode=1,control=32),{'lcd-line':0,'lcd-dot':0,'m65348':0,'m65345':162,'m65295':226})
    add('lcd-enable',{'a':129}, {'m65344':129,'m65345':134,'m65348':0,'lcd-line':0,'lcd-dot':0,'m65295':224}, [0xE0,0x40])
    add('lcd-enable-lyc',{'a':128,'m65345':196}, {'m65344':128,'m65345':198,'lcd-stat':1,'m65295':226}, [0xE0,0x40])
    add('lcd-disable',seed(line=145,dot=100,mode=1,control=16,signal=1,a=0),{'m65344':0,'m65345':144,'m65348':0,'lcd-line':0,'lcd-dot':0,'lcd-stat':0,'m65295':224},[0xE0,0x40])
    add('lcdc-on-write-preserves-phase',seed(line=12,dot=100,mode=3,a=255),{'m65344':255,'m65348':12,'lcd-line':12,'lcd-dot':112,'m65345':131},[0xE0,0x40])
    add('ly-write-ignored',seed(line=12,dot=100,mode=3,a=55),{'m65348':12,'lcd-line':12,'lcd-dot':112},[0xE0,0x44])
    add('lyc-write-request',seed(line=12,dot=100,mode=3,control=64,a=12),{'m65349':12,'m65345':199,'lcd-stat':1,'m65295':226},[0xE0,0x45])
    add('lyc-write-clear',seed(line=12,dot=100,mode=3,control=64,lyc=12,signal=1,a=13),{'m65349':13,'m65345':195,'lcd-stat':0,'m65295':224},[0xE0,0x45])
    add('stat-write-mask',seed(dot=100,mode=3,lyc=0,a=255),{'m65345':255,'lcd-stat':1,'m65295':226},[0xE0,0x41])
    add('stat-write-low-bits-read-only',seed(a=7),{'m65345':130,'lcd-stat':0,'m65295':224},[0xE0,0x41])
    add('disabled-lyc-no-interrupt',{'a':64}, {'m65345':196,'lcd-stat':0,'m65295':224},[0xE0,0x41])
    add('read-final-ly',seed(line=143,dot=448,mode=0),{'a':144,'lcd-dot':4,'m65295':225},[0xF0,0x44])
    add('read-final-stat',seed(dot=72),{'a':131,'lcd-dot':84,'m65345':131},[0xF0,0x41])
    add('read-modify-write-stat',seed(dot=100,mode=3,control=8,h=255,l=65),{'m65345':139,'lcd-dot':112,'m65295':224,'ticks':1},[0x34])
    concurrent=seed(line=143,dot=452,mode=0,control=16,**{'timer-reload':1,'m65286':42,'m65281':255,'m65282':255,'serial-phase':508,'serial-bits':7})
    add('all-hardware-requests',concurrent,{'m65295':239,'m65285':42,'m65282':127,'lcd-line':144,'m65345':145})
    add('read-clocked-if',concurrent,{'a':239,'m65295':239},[0xF0,0x0F])
    add('if-write-wins',concurrent|{'a':0},{'m65295':224,'lcd-line':144},[0xE0,0x0F])
    add('read-modify-write-if',seed(line=143,dot=452,mode=0,h=255,l=15),{'m65295':226,'ticks':1},[0x34])
    add('irq-ack-before-new-request',seed(line=143,dot=452,mode=0,ime=1,sp=65534,m65535=1,m65295=225),{'pc':64,'sp':65532,'ticks':0,'tcycles':20,'m65295':225,'lcd-line':144,'lcd-dot':16})
    add('24-cycle-call',seed(dot=72,sp=65534),{'pc':256,'ticks':1,'tcycles':24,'lcd-dot':96,'m65345':131},[0xCD,0,1])
    add('halt-idle',seed(halted=1),{'ticks':0,'tcycles':0,'clocked':1,'lcd-dot':4,'halted':1})
    add('pause-freezes',seed(dot=248,mode=3,control=8),{'lcd-dot':248,'m65345':139,'lcd-stat':0,'m65295':224,'ticks':0},run=0)
    add('fault-freezes',seed(dot=248,mode=3,control=8,fault=1),{'lcd-dot':248,'m65345':139,'m65295':224,'ticks':0,'fault':1})
    add('opcode-trap-freezes',seed(dot=248,mode=3,control=8),{'lcd-dot':248,'m65345':139,'m65295':224,'ticks':0,'fault':1},[0xD3])
    add('word-trap-atomic',seed(dot=248,mode=3,sp=0xFFFF),{'lcd-dot':248,'m65344':128,'m65345':131,'ticks':0,'fault':1},[0x08,0x3F,0xFF])
    add('word-lcdc-stat-write',seed(dot=100,mode=3,sp=0x4080,lyc=0),{'lcd-dot':120,'m65344':128,'m65345':199,'m65295':226},[0x08,0x40,0xFF])
    return result


def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'cases.json').write_text(json.dumps(cases()))
    for decoder in ('math','native'):
        css=machine(ROM([0]),storage,arithmetic=decoder=='math').replace('\n.machine {','\n.pipeline-read {')
        css+='\n.case{--run:0} #power:checked ~ .cases .active{--run:1}\n'
        rows=[]
        for case in cases():
            initial=''.join(f'--next-{key}:{value};' for key,value in case['initial'].items())
            active=' active' if case['run'] else ''
            rows.append(f'<section class="case{active}" style="{initial}"><div class="pipeline-read"><div class="pipeline-execute"><div class="pipeline-read result" id="{case["name"]}"></div></div></div></section>')
        (out/f'{decoder}.css').write_text(css)
        (out/f'{decoder}.html').write_text(f'<!doctype html><meta charset="utf-8"><title>LCD boundary contracts</title><link rel="stylesheet" href="{decoder}.css"><label for="power">Run</label><input id="power" type="checkbox"><div class="cases">'+''.join(rows)+'</div>')
