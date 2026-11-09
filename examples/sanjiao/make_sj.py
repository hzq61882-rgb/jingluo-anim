# 10 手少阳三焦经 · 准确版 · 火音  (30 s, 1920x1080)
# Posterior view (back of figure). Figure's RIGHT arm (viewer right) abducted, palm forward,
# so the DORSUM of hand / extensor side of forearm / posterior upper arm faces the viewer.
# => radial (thumb) side is UP, ulnar (little finger) side is DOWN.
import numpy as np, math, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1920,1080; FPS=30; T=30.0; N=int(T*FPS)
OUTDIR=os.path.dirname(os.path.abspath(__file__))
FB='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FR='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
_fc={}
def F(s,b=True):
    k=(int(s),b)
    if k not in _fc: _fc[k]=ImageFont.truetype(FB if b else FR,int(s),index=2)
    return _fc[k]
P=lambda *a: np.array(a,dtype=float)
def ease(x): x=max(0.,min(1.,x)); return x*x*(3-2*x)
def text(dr,xy,s,f,fill,anchor='la',stroke=0,sf=(4,10,28)):
    dr.text(tuple(xy),s,font=f,fill=fill,anchor=anchor,stroke_width=stroke,stroke_fill=sf)
# ---------------- main geometry ----------------
MID=560.; HC=P(MID,190.); U=66.; HRY=82.
S=P(MID+140,345.); ang=math.radians(8); d=P(math.cos(ang),math.sin(ang)); n=P(d[1],-d[0])  # n = up (radial side)
def arm(t,off=0): return S+d*t+n*off
CU=38.; tE=402.; tW=tE+12*CU          # olecranon -> wrist = 12 cun
CUU=40.                               # upper-arm cun
def hw(t):
    if t<=tE: return 50-(t/tE)*11
    return 39-((t-tE)/(tW-tE))*12
WR=arm(tW,0); HS=1.7
def hand(t,off): return WR+(d*t+n*off)*HS
CMC=(10,21); MCP=(50,55); IP=(76,70); TIP=(100,79)   # thumb UP
def hv(p): return hand(*p)
FING=[(-22,50,9.5),(-8,63,10.5),(6,68,11),(22,60,10.5)]  # little(lowest), ring, middle, index
def fpt(off,t): return hand(t,off*(1+0.1*(t-92)/60))
def fore(k,f=-0.06): t=tW-k*CU; return arm(t,f*hw(t))
NM=["关冲","液门","中渚","阳池","外关","支沟","会宗","三阳络","四渎","天井","清冷渊","消泺","臑会","肩髎","天髎",
    "天牖","翳风","瘈脉","颅息","角孙","耳门","耳和髎","丝竹空"]
LOC={1:"无名指末节尺侧，指甲根角侧上方0.1寸",2:"手背，第4、5指间，指蹼缘上方赤白肉际凹陷中",
 3:"手背，第4、5掌骨间，第4掌指关节近端凹陷中",4:"腕背侧远端横纹上，指伸肌腱尺侧缘凹陷中",
 5:"腕背侧远端横纹上2寸，尺骨与桡骨间隙中点",6:"腕背侧远端横纹上3寸，尺骨与桡骨间隙中点",
 7:"腕背侧远端横纹上3寸，尺骨的桡侧缘（支沟尺侧）",8:"腕背侧远端横纹上4寸，尺骨与桡骨间隙中点",
 9:"肘尖下5寸，尺骨与桡骨间隙中点",10:"肘尖（尺骨鹰嘴）上1寸凹陷中",11:"肘尖与肩峰角连线上，肘尖上2寸",
 12:"肘尖与肩峰角连线上，肘尖上5寸",13:"肩峰角下3寸，三角肌后下缘",14:"肩峰角与肱骨大结节两骨间凹陷中",
 15:"肩胛骨上角骨际凹陷中",16:"横平下颌角，胸锁乳突肌后缘凹陷中",17:"耳垂后方，乳突下端前方凹陷中",
 18:"乳突中央，角孙至翳风沿耳轮弧形连线的上2/3与下1/3交点",19:"角孙至翳风沿耳轮弧形连线的上1/3与下2/3交点",
 20:"耳尖正对发际处",21:"耳屏上切迹与下颌骨髁突之间凹陷中",22:"鬓发后缘，耳廓根前方，颞浅动脉后缘",23:"眉梢凹陷中"}
