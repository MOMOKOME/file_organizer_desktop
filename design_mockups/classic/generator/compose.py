import sys,re,pathlib,random
sys.path.insert(0,'.')
from engrave import *
def svg(cls,w,h,parts,vb=None):
    return f'<svg class="bot {cls}" viewBox="{vb or f"0 0 {w} {h}"}" aria-hidden="true">{render(parts)}</svg>'
# sidebar 232x768
sb=[]
sb+=fern(((-46,650),(-4,592),(40,520),(118,446)),rng=random.Random(11))
sb+=coffee_branch(((318,706),(222,640),(150,520),(66,404)),[0.18,0.4,0.62,0.83],[104,98,86,68],wbase=3.6,berries_at=(0.62,),rng=random.Random(4))
SB=svg('bot-sb',232,768,sb)
# header 420x110 ; olive entering from right/top
hd=olive_branch(((560,-46),(430,8),(300,46),(150,76)),[0.2,0.3,0.4,0.5,0.6,0.7,0.79,0.87,0.94],[80,80,76,72,66,60,52,44,36],wbase=2.6,olives=((0.45,8,20,80),(0.66,-4,20,100)),rng=random.Random(8))
HD=svg('bot-hd',420,110,hd)
# card bottom-left fern 240x230
cd=fern(((-30,250),(10,190),(70,120),(170,70)),n=16,Lmax=50,rng=random.Random(21))
CD=svg('bot-card',240,230,cd)
# small olive sprig under the empty icon 170x90
wr=olive_branch(((8,64),(40,92),(120,92),(164,40)),[0.12,0.22,0.32,0.44,0.56,0.68,0.8,0.9],[24,26,26,25,24,22,19,15],wbase=1.4,olives=((0.38,2,8,95),(0.62,-2,8,85)),rng=random.Random(2))
WR=svg('bot-wr',170,96,wr)
f=pathlib.Path(sys.argv[1]); t=f.read_text()
def sub(pat,rep,flags=re.S):
    global t; t,n=re.subn(pat,lambda m:rep,t,count=1,flags=flags); assert n==1,pat
sub(r'\s*<svg class="i leaf3".*?</svg>','')
sub(r'<svg class="i sbvine".*?</svg>',SB)
sub(r'<svg class="i leaf2".*?</svg>',HD)
sub(r'<svg class="i cs1".*?</svg>\s*<svg class="i cs2".*?</svg>',CD)
sub(r'<svg class="i wreath".*?</svg>',WR)
# CSS
for pat in [r'^\.leaf2\{.*\n',r'^\.leaf2 circle\{.*\n',r'^\.leaf3\{.*\n',r'^\.leaf4\{.*\n',r'^\.sbvine\{.*\n',r'^\.sbvine circle\{.*\n',r'^\.cs1\{.*\n',r'^\.cs2\{.*\n',r'^\.wreath\{.*\n']:
    t,n=re.subn(pat,'',t,count=1,flags=re.M); assert n==1,pat
css=""".bot{fill:currentColor;stroke:none;pointer-events:none;position:absolute;overflow:hidden}
.bot-sb{left:0;top:0;width:232px;height:768px;color:#b39566;opacity:.3}
.bot-hd{right:-24px;top:-20px;width:420px;height:110px;color:#7a6440;opacity:.26}
.bot-card{left:0;bottom:0;width:240px;height:230px;color:#7a6440;opacity:.1}
.bot-wr{left:-7px;top:-4px;width:170px;height:96px;color:#8a6a3a;opacity:.55}
"""
t=t.replace('.wr{position:relative;width:156px;height:86px;',css+'.wr{position:relative;width:156px;height:86px;',1)
f.write_text(t); print('ok',len(t))
