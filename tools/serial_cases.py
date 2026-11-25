"""Literal serial transition checks; no Python emulation of the circuit."""


def cases():
    result=[]
    def case(name,seed=None,final=None,op=0,byte=0,upper=None,run=1):
        before=dict(pc=256,sp=65534,a=0,ime=0,halted=0,fault=0,ticks=0,tcycles=0,
                    m65281=0,m65282=126,m65295=224,m65535=0,
                    **{'serial-phase':0,'serial-bits':0,'serial-tx':0,'serial-count':0,'serial-length':0,
                       'serial-log0':0,'serial-log15':0,'clocked':0}) | (seed or {})
        after=before|dict(pc=257,ticks=1,tcycles=4,clocked=1)|(final or {})
        item=dict(name=name,initial=before,final=after,opcode=op,byte=byte,run=run)
        if upper is not None:item['upper']=upper
        result.append(item)
    case('idle port')
    for value in (0,126):
        case(f'Mooneye SC unused-bit write {value}',{'a':value},{'pc':258,'tcycles':12},0xE0,2)
    case('SC unused bits read high',{'a':2},{'pc':258,'tcycles':12},0xE0,2)
    case('start internal transfer',{'a':129,'m65281':165}, {'pc':258,'tcycles':12,'m65282':255},0xE0,2)
    case('DMG ignores CGB speed bit',{'a':131},{'pc':258,'tcycles':12,'m65282':255},0xE0,2)
    case('external clock does not advance',{'m65282':254,'m65281':165})
    case('before first edge',{'m65282':255,'m65281':165,'serial-phase':504},{'serial-phase':508})
    # Pan Docs' shift register description: A5 shifted MSB-first, input pulled high.
    for i,(sb,tx,out,shifted) in enumerate([(165,0,75,1),(75,1,151,2),(151,2,47,5),(47,5,95,10),
                                         (95,10,191,20),(191,20,127,41),(127,41,255,82),(255,82,255,165)]):
        final={'serial-phase':0,'serial-bits':(i+1)%8,'m65281':out,'serial-tx':shifted}
        if i==7:final.update(m65282=127,m65295=232,**{'serial-count':1,'serial-length':1,'serial-log0':165})
        case(f'disconnected shift {i+1}',{'m65282':255,'m65281':sb,'serial-tx':tx,'serial-bits':i,'serial-phase':508},final)
    done={'m65282':255,'m65281':255,'serial-phase':508,'serial-bits':7,'serial-tx':82}
    end={'m65282':127,'m65295':232,'serial-phase':0,'serial-bits':0,'serial-tx':165,'serial-count':1,'serial-length':1,'serial-log0':165}
    case('HALT clocks serial completion',done|{'halted':1},end|{'pc':256,'ticks':0,'tcycles':0})
    case('external-only HALT is quiescent',{'halted':1,'m65282':254}, {'pc':256,'ticks':0,'tcycles':0,'clocked':0})
    case('IME-off serial wake',{'halted':1,'m65295':232,'m65535':8},{'halted':0})
    case('count wraps and log evicts oldest',done|{'serial-count':65535,'serial-length':16,'serial-log0':1,'serial-log1':2,'serial-log15':16},
         end|{'serial-count':0,'serial-length':16,'serial-log0':2,'serial-log15':165,'serial-log1':0})
    # Read final clocked values; explicit writes follow completion.
    for name,addr,a in [('read completed SB',1,255),('read completed SC',2,127),('read serial request',15,232)]:
        case(name,done|{'serial-phase':500},end|{'pc':258,'tcycles':12,'a':a},0xF0,addr)
    case('SB write after completing byte',done|{'serial-phase':500,'a':42},end|{'pc':258,'tcycles':12,'m65281':42},0xE0,1)
    case('SC restart at completion preserves the completed byte',done|{'serial-phase':500,'a':129},end|{'pc':258,'tcycles':12,'m65282':255,'serial-tx':0},0xE0,2)
    case('SB write during transfer preserves shifted prefix',{'a':128,'m65281':1,'m65282':255,'serial-phase':500,'serial-bits':3,'serial-tx':5},
         {'pc':258,'tcycles':12,'m65281':128,'serial-phase':0,'serial-bits':4,'serial-tx':10},0xE0,1)
    case('outgoing bit follows modified SB',{'m65281':128,'m65282':255,'serial-phase':508,'serial-bits':4,'serial-tx':10},
         {'m65281':1,'serial-phase':0,'serial-bits':5,'serial-tx':21})
    case('IF write overrides completion request',done|{'serial-phase':500,'a':1},end|{'pc':258,'tcycles':12,'m65295':225},0xE0,15)
    case('SC write aborts before completion',{'m65282':255,'serial-phase':100,'serial-bits':3,'serial-tx':5,'m65281':47},
         {'pc':258,'tcycles':12,'m65282':126,'serial-phase':0,'serial-bits':0,'serial-tx':0},0xE0,2)
    case('SC write restarts active transfer',{'a':129,'m65282':255,'serial-phase':100,'serial-bits':3,'serial-tx':5},
         {'pc':258,'tcycles':12,'serial-phase':0,'serial-bits':0,'serial-tx':0},0xE0,2)
    for name,extra,op,run in [('pause',{},0,0),('fault',{'fault':1},0,1),('trap',{},0xD3,1)]:
        case(f'{name} freezes serial',done|extra,{'pc':256,'ticks':0,'tcycles':0,'clocked':0,'fault':int(name!='pause')},op,run=run)
    case('atomic word writes SB and SC',{'sp':0x8142},{'pc':259,'tcycles':20,'m65281':66,'m65282':255},0x08,1,255)
    case('rejected word leaves serial unchanged',{'sp':0x8142},{'pc':256,'ticks':0,'tcycles':0,'clocked':0,'fault':1},0x08,2,255)
    case('serial completes during other IRQ',done|{'ime':1,'m65535':1,'m65295':225,'serial-phase':492},
         end|{'pc':64,'sp':65532,'ime':0,'ticks':0,'tcycles':20})
    # Timer and serial complete in the same M-cycle; both IF bits survive.
    case('timer and serial requests combine',done|{'timer-reload':1,'m65286':42},end|{'timer-reload':0,'m65285':42,'m65286':42,'m65295':236})
    # Uniform observed keys, including extra IO/slots used by individual cases.
    keys=set().union(*(x['final'] for x in result))
    for item in result:
        for k in keys:
            item['initial'].setdefault(k,0)
            item['final'].setdefault(k,item['initial'][k])
    return result