KEY={1,3,4,5,6,10,14,17,20,21,23}
POS={1:fpt(-8,149)-n*5, 2:fpt(-15,93), 3:hand(72,-14), 4:arm(tW,-0.14*hw(tW)),
     5:fore(2),6:fore(3),7:arm(tW-3*CU,-0.55*hw(tW-3*CU)),8:fore(4),9:arm(tE+5*CU,-0.06*hw(tE+5*CU)),
     10:arm(tE-1*CUU,0),11:arm(tE-2*CUU,0),12:arm(tE-5*CUU,0),13:arm(12+3*CUU,-0.2*hw(132)),14:arm(10,0.42*hw(10)),
     15:P(MID+80,356.),16:P(MID+41,262.),17:P(MID+55,221.),18:P(MID+55,207.),19:P(MID+55,192.),20:P(MID+60,177.)}
TIMES={}
for i,v in zip(range(1,24),[1.8,2.6,3.4,4.3,5.3,6.1,6.8,7.6,8.7,10.0,11.0,11.9,12.9,14.0,15.3,16.8,17.9,18.9,19.8,20.8,22.0,23.0,24.3]): TIMES[i]=v
T_END=TIMES[23]
def dens(poly,step=0.8,smooth=5):
    out=[poly[0]]
    for a,b in zip(poly[:-1],poly[1:]):
        k=max(1,int(np.linalg.norm(b-a)/step))
        for i in range(1,k+1): out.append(a+(b-a)*i/k)
    out=np.array(out)
    for _ in range(smooth):
        sm=out.copy(); sm[1:-1]=(out[:-2]+2*out[1:-1]+out[2:])/4; out=sm
    s=np.concatenate([[0],np.cumsum(np.linalg.norm(np.diff(out,axis=0),axis=1))])
    return out,s
class Seg:
    def __init__(s,poly,anchors,tstart,tend=None,step=0.8):
        s.P,s.S=dens(poly,step)
        s.anc=[(0.0,tstart)]; last=0
        for p,t in anchors:
            dd=np.linalg.norm(s.P-p,axis=1); dd[:last]=1e9; j=int(np.argmin(dd)); last=j
            s.anc.append((s.S[j],t))
        if tend is not None: s.anc.append((s.S[-1],tend))
        s.t0=tstart; s.t1=s.anc[-1][1]
    def s_at(s,t):
        if t<=s.t0: return -1
        if t>=s.t1: return s.S[-1]
        for (a0,b0),(a1,b1) in zip(s.anc[:-1],s.anc[1:]):
            if b0<=t<=b1:
                x=(t-b0)/(b1-b0); x=x*x*(3-2*x)*0.35+x*0.65; return a0+(a1-a0)*x
        return s.S[-1]
outer=[POS[1],fpt(-8,140),fpt(-11,112),POS[2],POS[3],hand(30,-10),POS[4],POS[5],POS[6],POS[8],POS[9],arm(tE+1.5*CU,-0.03*hw(tE)),
       POS[10],POS[11],POS[12],POS[13],arm(40,0.3*hw(40)),POS[14],P(MID+118,330.),POS[15],P(MID+62,318.),P(MID+44,292.),POS[16],
       P(MID+50,238.),POS[17],POS[18],POS[19],POS[20]]
