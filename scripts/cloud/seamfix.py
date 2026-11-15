import numpy as np
XS=np.array([-0.14,-0.13,-0.11,-0.09,-0.07,-0.05,-0.03,-0.01,0.01,0.03,0.05,0.07,0.09,0.11,0.13,0.14])
SS=np.array([1.430,1.430,1.434,1.439,1.439,1.433,1.428,1.403,1.424,1.444,1.454,1.444,1.439,1.431,1.431,1.431])
T=1.438
def ss(t): t=np.clip(t,0,1); return t*t*(3-2*t)
def disp(P):
    x,y,z=P[:,0],P[:,1],P[:,2]
    s=np.interp(x,XS,SS)
    d=(T-s)*(1-ss((abs(x)-0.095)/0.04))            # seam displacement, tapered at the sides
    wz=ss((-z-0.0)/0.02)                           # rear only
    h=y-s
    w=np.where(h>=0,1-ss(h/0.03),np.exp(-(h/0.012)**2))
    m=(abs(x)<0.14)&(y>1.37)&(y<1.5)
    y1=y+np.where(m,d*w*wz,0)
    tx=1-ss((abs(x)-0.095)/0.04)
    wb=1-ss(abs(y1-T)/0.025)
    y2=y1+np.where(m,(T-y1)*0.85*wb*tx*wz,0)
    out=np.zeros_like(P); out[:,1]=y2-y
    return out
