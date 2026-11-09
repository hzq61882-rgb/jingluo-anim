# 火音 · 徵调 (G zhi pentatonic: G A C D E), same synth approach as 01/02 金音 (pad + chimes + bowls + reverb)
import numpy as np, wave, os
OUTDIR=os.path.dirname(os.path.abspath(__file__))
SR=44100; T=30.0; N=int(SR*T); t=np.arange(N)/SR
rng=np.random.default_rng(10)
out=np.zeros((2,N))
def hz(m): return 440*2**((m-69)/12)
deg=[67,69,72,74,76,79,81,84,86,88]          # G4 A4 C5 D5 E5 G5 A5 C6 D6 E6 — 徵为主
mel=[0,1,2,3,2,4,3,5,4,3,5,6,5,7,6,5,4,5,6,4,3,1,0]
TIMES=[1.8,2.6,3.4,4.3,5.3,6.1,6.8,7.6,8.7,10.0,11.0,11.9,12.9,14.0,15.3,16.8,17.9,18.9,19.8,20.8,22.0,23.0,24.3]
# warm pad: open fifths on G (G2 D3 G3 B3 D4) — brighter, fire colour
for m,a in [(43,0.09),(50,0.075),(55,0.05),(59,0.025),(62,0.03)]:
    f=hz(m)
    for ch,det in [(0,-0.2),(1,0.22)]:
        lfo=0.55+0.45*np.sin(2*np.pi*(0.04+0.012*ch)*t+m*0.7)
        out[ch]+=a*lfo*(np.sin(2*np.pi*(f+det)*t)+0.2*np.sin(2*np.pi*2*(f+det)*t)+0.1*np.sin(2*np.pi*3*(f+det)*t))
def strike(t0,f,amp,pan,parts):
    i0=int(t0*SR); tt=t[:N-i0]; s=np.zeros_like(tt)
    for r,a,dec in parts: s+=a*np.sin(2*np.pi*f*r*tt+rng.random()*6)*np.exp(-tt*dec)
    s*=np.minimum(1,tt/0.004)*amp
    out[0,i0:]+=s*(1-pan); out[1,i0:]+=s*pan
BOWL=[(1,1.0,0.22),(2.71,0.5,0.38),(5.15,0.22,0.7),(8.43,0.08,1.2)]
for t0,m,a,p in [(0.25,43,0.22,0.5),(10.0,50,0.15,0.6),(15.3,55,0.14,0.4),(20.8,50,0.14,0.5),(24.3,43,0.2,0.5)]:
    i0=int(t0*SR); tt=t[:N-i0]; s=np.zeros_like(tt)
    for r,aa,dec in BOWL: s+=aa*np.sin(2*np.pi*hz(m)*r*tt)*np.exp(-tt*dec)*(1+0.35*np.sin(2*np.pi*(0.9+r*0.25)*tt))
    s*=np.minimum(1,tt/0.01)*a; out[0,i0:]+=s*(1-p); out[1,i0:]+=s*p
CHIME=[(1,1.0,1.0),(2.76,0.5,1.9),(5.40,0.28,3.2),(8.93,0.14,5.5),(13.34,0.06,8)]
KEYI=[0,2,3,4,5,9,13,16,19,20,22]
for k,(t0,i) in enumerate(zip(TIMES,mel)):
    strike(t0,hz(deg[i]),0.15 if k<22 else 0.2,0.75-0.5*k/22,CHIME)
    if k in KEYI: strike(t0+0.12,hz(deg[i]+7),0.06,0.5,CHIME)
# closing: soft G-zhi chord swell
for m in (55,62,67,71,74): strike(25.6,hz(m),0.05,0.5,[(1,1.0,0.5),(2.0,0.3,1.2)])
nz=rng.standard_normal((2,N))
for ch in range(2):
    hp=nz[ch]-np.convolve(nz[ch],np.ones(30)/30,'same')
    out[ch]+=0.01*np.convolve(hp,np.ones(6)/6,'same')*(0.5+0.5*np.sin(2*np.pi*0.05*t+2*ch))
L=int(SR*3.2); ir_t=np.arange(L)/SR; wet=np.zeros_like(out)
nfft=1<<int(np.ceil(np.log2(N+L)))
for ch in range(2):
    ir=rng.standard_normal(L)*np.exp(-ir_t*1.9); ir[:int(0.025*SR)]=0; ir/=np.sqrt((ir**2).sum())
    wet[ch]=np.fft.irfft(np.fft.rfft(out[ch],nfft)*np.fft.rfft(ir,nfft),nfft)[:N]
mix=0.68*out+0.5*wet
mix*=np.minimum(1,t/2.0)*np.minimum(1,(T-t)/3.0)
mix=np.tanh(mix*1.2)/1.2
mix*=10**(-7/20)/np.abs(mix).max()
pcm=(mix.T*32767).astype(np.int16)
w=wave.open(f'{OUTDIR}/huo_sj.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
print('ok')