SM=Seg(outer,[(POS[i],TIMES[i]) for i in range(1,21) if i!=7],TIMES[1]-0.01)
SM.anc[0]=(0.0,TIMES[1]-0.01); SM.anc[1]=(0.0,TIMES[1])
# ---------------- lateral head inset (right side, face to viewer right) ----------------
BOX=(16,24,476,604)
ISC=1.5
def IV(p): return P(128,46)+(np.asarray(p,float)-P(100,150))*ISC
EARC=P(190,268); ERX,ERY=24,36
arc=[P(184,314),P(166,302),P(157,280),P(156,258),P(164,238),P(176,226),P(190,222)]
ARC,ARS=dens(arc,0.5,6)
def arcpt(f): return ARC[np.argmin(np.abs(ARS-f*ARS[-1]))]   # f from 翳风(0) to 角孙(1)
IP={16:P(168,352),17:P(184,314),18:arcpt(1/3),19:arcpt(2/3),20:P(190,222),21:P(224,258),22:P(238,238),23:P(259,234)}
GB1=P(278,255)   # 瞳子髎
ipath=[P(150,470),P(160,410),IP[16],P(178,334),]+[p for p in ARC[::6]]+[IP[20],P(180,236),P(186,256),P(204,266),IP[21],P(232,249),IP[22],P(246,232),IP[23],P(270,244),GB1]
SI=Seg([IV(p) for p in ipath],[(IV(IP[i]),TIMES[i]) for i in range(16,24)],TIMES[15]+0.6,TIMES[23]+0.7,step=0.6)
# ---------------- base art ----------------
SS=2
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
top=np.array([14,32,70],np.float32); bot=np.array([3,8,22],np.float32)
g=(yy/H)[...,None]; bg=top*(1-g)+bot*g
r=np.sqrt(((xx-900)/1300)**2+((yy-420)/900)**2)
bg=bg*(1.25-0.6*np.clip(r,0,1))[...,None]
BG=Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).convert('RGBA')
def body_mask():
    im=Image.new('L',(W*SS,H*SS),0); dr=ImageDraw.Draw(im)
    def X(p): q=np.asarray(p)*SS; return (q[0],q[1])
    def Q(pts): return [X(p) for p in pts]
    def E(c,rx,ry): dr.ellipse([(c[0]-rx)*SS,(c[1]-ry)*SS,(c[0]+rx)*SS,(c[1]+ry)*SS],fill=255)
    def L(a,b,w): dr.line([X(a),X(b)],fill=255,width=max(1,int(w*2*SS))); E(b,w,w); E(a,w,w)
    E(HC,U,HRY); E(HC+P(-U+2,8),9,17); E(HC+P(U-2,8),9,17)
    dr.polygon(Q([P(MID-36,255),P(MID+36,255),P(MID+42,322),P(MID-42,322)]),fill=255)
    M=MID-330
    dr.polygon(Q([P(x+M,y) for x,y in [(190,330),(250,312),(300,302),(360,302),(410,312),(470,325),(505,360),(480,470),(455,600),(440,720),(452,820),(470,1000),(190,1000),(208,820),(220,720),(205,600),(180,470),(150,360)]]),fill=255)
    E(P(185+M,350),45,48); E(P(478+M,352),44,46)
    dr.polygon(Q([P(x+M,y) for x,y in [(140,345),(205,360),(190,560),(178,740),(140,740),(128,560),(120,400)]]),fill=255)
    dr.polygon(Q([P(x+M,y) for x,y in [(140,740),(178,740),(176,820),(150,830),(136,800)]]),fill=255)
    a=[];b=[]
    for t in np.linspace(0,tW,80): a.append(X(arm(t,hw(t)))); b.append(X(arm(t,-hw(t))))
    dr.polygon(a+b[::-1],fill=255)
    palm=[hand(0,16),hand(14,20),hand(60,28),hand(96,26),hand(102,14),hand(102,-16),hand(92,-25),hand(40,-26),hand(8,-19),hand(0,-16)]
    dr.polygon(Q(palm),fill=255)
    for off,l,wd in FING: L(fpt(off,92),fpt(off,92+l),wd)
    th=[hand(0,22),hv(CMC),hv(MCP),hv(IP_),hv(TIP)]
    for p0,p1,w0 in zip(th[:-1],th[1:],[22,21,18,16]): L(p0,p1,w0)
    dr.polygon(Q([hand(2,14),hv(CMC),hv(MCP),hand(70,30),hand(40,24)]),fill=255)
    m=im.resize((W,H),Image.LANCZOS)
    fm=np.array(m,np.float32)*np.clip((1000-yy)/160,0,1)
    return Image.fromarray(fm.astype(np.uint8))
