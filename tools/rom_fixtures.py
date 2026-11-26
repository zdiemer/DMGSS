"""Test-only lookup probes. Inputs are fixed before the browser loads."""
from pathlib import Path
from cpu import choose_math, choose_native
from dense_rom import dense_data
from rom import ROM


def build(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    data = dense_data()
    data[:12] = bytes([255,255,0,0,255,0,0,255,254,255,255,254])
    data[0x300:0x400] = bytes([255])*256
    data[0x500:0x600] = bytes(256)
    data[0x700:0x800] = bytes([255])*256
    (out/'data.bin').write_bytes(data)
    addresses = sorted(set(range(256)) | {256*p+i for p in range(128) for i in (0,1,254,255)} | {-1,32768,32769,65408,65535,65536})
    for name, choose in [('math',choose_math),('native',choose_native)]:
        rom=ROM(data,0)
        valid=rom.readable('address',choose,[32768,65535])
        result=rom.lookup('address',choose,{32768:17,65535:203},valid)
        props=''.join(f'@property --{key} {{syntax:"<integer>";inherits:false;initial-value:0;}}' for key in ['address','result',*rom.lookup_expr])
        css=props+'.case{'+''.join(f'--{key}:{value};' for key,value in rom.lookup_expr.items())+f'--result:{result};}}'
        (out/f'{name}.css').write_text(css)
        cases=''.join(f'<div class="case" data-address="{address}" style="--address:{address}"></div>' for address in addresses)
        (out/f'{name}.html').write_text(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{name}.css"><title>ROM lookup probes</title>{cases}')
