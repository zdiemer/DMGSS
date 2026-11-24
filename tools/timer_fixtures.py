"""Assemble reduced, pinned Mooneye timer bodies; never run their instructions."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NAMES = [f'tim{i:02b}{suffix}' for suffix in ('','_div_trigger') for i in range(4)] + [
    'tima_reload','tima_write_reloading','tma_write_reloading']
IO = {'IE':255,'IF':15,'DIV':4,'TIMA':5,'TMA':6,'TAC':7}
REGS = {'b':0,'c':1,'d':2,'e':3,'h':4,'l':5,'a':7}


def number(value):
    return int(value[1:],16) if value.startswith('$') else int(value[1:],2) if value.startswith('%') else int(value)


def assemble(source):
    body = source.split('\ntest:\n',1)[1].split('  setup_assertions',1)[0]
    code=[]
    for raw in body.splitlines():
        line=re.sub(r'\s+','',raw.split(';',1)[0]).lower()
        if not line: continue
        if line in ('di','xora','nop'):
            code.append({'di':0xF3,'xora':0xAF,'nop':0}[line]);continue
        if line.startswith('nops'):
            code.extend([0]*number(line[4:]));continue
        if match:=re.fullmatch(r'ld([bcdehla]),([bcdehla]|\$[0-9a-f]+|%[01]+|\d+)',line):
            dst,src=match.groups()
            if src in REGS: code.append(0x40+8*REGS[dst]+REGS[src])
            else: code.extend([6+8*REGS[dst],number(src)])
            continue
        if match:=re.fullmatch(r'ldh\(<(ie|if|div|tima|tma|tac)\),a',line):
            code.extend([0xE0,IO[match[1].upper()]]);continue
        if match:=re.fullmatch(r'ldha,\(<(ie|if|div|tima|tma|tac)\)',line):
            code.extend([0xF0,IO[match[1].upper()]]);continue
        raise ValueError(f'Unrecognized pinned instruction: {raw}')
    expected={reg.lower():int(value,16) for reg,value in re.findall(r'assert_([bcdehl]) \$([0-9a-f]+)\b',source,re.I)}
    assert expected
    # Replace the printing/assertion harness with a timer shutdown and HALT.
    # This tail preserves every register used by the upstream assertions.
    return code+[0xAF,0xE0,7,0x76], expected


def cases():
    result=[]
    for name in NAMES:
        code,expected=assemble((ROOT / f'tests/vendor/mooneye/timer/{name}.s').read_text())
        result.append(dict(name=name,rom=code,expect=expected))
    return result