IP_=IP_T=(76,70)
def lines_main():
    im=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(im)
    lc=(160,205,255,95)
    def ln(pts,col=lc,w=1): dr.line([tuple(p) for p in pts],fill=col,width=max(1,int(round(w))),joint='curve')
    def el(c,rx,ry,col,fill=None,w=1): dr.ellipse([c[0]-rx,c[1]-ry,c[0]+rx,c[1]+ry],outline=col,fill=fill,width=w)
    ln([P(MID,262),P(MID,700)],(160,205,255,70),1.5)                       # spine
    for k in range(7,23): el(P(MID,262+k*0+ (k-7)*27+60),2,2,(170,210,255,90))  # spinous process hints
    el(P(MID,300),4,4,(170,210,255,140))                                     # C7 (大椎)
    for s in (-1,1):
        sc=[P(MID+s*x,y) for x,y in [(78,356),(48,420),(46,470),(70,505),(112,440),(126,372),(78,356)]]
        ln(sc,(160,205,255,70),1.2)                                          # scapula outline
        ln([P(MID+s*52,392),P(MID+s*128,368),P(MID+s*146,340)],(160,205,255,85),1.5)  # spine of scapula -> acromion
        ln([P(MID+s*20,268),P(MID+s*95,312),P(MID+s*140,332)],(160,205,255,45),1)     # trapezius edge
    # hair (back of head)
    for k in range(-3,4): ln([HC+P(k*14,-70),HC+P(k*16,-20),HC+P(k*15,40)],(170,205,250,45),1)
    ln([HC+P(-50,52),HC+P(0,64),HC+P(50,52)],(170,205,250,70),1)             # hairline nape
    # ears from behind
    for s in (-1,1): el(HC+P(s*(U-2),8),5,11,(170,210,255,100))
    # elbow: olecranon + wrist crease
    el(arm(tE,0),7,7,(170,210,255,140))
    ln([arm(tW,hw(tW)-3),arm(tW,-hw(tW)+3)],(180,215,255,140),2)
    ln([arm(tE+8,hw(tE)*0.55),arm(tW-6,hw(tW)*0.55)],(160,205,255,55),1.5)   # radius (up)
    ln([arm(tE+8,-hw(tE)*0.55),arm(tW-6,-hw(tW)*0.62)],(160,205,255,55),1.5) # ulna (down)
    ln([S+P(-30,-28),arm(10,0.95*hw(10)),arm(150,-0.5*hw(150))],(160,205,255,50),1)   # deltoid posterior border
    for off,l,wd in FING:
        ln([hand(16,off*0.45),fpt(off,90)],(160,205,255,60),1)
        k=fpt(off,92); el(k,wd*0.5,wd*0.5,(180,215,255,90))
        tip=fpt(off,92+l); nb=fpt(off,92+l-wd*1.0/HS*1.4)
        ln([nb,tip-d*3],(200,225,255,95),wd*0.9)
    ln([hv(IP_)+(hv(TIP)-hv(IP_))*0.5,hv(TIP)-(hv(TIP)-hv(IP_))*0.08],(200,225,255,95),10)
    return im
def compose(M,lines,blur=22):
    BODY=Image.new('RGBA',(W,H),(90,150,230,0)); BODY.putalpha(M.point(lambda q:int(q*0.42)))
    EDGE=M.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.2)).point(lambda q:min(255,q*3))
    EL=Image.new('RGBA',(W,H),(140,200,255,0)); EL.putalpha(EDGE.point(lambda q:int(q*0.55)))
    HA=Image.new('RGBA',(W,H),(70,130,230,0)); HA.putalpha(M.filter(ImageFilter.GaussianBlur(blur)).point(lambda q:int(q*0.30)))
    return Image.alpha_composite(Image.alpha_composite(Image.alpha_composite(HA,BODY),EL),lines)
def head_mask():
    im=Image.new('L',(W*SS,H*SS),0); dr=ImageDraw.Draw(im)
    def X(p): q=IV(p)*SS; return (q[0],q[1])
    c=IV(P(200,232)); rx=125*ISC; ry=122*ISC
    dr.ellipse([(c[0]-rx)*SS,(c[1]-ry)*SS,(c[0]+rx)*SS,(c[1]+ry)*SS],fill=255)
    face=[(250,130),(300,165),(322,205),(327,232),(318,248),(330,268),(346,292),(330,302),(336,322),(327,334),(333,346),(320,360),(324,378),(300,394),(250,390),(214,356),(200,300),(160,330)]
    dr.polygon([X(P(*p)) for p in face],fill=255)
    neck=[(140,330),(214,356),(262,392),(296,470),(345,560),(360,640),(70,640),(100,520),(128,420)]
    dr.polygon([X(P(*p)) for p in neck],fill=255)
    return im.resize((W,H),Image.LANCZOS)
