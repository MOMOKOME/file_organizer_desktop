"""Engraving-style botanical generator: all marks are filled tapered shapes (variable line weight)."""
import math, random

def F(v): return f'{v:.1f}'

# ---------- geometry ----------
def bez(p,t):
    (x0,y0),(x1,y1),(x2,y2),(x3,y3)=p; u=1-t
    return (u**3*x0+3*u*u*t*x1+3*u*t*t*x2+t**3*x3, u**3*y0+3*u*u*t*y1+3*u*t*t*y2+t**3*y3)
def bezd(p,t):
    (x0,y0),(x1,y1),(x2,y2),(x3,y3)=p; u=1-t
    return (3*u*u*(x1-x0)+6*u*t*(x2-x1)+3*t*t*(x3-x2), 3*u*u*(y1-y0)+6*u*t*(y2-y1)+3*t*t*(y3-y2))
def ang(p,t):
    dx,dy=bezd(p,t); return math.degrees(math.atan2(dy,dx))

def band(pts, widths):
    """Filled polygon around polyline with per-point width."""
    n=len(pts); L=[];Rr=[]
    for i,(x,y) in enumerate(pts):
        a=pts[max(i-1,0)]; b=pts[min(i+1,n-1)]
        dx,dy=b[0]-a[0],b[1]-a[1]; d=math.hypot(dx,dy) or 1
        nx,ny=-dy/d,dx/d; w=widths[i]/2
        L.append((x+nx*w,y+ny*w)); Rr.append((x-nx*w,y-ny*w))
    poly=L+Rr[::-1]
    return 'M'+'L'.join(F(x)+' '+F(y) for x,y in poly)+'Z'

def curve_band(p, w0, w1, n=24, prof=None):
    pts=[bez(p,i/n) for i in range(n+1)]
    ws=[(prof(i/n) if prof else w0+(w1-w0)*i/n) for i in range(n+1)]
    return band(pts,ws)

def xf(pts, tx, ty, a, sx=1, sy=1):
    c,s=math.cos(math.radians(a)),math.sin(math.radians(a))
    return [(tx+(x*sx)*c-(y*sy)*s, ty+(x*sx)*s+(y*sy)*c) for x,y in pts]

# ---------- leaf ----------
def leaf(tx,ty,a,L,kind='coffee',flip=1,bend=0.06,veins=None,hatch=True,rng=None,turn=1.0):
    rng=rng or random.Random(1)
    if kind=='coffee':
        W=0.22*L*turn; nv=veins or 9
        def hw(s):
            if s<=0 or s>=1: return 0
            v=W*math.sin(math.pi*min(s,1)**0.85)**0.75
            if s>0.82: v*=((1-s)/0.18)**0.7
            return v*(1+0.035*math.sin(16*math.pi*s))
    elif kind=='olive':
        W=0.12*L*turn; nv=veins or 5
        def hw(s):
            if s<=0 or s>=1: return 0
            return W*math.sin(math.pi*s)**0.9*(1-0.25*s)
    else: # pinna
        W=0.24*L*turn; nv=veins or 0
        def hw(s):
            if s<=0 or s>=1: return 0
            return W*math.sin(math.pi*s**0.9)**0.8
    def mid(s): return bend*L*s*(1-s)*4*0.25
    N=26
    ss=[i/N for i in range(N+1)]
    up=[(s*L, mid(s)-hw(s)) for s in ss]
    lo=[(s*L, mid(s)+hw(s)) for s in ss]
    out=[]
    T=lambda pts: xf(pts,tx,ty,a,1,flip)
    lw=max(0.5,L/62)
    out.append(band(T(up),[lw*(0.55+0.45*math.sin(math.pi*s)) for s in ss]))
    out.append(band(T(lo),[lw*(0.9+1.3*math.sin(math.pi*s)) for s in ss]))
    # midrib incl. petiole
    ms=[-0.07+i*(1.0)/N for i in range(N+1)]
    mp=[(s*L, mid(max(s,0))) for s in ms]
    out.append(band(T(mp),[lw*(2.0-1.7*max(s,0)) for s in ms]))
    # veins
    for k in range(nv):
        s0=0.1+(k+0.5)*0.78/nv; s1=min(0.97,s0+0.16)
        for side in (-1,1):
            e=hw(s1)*0.88
            x0,y0=s0*L,mid(s0); x2,y2=s1*L,mid(s1)+side*e
            cx,cy=(s0+0.04)*L, mid(s0)+side*e*0.75
            pts=[((1-t)**2*x0+2*(1-t)*t*cx+t*t*x2,(1-t)**2*y0+2*(1-t)*t*cy+t*t*y2) for t in [i/8 for i in range(9)]]
            out.append(band(T(pts),[lw*(0.95-0.8*i/8) for i in range(9)]))
            # engraved hatching on shaded half (+1 side)
            if hatch and side==1 and k<nv-1:
                s0b=0.1+(k+1.5)*0.78/nv
                for h in (0.33,0.66):
                    sa=s0+(s0b-s0)*h; sb=min(0.97,sa+0.14)
                    e2=hw(sb)*0.7
                    hx0,hy0=sa*L,mid(sa)+hw(sa)*0.18; hx2,hy2=sb*L,mid(sb)+e2
                    hp=[(hx0+(hx2-hx0)*t, hy0+(hy2-hy0)*t) for t in [i/4 for i in range(5)]]
                    out.append(band(T(hp),[lw*0.45*(1-0.6*i/4) for i in range(5)]))
    return out

