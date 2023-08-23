# Binomial fit, with likelihood output of growth rate, and possibly introduction day
# What happens if you add a day-of-introduction parameter?
# Explain (a_i, b_i)   a_i=non-variant, b_i=variant,
# by assuming a_i+b_i is given and that b_i ~ B(a_i+b_i, p_i)
# where p_i/(1-p_i) = exp(c + (i-i0)*g)  if i>=i0
#                   = 0                  if i<i0
# But c isn't allowed to be arbitrary, because on the day of introduction
# we expect the odds to be on the order of (a few)/number_of_cases, i.e.,
# c should be about -log(number_of_cases/(a few)).
# So in that case, we don't need to add the 0 for i<i0, because p_i will be
# essentially zero for i<i0 anyway (assuming g>=0), given that we're sequencing
# far fewer than the number of infections. So we're back to normal binomial regression.
#
# So here we do normal binomial regression,
# where p_i/(1-p_i) = exp(c + i*g)
#
# outputting a likelihood for g, assuming g>=0.

import numpy as np
from math import exp,log,sqrt,floor
from stuff import *

# Variant0, Variant1 counts by day
N0=[];N1=[];DT=[]
for x in sys.stdin:
  if x[0]=='#': continue
  y=x.strip().split()
  d=datetoday(y[0])
  v0,v1=int(y[1]),int(y[2])
  N0.append(v0);N1.append(v1);DT.append(d)

minday=min(DT)
maxday=max(DT)+1
ndays=maxday-minday
V0=np.zeros(ndays)
V1=np.zeros(ndays)
for (v0,v1,dt) in zip(N0,N1,DT):
  V0[dt-minday]=v0
  V1[dt-minday]=v1

# p_i/(1-p_i) = exp(xx[0] + i*xx[1]), i=0, 1, ..., ndays-1
def LL(g,pr=0):
  c=-log(ipd)-intro*g
  logodds=c+np.arange(ndays)*g
  Z=np.log(1+np.exp(logodds))
  return np.sum(V1*(logodds-Z)-V0*Z)

ipd=10000# infections per day
firstseen=min(i for i in range(ndays) if V1[i]>0)

# Assuming on day of introduction odds are 1/ipd
# So xx[0] + intro*xx[1] = -log(ipd)
# Then (assuming xx[1]>=0) we want to bound xx[0] + ndays*xx[1] in a sensible way
# So (ndays-intro)*xx[1]-log(ipd) <= 10, say. (Assuming it hasn't swept yet.)
# and xx[1] <= (10+log(ipd))/(ndays-intro)
# But also, there needs to be a sensible chance of seeing on the first day it was seen, so
# xx[0] + firstseen*xx[1] >= -10 say
# (firstseen-intro)*xx[1] >= -10 + log(ipd) (with intro < firstseen)
# (log(ipd)-10)/(firstseen-intro) <= xx[1] <= (log(ipd)+10)/(ndays-intro)
# (log(ipd)-10)*(ndays-intro) <= (log(ipd)+10)*(firstseen-intro)
# 20*intro <= (log(ipd)+10)*firstseen - (log(ipd)-10)*ndays
# intro <= ((log(ipd)+10)*firstseen - (log(ipd)-10)*ndays)/20

dg=0.001
def g2bin(g): return int(floor(g/dg+0.5))
def bin2g(b): return b*dg

maxintro = min(firstseen, int( ((log(ipd)+10)*firstseen - (log(ipd)-10)*ndays)/20+1 ))
l=[]
dsum={}# Integrating over nuisance parameter (c or intro)
dmax={}# Maximising over nuisance parameter (c or intro)
for intro in np.arange(0,maxintro,0.25):
  ming,maxg = max((log(ipd)-10)/(firstseen-intro),0), max((log(ipd)+10)/(ndays-intro),0)
  for g in np.arange(bin2g(g2bin(ming)),bin2g(g2bin(maxg)),dg):
    ll=LL(g);el=exp(ll)
    dsum[g]=dsum.get(g,0)+el
    dmax[g]=max(dmax.get(g,0),el)
    #print("%8.3f %10.6f %10.6f %12g"%(intro,g,ll,el),file=fp)

for method,d in ("sum",dsum),("max",dmax):
  t=sum(d.values())
  for g in d: d[g]/=t
  with open("outlik_"+method,"w") as fp:
    for g in sorted(list(d)):
      print("%10.6f %12g"%(g,d[g]/dg),file=fp)
  thr=[0.5,0.9,0.95,0.99]
  i=0
  t=0;s=0
  for g in sorted(list(d)):
    t+=d[g]
    s+=d[g]*g
    while i<len(thr) and t>thr[i]:
      print("Method %s: %2.0f%% point at daily logarithmic growth %5.3f = %+5.0f%% per week"%(method,thr[i]*100,g,(exp(g*7)-1)*100))
      i+=1
  print("Method %s: mean      at daily logarithmic growth %5.3f = %+5.0f%% per week"%(method,s,(exp(s*7)-1)*100))
  print()
  