def lines_head():
    im=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(im)
    fc=(190,220,255,150)
    def ln(pts,col=fc,w=1.5): dr.line([tuple(IV(P(*p))) for p in pts],fill=col,width=max(1,int(round(w))),joint='curve')
    # ear: helix, antihelix, tragus, lobe
    e=IV(EARC); ex,ey=ERX*ISC,ERY*ISC
    dr.ellipse([e[0]-ex,e[1]-ey,e[0]+ex,e[1]+ey],outline=(200,228,255,190),width=3)
    ln([(194,244),(178,252),(176,276),(186,292),(196,296)],(190,220,255,120),2)    # antihelix
    ln([(204,262),(214,256),(216,268),(212,282),(204,286)],(200,228,255,170),2)    # tragus
    ln([(200,250),(206,246)],(190,220,255,110),1.5)                                 # supratragic notch
    dr.ellipse([*(IV(P(192,272))-7),*(IV(P(192,272))+7)],fill=(40,70,130,200))     # concha / ear canal
    # face
    ln([(262,236),(282,228),(306,229),(318,236)],(200,228,255,190),3)              # eyebrow (lateral end = posterior)
    ln([(280,256),(292,250),(306,254)],fc,2); ln([(280,256),(294,260),(306,256)],fc,1.5)   # eye
    ln([(318,248),(336,276),(346,292)],(170,205,250,110),1.2)                      # nasal dorsum
    ln([(318,300),(326,292)],(170,205,250,110),1.2)                                 # ala
    ln([(330,334),(318,336)],fc,1.5)                                                # lips
    ln([(222,272),(214,330),(214,356),(250,388),(300,394)],(170,205,250,110),1.5)  # mandible (ramus->angle->body)
    ln([(176,318),(180,330)],(170,205,250,110),2)                                   # mastoid tip
    ln([(178,326),(220,430),(270,540)],(160,205,255,80),1.5)                        # SCM posterior border
    ln([(190,322),(250,430),(300,540)],(160,205,255,60),1.2)                        # SCM anterior border
    ln([(228,262),(236,232),(240,200)],(255,140,140,70),1.2)                        # superficial temporal a.
    ln([(150,196),(190,180),(230,190),(244,214),(244,252)],(170,205,250,80),1.2)   # hairline / sideburn
    ln([(250,130),(160,120),(100,170)],(170,205,250,45),1)
    return im
BASE_MAIN=compose(body_mask(),lines_main())
HM=head_mask(); BM=Image.new('L',(W,H),0); ImageDraw.Draw(BM).rounded_rectangle(BOX,18,fill=255)
HM=Image.fromarray(np.minimum(np.array(HM),np.array(BM)))
BASE_INS=compose(HM,lines_head(),14)
INS_BG=Image.new('RGBA',(W,H),(0,0,0,0)); ImageDraw.Draw(INS_BG).rounded_rectangle(BOX,18,fill=(8,20,48,238))
INS_BASE=Image.alpha_composite(INS_BG,BASE_INS)
REG=(P(MID+10,150.),P(MID+100,290.))
# ---------------- labels ----------------
LOFF={1:(P(-30,70),'mm'),2:(P(30,-118),'mm'),3:(P(-10,-150),'mm'),4:(P(-10,100),'mm'),5:(P(20,-112),'mm'),6:(P(-10,-80),'mm'),
      7:(P(-30,95),'mm'),8:(P(-10,-140),'mm'),9:(P(0,92),'mm'),10:(P(0,-86),'mm'),11:(P(-10,90),'mm'),12:(P(0,-86),'mm'),
      13:(P(-20,102),'mm'),14:(P(60,-100),'mm'),15:(P(-40,110),'mm')}
def ilabel(i):
    q=IV(IP[i])
    return {16:(q+P(-30,10),'rm'),17:(q+P(-60,30),'rm'),18:(q+P(-40,4),'rm'),19:(q+P(-40,-6),'rm'),20:(q+P(-40,-40),'rm'),
            21:(q+P(30,80),'lm'),22:(q+P(-10,-70),'mm'),23:(q+P(40,-40),'mm')}[i]