# ---------- fruit ----------
def berry(cx,cy,rx,ry,a=0,shade=40,calyx=True):
    out=[]
    N=48; outer=[];inner=[]
    for i in range(N+1):
        th=2*math.pi*i/N
        w=0.35+0.75*max(0,math.cos(th-math.radians(shade)))
        outer.append(((rx+w/2)*math.cos(th),(ry+w/2)*math.sin(th)))
        inner.append(((rx-w/2)*math.cos(th),(ry-w/2)*math.sin(th)))
    o=xf(outer,cx,cy,a); n=xf(inner,cx,cy,a)[::-1]
    out.append(('eo','M'+'L'.join(F(x)+' '+F(y) for x,y in o)+'ZM'+'L'.join(F(x)+' '+F(y) for x,y in n)+'Z'))
    for k,f in enumerate((0.72,0.52,0.32)):
        pts=[]; 
        for i in range(13):
            th=math.radians(shade)-1.1+2.2*i/12
            pts.append(((rx*f+rx*(1-f)*0.6)*math.cos(th)*0.95,(ry*f+ry*(1-f)*0.6)*math.sin(th)*0.95))
        out.append(band(xf(pts,cx,cy,a),[0.42*math.sin(math.pi*i/12)+0.05 for i in range(13)]))
    if calyx:
        th=math.radians(shade+180)
        px,py=xf([(rx*0.75*math.cos(th),ry*0.75*math.sin(th))],cx,cy,a)[0]
        out.append(band([(px-1.1,py),(px+1.1,py)],[0.6,0.6])); out.append(band([(px,py-1.1),(px,py+1.1)],[0.6,0.6]))
    return out

def render(parts):
    s=[]
    for p in parts:
        if isinstance(p,tuple): s.append(f'<path fill-rule="evenodd" d="{p[1]}"></path>')
        else: s.append(f'<path d="{p}"></path>')
    return ''.join(s)

# ---------- species ----------
def coffee_branch(p, nodes, sizes, wbase=3.2, berries_at=(), flip_start=1, rng=None):
    rng=rng or random.Random(3); out=[]
    out.append(curve_band(p,wbase,0.6,40,lambda t: wbase*(1-t)**0.8+0.5))
    for t,Lf in zip(nodes,sizes):
        x,y=bez(p,t); a0=ang(p,t)
        out.append(band([(x-1.6,y),(x+1.6,y)],[1.2,1.2]))  # node
        for side in (-1,1):
            aa=a0+side*(46+rng.uniform(-8,8))
            out+=leaf(x,y,aa,Lf*rng.uniform(0.88,1.06),'coffee',flip=side,bend=0.08*side,rng=rng,turn=rng.choice([1,1,0.8,0.62]))
        if t in berries_at:
            for i,(dx,dy) in enumerate([(6,8),(-5,10),(11,0),(1,18),(13,13),(-9,2)]):
                r=7.4+rng.uniform(-0.7,0.9)
                out.append(band([(x,y),(x+dx*0.9,y+dy*0.9)],[0.9,0.6]))
                out+=berry(x+dx*1.35,y+dy*1.35,r,r*1.15,a0+90+rng.uniform(-20,20),shade=35)
    x,y=bez(p,1); out+=leaf(x,y,ang(p,1),sizes[-1]*0.55,'coffee',bend=0.04,rng=rng)
    return out

def olive_branch(p, nodes, sizes, wbase=2.2, olives=(), rng=None):
    rng=rng or random.Random(5); out=[]
    out.append(curve_band(p,wbase,0.5,40,lambda t: wbase*(1-t)**0.7+0.45))
    for i,(t,Lf) in enumerate(zip(nodes,sizes)):
        x,y=bez(p,t); a0=ang(p,t); side=1 if i%2 else -1
        out+=leaf(x,y,a0+side*(32+rng.uniform(-8,10)),Lf*rng.uniform(0.9,1.08),'olive',flip=side,bend=0.12*side,rng=rng,turn=rng.choice([1,1,0.75]))
        if i%3==1:
            out+=leaf(x,y,a0-side*(48+rng.uniform(-6,6)),Lf*0.7,'olive',flip=-side,bend=-0.08*side,rng=rng)
    x,y=bez(p,1); out+=leaf(x,y,ang(p,1),sizes[-1]*0.8,'olive',bend=0.05,rng=rng)
    for (t,dx,dy,a) in olives:
        x,y=bez(p,t)
        q=((x,y),(x+dx*0.3,y+dy*0.2),(x+dx*0.7,y+dy*0.8),(x+dx,y+dy))
        out.append(curve_band(q,0.9,0.5,10))
        out+=berry(x+dx+math.cos(math.radians(a))*8,y+dy+math.sin(math.radians(a))*8,6.0,8.4,a-90,shade=30,calyx=False)
    return out

def fern(p, n=20, Lmax=58, wbase=2.2, rng=None):
    rng=rng or random.Random(9); out=[]
    out.append(curve_band(p,wbase,0.3,40,lambda t: wbase*(1-t)+0.3))
    for i in range(n):
        t=0.08+0.88*i/n
        x,y=bez(p,t); a0=ang(p,t)
        Lp=Lmax*(math.sin(math.pi*min(1,t*1.1+0.05))**0.45)*(1-0.62*t)+3
        for side in (-1,1):
            tt=t+(0.012 if side>0 else 0)
            x2,y2=bez(p,min(tt,1))
            out+=leaf(x2,y2,a0+side*(64-22*t+rng.uniform(-5,5)),Lp*rng.uniform(0.9,1.08),'pinna',flip=side,bend=0.16*side,veins=3 if Lp>18 else 0,hatch=Lp>22,rng=rng,turn=rng.uniform(0.8,1))
    return out
