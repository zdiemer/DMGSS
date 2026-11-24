"""Original single-step timer regressions; literal expectations, no simulation."""


def cases():
    result=[]
    def case(name,initial=None,final=None,opcode=0,byte=0,upper=None,run=1):
        before=dict(pc=256,sp=0xC020,a=0,f=0,h=0,l=0,ime=0,ticks=0,tcycles=0,halted=0,fault=0,
                    m65284=0,m65285=0,m65286=0,m65287=248,m65295=224,m65535=0,
                    **{'div-low':0,'timer-reload':0,'clocked':0}) | (initial or {})
        after=before | dict(pc=257,ticks=1,tcycles=4,clocked=1,**{'div-low':4}) | (final or {})
        item=dict(name=name,opcode=opcode,byte=byte,initial=before,final=after,run=run)
        if upper is not None:item['upper']=upper
        result.append(item)
    case('DIV carries',{'div-low':252},{'m65284':1,'div-low':0})
    case('DIV wraps',{'m65284':255,'div-low':252},{'m65284':0,'div-low':0})
    case('disabled TIMA',{'div-low':12,'m65285':255},{'div-low':16})
    for select,high,low,out_high,out_low in [(0,3,252,4,0),(1,0,12,0,16),(2,0,60,0,64),(3,0,252,1,0)]:
        case(f'frequency {select}',{'m65284':high,'div-low':low,'m65285':7,'m65287':252+select},
             {'m65284':out_high,'div-low':out_low,'m65285':8})
    case('before edge',{'div-low':8,'m65285':7,'m65287':253},{'div-low':12})
    case('overflow delay',{'div-low':12,'m65285':255,'m65286':42,'m65287':253},
         {'div-low':16,'m65285':0,'timer-reload':1})
    for tac in (248,253):
        case(f'reload even with TAC {tac}',{'div-low':16,'timer-reload':1,'m65286':42,'m65287':tac,'m65295':225},
             {'div-low':20,'timer-reload':0,'m65285':42,'m65295':229})
    case('read zero during overflow',{'div-low':4,'m65285':255,'m65286':42,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':16,'m65285':0,'timer-reload':1},0xF0,5)
    case('read reload on final M-cycle',{'div-low':8,'m65285':255,'m65286':42,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':20,'m65285':42,'a':42,'m65295':228},0xF0,5)
    case('DIV write falling edge',{'a':99,'m65285':10,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':0,'m65285':11},0xE0,4)
    case('DIV write after natural edge',{'a':99,'div-low':4,'m65285':10,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':0,'m65285':11},0xE0,4)
    case('disable high timer input',{'m65285':10,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':12,'m65285':11,'m65287':248},0xE0,7)
    case('enable high input has no falling edge',{'a':5,'m65285':10},
         {'pc':258,'tcycles':12,'div-low':12,'m65287':253},0xE0,7)
    case('change high input to low',{'a':5,'m65284':1,'div-low':244,'m65285':10,'m65287':252},
         {'pc':258,'tcycles':12,'m65284':2,'div-low':0,'m65285':11,'m65287':253},0xE0,7)
    case('TIMA write cancels pending reload',{'a':77,'div-low':4,'m65285':255,'m65286':42,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':16,'m65285':77},0xE0,5)
    case('TIMA write ignored during reload',{'a':77,'div-low':8,'m65285':255,'m65286':42,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':20,'m65285':42,'m65295':228},0xE0,5)
    case('TMA write feeds same-cycle reload',{'a':77,'div-low':8,'m65285':255,'m65286':42,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':20,'m65285':77,'m65286':77,'m65295':228},0xE0,6)
    case('TMA write before reload',{'a':77,'div-low':4,'m65285':255,'m65286':42,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':16,'m65285':0,'m65286':77,'timer-reload':1},0xE0,6)
    case('word transfer into timer registers',{'sp':0x052A},
         {'pc':259,'tcycles':20,'div-low':20,'m65286':42,'m65287':253},0x08,6,255)
    case('word transfer validates both lanes',{'m65284':7,'div-low':12},
         {'pc':256,'ticks':0,'tcycles':0,'clocked':0,'div-low':12,'fault':1},0x08,3,255)
    case('timer requests during another interrupt entry',{'sp':65534,'ime':1,'m65535':1,'m65295':225,'m65285':255,'m65286':42,'m65287':253},
         {'pc':64,'sp':65532,'ime':0,'ticks':0,'tcycles':20,'div-low':20,'m65285':42,'m65295':228})
    case('idle overflow preserves CPU',{'halted':1,'div-low':12,'m65285':255,'m65286':42,'m65287':253},
         {'pc':256,'ticks':0,'tcycles':0,'div-low':16,'m65285':0,'timer-reload':1})
    case('idle reload raises IF',{'halted':1,'div-low':16,'timer-reload':1,'m65286':42,'m65287':253,'m65535':4},
         {'pc':256,'ticks':0,'tcycles':0,'div-low':20,'timer-reload':0,'m65285':42,'m65295':228})
    case('timer wakes HALT with IME off',{'halted':1,'div-low':20,'m65285':42,'m65287':253,'m65535':4,'m65295':228},
         {'halted':0,'div-low':24})
    for name,seed,opcode,run in [('fault freezes timer',{'fault':1},0,1),
                                 ('trap freezes timer',{},0xD3,1),('pause freezes timer',{},0,0)]:
        case(name,{'div-low':12,'m65285':255,'m65287':253}|seed,
             {'pc':256,'ticks':0,'tcycles':0,'div-low':12,'clocked':0,'fault':int(name!='pause freezes timer')},opcode,run=run)
    case('HALT with no event source is quiescent',{'halted':1,'div-low':12},
         {'pc':256,'ticks':0,'tcycles':0,'div-low':12,'clocked':0})
    case('TAC masks unused bits',{'a':255},{'pc':258,'tcycles':12,'div-low':12,'m65287':255},0xE0,7)
    case('BIT reads timer at last M-cycle',{'h':255,'l':5,'div-low':4,'m65285':255,'m65286':42,'m65287':253},
         {'pc':258,'tcycles':12,'div-low':16,'m65285':0,'timer-reload':1,'f':160},0xCB,0x46)
    case('CB modifies clocked TIMA value',{'h':255,'l':5,'m65285':128,'m65287':253},
         {'pc':258,'tcycles':16,'div-low':16,'m65285':3,'f':16},0xCB,0x06)
    return result