# ---------------- point diagram: flowing ring + radial pulse ----------------
def pfx(dr,p,age,rad,t,key,big=1.0):
    boost=1+1.6*math.exp(-age*1.8)
    R=(rad+8)*big
    col=(255,196,110) if key else (226,234,248)
    # radial energy pulses (expanding rings from centre)
    for k in range(2):
        ph=(t*0.75+k*0.5+p[0]*0.013)%1.0
        rr=rad+ph*R*1.5; a=int((1-ph)**1.5*110*min(boost,1.6))
        dr.ellipse([p[0]-rr,p[1]-rr,p[0]+rr,p[1]+rr],outline=col+(a,),width=1)
    # radial rays streaming outward
    for j in range(8):
        th=j*math.pi/4+0.4
        ph=(t*1.1+j*0.125)%1.0
        r1=rad+2+ph*R*0.9; r2=r1+3*big
        a=int(math.sin(ph*math.pi)*120*min(boost,1.5))
        dr.line([(p[0]+r1*math.cos(th),p[1]+r1*math.sin(th)),(p[0]+r2*math.cos(th),p[1]+r2*math.sin(th))],fill=col+(a,),width=1)
    # circumference: moving dashes around the ring
    ra=R*0.82; bb=[p[0]-ra,p[1]-ra,p[0]+ra,p[1]+ra]
    dr.ellipse(bb,outline=col+(int(60*min(boost,1.5)),),width=1)
    rot=(t*140*(1 if key else -1)+p[1]*3)%360
    for j in range(4): dr.arc(bb,rot+j*90,rot+j*90+38,fill=col+(int(min(255,170*boost)),),width=2)
    # arrival burst
    if age<1.6:
        pulse=rad+2+14*big*(1-math.exp(-age*2.5))
        dr.ellipse([*(p-pulse-3),*(p+pulse+3)],outline=(255,200,120,int(230*math.exp(-age*1.8))),width=2)
    # the point itself: key = solid orange, others = hollow (blank) white ring with orange core
    if key: dr.ellipse([*(p-rad),*(p+rad)],fill=(255,140,40,255),outline=(255,235,200,255),width=2)
    else:
        dr.ellipse([*(p-rad),*(p+rad)],fill=(10,22,50,255),outline=(240,240,245,255),width=2)
        rc=max(1.5,rad*0.38); dr.ellipse([*(p-rc),*(p+rc)],fill=(255,150,60,255))
