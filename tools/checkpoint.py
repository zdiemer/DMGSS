"""Reusable native HTML bit banks for explicitly user-clocked CSS checkpoints."""
from work_memory import pack_initial
from cpu import machine, tile_css, choose_math
from portable import storage as pipeline_storage

WIDTHS = {'lcd-dot': 9, 'lcd-stat': 1, 'pc': 16, 'sp': 16, 'halted': 1, 'fault': 1, 'ticks': 16, 'tcycles': 16, 'ime': 1, 'ime-delay': 1, 'halt-bug': 1, 'timer-reload': 1, 'clocked': 1, 'serial-phase': 9, 'serial-bits': 3, 'serial-count': 16, 'serial-length': 5}


def counter_rom():
    # Four instructions per lap: RAM[C000]++ with 8-bit wrap, then branch back.
    return [0xFA, 0x00, 0xC0, 0x3C, 0xEA, 0x00, 0xC0, 0x18, 0xF7]


def width(name):
    if name == 'mbc-bank': return 5
    return 16 if name.startswith(('wram','vram')) else WIDTHS.get(name,8)


def generate(rom, initial=None):
    """Native bit storage, grouped readers and a bounded next-bit selector."""
    initial = pack_initial(initial)
    states = {}
    def storage(definitions):
        definitions = {name:(initial.get(name,value),expression) for name,(value,expression) in definitions.items()}
        states.update(definitions)
        return pipeline_storage(definitions, initialize=False)
    css = machine(rom,storage,arithmetic=True).replace('\n.machine {','\n.pipeline-read {')
    rules = [css,tile_css(arithmetic=True)]
    names = list(states)
    positions = {name:i for i,name in enumerate(names)}
    groups = [names[i:i+64] for i in range(0,len(names),64)]
    bits = [(name,bit,(states[name][0] >> bit)&1) for name in states for bit in range(width(name))]
    count = len(bits)
    base, offset = {},0
    for name in names:
        base[name]=offset;offset+=width(name)
    rules.append('@property --bank-phase {syntax:"<integer>";inherits:false;initial-value:0;}')
    for name in ('copy-index','copy-group','copy-slot','copy-remaining'):
        rules.append(f'@property --{name} {{syntax:"<integer>";inherits:true;initial-value:0;}}')
    rules.append('.clock {container-name:checkpoint-bank}')
    rules.append('#commit:checked ~ .clock,#commit:checked ~ .clock .checkpoint-select {--bank-phase:1} .checkpoint-reader,.checkpoint-seed {display:contents} .copy-page {display:none}')
    # Unregistered raw bits are reset locally. Only active-bank bits affect
    # source readers; inactive-bank bits update the UI without touching CPU state.
    rules.append('.checkpoint-reader {' + ''.join(f'--bit-{i}:0;' for i in range(1024)) + '}')
    rules.append('.checkpoint-diff-execute {' + ''.join(f'--diff-bit-{i}:0;' for i in range(4096)) + '}')
    rules.append('.checkpoint-bit {display:none} .checkpoint-bit:target {display:block}')
    for i in range(64):
        rules.append(f'@property --source-local-{i} {{syntax:"<integer>";inherits:false;initial-value:0;}}')
    opening=[]
    # Keep a unique reader class per group: a shared class makes every reader
    # match the entire bit-rule table before rejecting unrelated siblings.
    read_rules, diff_rules = {0:[],1:[]}, {0:[],1:[]}
    inactive={}
    for g,group in enumerate(groups):
        bindings=[]
        bank_words=[{},{}]
        for bank in range(2):
            local=0
            for name in group:
                terms=[]
                diff_terms=[]
                for bit in range(width(name)):
                    i=base[name]+bit;ident=f'c{bank}-{i}'
                    checked=' checked' if bits[i][2] else ''
                    opening.append(f'<input class="sr-only checkpoint-bit" type=checkbox id={ident} tabindex=-1 autocomplete=off{checked}>')
                    read_rules[bank].append(f'#{ident}:checked ~ .checkpoint-reader-{g} {{--bit-{local}:1}}')
                    diff_group=positions[name]//256
                    diff_local=i-base[names[diff_group*256]]
                    diff_rules[1-bank].append(f'#{ident}:checked ~ .checkpoint-reader-{g} .checkpoint-diff-execute-{diff_group} {{--diff-bit-{diff_local}:1}}')
                    diff_terms.append(f'var(--diff-bit-{diff_local}) * {1<<bit}')
                    terms.append(f'var(--bit-{local}) * {1<<bit}');local+=1
                bank_words[bank][name]='('+' + '.join(terms)+')'
                inactive[name]='('+' + '.join(diff_terms)+')'
        opening.append(f'<div class="checkpoint-reader checkpoint-reader-{g}">')
        for i,name in enumerate(group):
            a,b=bank_words[0][name],bank_words[1][name]
            bindings.append(f'--source-local-{i}:calc({a});--next-{name}:var(--source-local-{i});')
        rules.append(f'.checkpoint-reader-{g} {{'+''.join(bindings)+'}')
    opening.append('<div class="checkpoint-seed">')
    # Readers seed next-state fields directly. A second inherited source alias
    # for every word needlessly survives through the whole pipeline and UI.
    # Fold the UI comparison in small stages. Reuse local helper names rather
    # than registering a distinct global property for every RAM bit or word.
    diff_groups = [names[i:i+256] for i in range(0,len(names),256)]
    for i in range(256):
        for prefix in ('diff-target','diff-mask'):
            rules.append(f'@property --{prefix}-{i} {{syntax:"<integer>";inherits:false;initial-value:0;}}')
    for name in ('diff-first','diff-selected'):
        rules.append(f'@property --{name} {{syntax:"<integer>";inherits:false;initial-value:0;}}')
    for name,value in [('diff-count',0),('diff-base',count),('diff-bits',0)]:
        for phase in ('old','next'):
            rules.append(f'@property --{name}-{phase} {{syntax:"<integer>";inherits:true;initial-value:{value};}}')
    rules.append('.checkpoint-values {--diff-count-next:0;--diff-base-next:'+str(count)+';--diff-bits-next:0;} .checkpoint-diff-read {--diff-count-old:var(--diff-count-next);--diff-base-old:var(--diff-base-next);--diff-bits-old:var(--diff-bits-next);}')
    diff_open=[]
    for g,group in enumerate(diff_groups):
        diff_open.append(f'<div class="checkpoint-diff-read"><div class="checkpoint-diff-execute checkpoint-diff-execute-{g}">')
        bindings=[]
        for i,name in enumerate(group):
            bindings.append(f'--diff-target-{i}:calc({inactive[name]});')
            terms=[f'abs(mod(round(down,var(--{name}) / {1<<bit}),2) - mod(round(down,var(--diff-target-{i}) / {1<<bit}),2)) * {1<<bit}' for bit in range(width(name))]
            bindings.append(f'--diff-mask-{i}:calc('+' + '.join(terms)+');')
        terms=[f'mod(round(down,var(--diff-mask-{i}) / {1<<bit}),2)' for i,name in enumerate(group) for bit in range(width(name))]
        bindings.append('--diff-count-next:calc(var(--diff-count-old) + '+' + '.join(terms)+');')
        terms=[f'{base[name]} + (1 - min(1,var(--diff-mask-{i}))) * {count}' for i,name in enumerate(group)]
        bindings.append('--diff-first:min('+','.join(terms)+f',{count});')
        bindings.append('--diff-selected:'+choose_math('diff-first',{base[name]:f'var(--diff-mask-{i})' for i,name in enumerate(group)},0)+';')
        bindings.append('--diff-base-next:min(var(--diff-base-old),var(--diff-first));--diff-bits-next:calc(var(--diff-bits-old) + (1 - min(1,var(--diff-bits-old))) * var(--diff-selected));')
        rules.append(f'.checkpoint-diff-execute-{g} {{'+''.join(bindings)+'}')
    # Query a stable parent outside the hidden controls. Accessibility reads
    # can make Chromium cache queries against a display:none unnamed ancestor.
    rules.append('.checkpoint-select {container-name:checkpoint-copy;--copy-remaining:var(--diff-count-next);--copy-index:min('+str(count)+',var(--diff-base-next) + min('+','.join(f'{bit} + (1 - mod(round(down,var(--diff-bits-next) / {1<<bit}),2)) * 16' for bit in range(16))+'));--copy-group:calc(round(down,var(--copy-index) / 32));--copy-slot:mod(var(--copy-index),32);}')
    def control(ident,classes):
        return f'<div class="copy-control {classes}"><label for={ident}>SAVE NEXT BIT</label><a href=#{ident}>Keyboard: focus, then Space</a></div>'
    controls=[]
    for start in range(0,count,32):
        group=start//32
        controls.append(f'<div class="copy-page copy-page-{group}">')
        for i in range(start,min(start+32,count)):
            for bank in range(2):
                ident=f'c{bank}-{i}'
                controls.append(f'<label class="copy-control bank{bank} copy-{i} slot-{i%32}" for={ident}>SAVE NEXT BIT<a href=#{ident}>Keyboard: focus, then Space</a></label>')
        controls.append('</div>')
        rules.append(f'@container checkpoint-copy style(--copy-group:calc({group})) {{.copy-page-{group}{{display:block}}}}')
    for bit in range(32):rules.append(f'@container checkpoint-copy style(--copy-slot:calc({bit})) {{.copy-control.slot-{bit}{{display:block}}}}')
    rules.append('@container checkpoint-copy style(--copy-remaining:0) {.checkpoint-controls .commit-control {display:block}.save-hint {display:none}} .checkpoint-memory::after {counter-reset:value var(--m49152);content:counter(value);}')
    controls.append('<div class="copy-control commit-control"><label for=commit>RUN NEXT 128</label><a href=#commit>Keyboard: focus, then Space</a></div>')
    html='<div class="checkpoint-values">'+''.join(diff_open)+'<div class="checkpoint-select"><div class="checkpoint-controls">'+''.join(controls)
    html+='<p class="save-hint"><span class="copy-remaining"></span> changed bits to save.<br>Tap once per bit, then run the next batch.</p></div></div>'+('</div></div>'*len(diff_groups))+'</div>'
    css='\n'.join(rules).replace('calc(var(--ticks) + 1)',f'calc(mod(var(--ticks) + 1,{1<<WIDTHS["ticks"]}))')
    commit='<input class="sr-only checkpoint-bit" type=checkbox id=commit tabindex=-1 autocomplete=off aria-label="Run next 128 instructions">'
    return css,commit,''.join(opening),html,len(groups)+1,read_rules,diff_rules