def path_layer(seg,s,w,hr,moving,tr,t):
    ml=Image.new('RGBA',(W,H),(0,0,0,0)); md=ImageDraw.Draw(ml)
    head=None
    if s>=0:
        k=int(np.searchsorted(seg.S,s))
        if k>=2: md.line([tuple(x) for x in seg.P[:k+1]],fill=(255,125,35,255),width=w,joint='curve')
        # flowing particles inside the pipe
        sp=34.; off=(t*110.)%sp; q=off
        while q<s-4:
            j=int(np.searchsorted(seg.S,q)); x=seg.P[min(j,len(seg.P)-1)]
            pr=w*0.42; md.ellipse([x[0]-pr,x[1]-pr,x[0]+pr,x[1]+pr],fill=(255,236,190,235)); q+=sp
        head=seg.P[min(len(seg.P)-1,k)]
        if moving: md.ellipse([*(head-hr),*(head+hr)],fill=(255,240,200,255))
    sm=ml.resize((W//2,H//2),Image.BILINEAR)
    g1=sm.filter(ImageFilter.GaussianBlur(7)).resize((W,H),Image.BILINEAR)
    g2=sm.filter(ImageFilter.GaussianBlur(2)).resize((W,H),Image.BILINEAR)
    return Image.alpha_composite(Image.alpha_composite(Image.alpha_composite(g1,g1),g2),ml),head
CAPS=[(0,2.2,"三焦手少阳之脉，起于小指次指之端","起于无名指尺侧端 · 关冲"),
 (2.2,4.8,"上出两指之间，循手表腕","出第4、5指间 · 液门 → 中渚 → 阳池"),
 (4.8,9.4,"出臂外两骨之间","沿前臂背面尺骨与桡骨之间上行 · 外关、支沟"),
 (9.4,10.6,"上贯肘","天井：尺骨鹰嘴上1寸"),
 (10.6,14.6,"循臑外上肩","沿上臂后侧上行 · 清冷渊 → 消泺 → 臑会 → 肩髎"),
 (14.6,16.4,"而交出足少阳之后，入缺盆","天髎（肩胛上角）· 布膻中，散络心包，下膈，循属三焦"),
 (16.4,20.4,"其支者：从膻中上出缺盆，上项，系耳后直上","天牖 → 翳风 → 瘈脉 → 颅息，沿耳后上行"),
 (20.4,21.6,"出耳上角，以屈下颊至䪼","角孙：耳尖直上入发际"),
 (21.6,25.4,"其支者：从耳后入耳中，出走耳前","耳门 → 耳和髎 → 丝竹空"),
 (25.4,30.1,"交颊，至目锐眦","至外眼角（瞳子髎），交足少阳胆经")]
CX=1250
def frame(fi):
    t=fi/FPS
    im=BG.copy()
    fade=ease(t/1.2)
    b=BASE_MAIN
    if fade<1: b=b.copy(); b.putalpha(b.split()[3].point(lambda q:int(q*fade)))
    im=Image.alpha_composite(im,b)
    sm=SM.s_at(t); moving=SM.t0-0.3<t<SM.t1+0.3
    lay,head=path_layer(SM,sm,6,10,moving,0,t)
    im=Image.alpha_composite(im,lay); dr=ImageDraw.Draw(im)
    if moving and head is not None:
        pr=16+4*math.sin(t*12); dr.ellipse([*(head-pr),*(head+pr)],outline=(255,210,140,150),width=2)
    cur=None
    for i in range(1,24):
        if t>=TIMES[i]-0.02: cur=i
    for i in range(1,21):
        if t>=TIMES[i]-0.02:
            age=t-TIMES[i]; p=POS[i]
            if i>=16:
                dr.ellipse([*(p-3.5),*(p+3.5)],fill=(255,140,40,255),outline=(255,235,200,255),width=1); continue
            key=i in KEY
            pfx(dr,p,age,6.5 if key else 5,t,key,0.9 if i<=3 else 1.0)
            off,anc=LOFF[i]; lp=p+off; a=int(255*ease(age*3))
            end=lp+P(0,16 if key else 13) if off[1]<0 else lp-P(0,18 if key else 14)
            dr.line([tuple(p),tuple(end)],fill=(255,190,120,int(a*0.7)),width=2 if key else 1)
            if key: text(dr,lp,f"{NM[i-1]} TE{i}",F(27),(255,215,160,a),anc,4)
            else: text(dr,lp,f"{NM[i-1]} TE{i}",F(21),(240,200,160,int(a*0.92)),anc,3)
    ta=int(200*ease((t-0.8)/1.0))
    text(dr,arm((tE+tW)/2,-hw((tE+tW)/2))+P(-10,150),"前臂背面 · 尺桡骨之间（阳面）",F(21,False),(150,210,255,ta),'mm',3)
    text(dr,P(MID,760),"背面观",F(22,False),(150,210,255,ta),'mm',3)
    fa=int(230*ease((t-1.0)/0.8))
    text(dr,fpt(-8,158)+P(12,-4),"无名指",F(22),(150,215,255,fa),'lm',3)
    text(dr,hv(TIP)+P(18,-18),"拇指",F(20,False),(150,215,255,int(fa*0.85)),'lm',3)
    # ---- inset: lateral head ----
    ia=ease((t-0.4)/1.0)
    if ia>0:
        lay=INS_BASE.copy()
        si=SI.s_at(t); mv=SI.t0<t<SI.t1+0.3
        pl,hh=path_layer(SI,si,7,9,mv,0,t)
        lay=Image.alpha_composite(lay,pl); ld=ImageDraw.Draw(lay)
        if t>=TIMES[23]+0.6:
            q=IV(GB1); ld.ellipse([*(q-6),*(q+6)],outline=(150,215,255,255),width=2)
            text(ld,q+P(14,28),"瞳子髎",F(17),(150,215,255,255),'lm',3)
            text(ld,q+P(14,50),"交足少阳",F(16,False),(150,215,255,255),'lm',3)
        for i in range(16,24):
            if t>=TIMES[i]-0.02:
                age=t-TIMES[i]; q=IV(IP[i]); key=i in KEY
                pfx(ld,q,age,6.5 if key else 5.5,t,key,1.0)
                lp,anc=ilabel(i); a=int(255*ease(age*3))
                ld.line([tuple(q),tuple(lp+(P(4,0) if anc=='rm' else P(-4,0)))],fill=(255,190,120,int(a*0.75)),width=2 if key else 1)
                if key: text(ld,lp,f"{NM[i-1]} TE{i}",F(23),(255,215,160,a),anc,4)
                else: text(ld,lp,f"{NM[i-1]} TE{i}",F(19),(240,200,160,a),anc,3)
        text(ld,(BOX[0]+16,BOX[1]+22),"头颈部放大（右侧面观）",F(19,False),(150,210,255,230),'lm',2)
        text(ld,(BOX[2]-14,BOX[1]+22),"后 ← → 前",F(16,False),(150,210,255,200),'rm',2)
        ld.rounded_rectangle(BOX,18,outline=(120,190,255,200),width=2)
        mk=BM.point(lambda q:int(q*ia))
        im.paste(lay,(0,0),mk); dr=ImageDraw.Draw(im)
        a0,b0=REG; ca=int(170*ia)
        dr.rectangle([a0[0],a0[1],b0[0],b0[1]],outline=(120,190,255,ca),width=1)
        dr.line([(BOX[2],BOX[1]+20),(a0[0],a0[1])],fill=(120,190,255,int(ca*0.6)),width=1)
        dr.line([(BOX[2],BOX[3]-20),(a0[0],b0[1])],fill=(120,190,255,int(ca*0.6)),width=1)
    # ---- title & captions ----
    ta=int(255*ease(t/0.8))
    text(dr,(CX,78),"手少阳三焦经",F(64),(255,155,60,ta),'mm')
    text(dr,(CX,132),"HAND  SHAOYANG  SANJIAO  MERIDIAN",F(26),(190,215,245,ta),'mm')
    text(dr,(CX,178),"起于关冲穴（TE1），止于丝竹空穴（TE23）",F(30,False),(225,232,245,ta),'mm')
    for a0_,a1_,c1,c2 in CAPS:
        if a0_<=t<a1_:
            al=int(255*min(ease((t-a0_)/0.4),ease((a1_-t)/0.4) if a1_<T else 1))
            text(dr,(CX,700),c1,F(34),(255,205,140,al),'mm',3)
            text(dr,(CX,746),c2,F(25,False),(210,222,240,al),'mm',3)
    if cur is not None:
        if t<T_END+1.2:
            i=cur; nm=NM[i-1]; age=t-TIMES[i]; al=int(255*ease(age*4))
            dr.rounded_rectangle([CX-470,790,CX+470,900],18,outline=(255,140,50,al),width=2,fill=(10,22,50,int(al*0.85)))
            text(dr,(CX-430,830),nm,F(46),(255,165,70,al),'lm')
            text(dr,(CX-430+48*len(nm)+20,834),f"TE{i}",F(32),(255,225,190,al),'lm')
            loc=LOC[i]; text(dr,(CX-430,875),loc,F(25 if len(loc)<=32 else 22,False),(225,232,245,al),'lm')
        else:
            al=int(255*ease((t-T_END-1.2)*2))
            dr.rounded_rectangle([CX-470,790,CX+470,900],18,outline=(255,140,50,al),width=2,fill=(10,22,50,int(al*0.85)))
            text(dr,(CX,828),"手少阳三焦经 · 单侧23穴",F(36),(255,165,70,al),'mm')
            text(dr,(CX,872),"起于无名指关冲，止于眉梢丝竹空 · 流注亥时（21–23点）",F(25,False),(225,232,245,al),'mm')
    for i in range(1,24):
        x=CX+(i-12)*34; on=t>=TIMES[i]-0.02
        if on: dr.ellipse([x-11,963,x+11,985],fill=(255,140,40,70))
        dr.ellipse([x-7,967,x+7,981],fill=(255,140,40) if on else (45,62,95))
    text(dr,(60,1040),"久真堂新九针课程专用",F(28),(200,215,240,230),'lm',3)
    text(dr,(1860,1032),"10",F(64),(255,155,60,235),'rm')
    return im.convert('RGB')
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]!='render':
        for tt in sys.argv[1:]:
            frame(int(float(tt)*FPS)).save(f'{OUTDIR}/frames/f_{tt}.png')
        sys.exit()
    from multiprocessing import Pool
    p=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p',f'{OUTDIR}/sj_noaudio.mp4'],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
    with Pool(6) as pool:
        for im in pool.imap(frame,range(N),chunksize=4): p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()
