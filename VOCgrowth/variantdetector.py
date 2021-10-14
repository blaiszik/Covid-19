import sys
from stuff import *
import numpy as np
from math import log,sqrt

mindate='2021-09-01'
maxdate='9999-12-31'

minday=datetoday(mindate)

fp=sys.stdin
#fp=open('cog_metadata.csv','r')#alter
mutcounts={}
daycounts={}
mutdaycounts={}
for (dt,lin,var,mut) in csvrows_it(fp,['sample_date','lineage','scorpio_call','mutations']):
  if dt>maxdate: continue
  day=datetoday(dt)
  #if day<minday-30: break# Can't use this cutoff in a simple way because of lots of erroneous dates
  if day<minday: continue
  daycounts[day]=daycounts.get(day,0)+1
  muts=mut.split('|')
  for mut in muts:
    mutcounts[mut]=mutcounts.get(mut,0)+1
    if mut not in mutdaycounts: mutdaycounts[mut]={}
    mutdaycounts[mut][day]=mutdaycounts[mut].get(day,0)+1
    
growth={}
for mut in mutcounts:
  if mutcounts[mut]<100: continue
  if mut!='synSNP:C27143T': continue
  m=np.zeros([2,2])
  r=np.zeros(2)
  for day in mutdaycounts[mut]:
    x=day-minday
    vm=mutdaycounts[mut][day]
    v0=daycounts[day]
    if v0>0 and vm>0:
      y=log(vm/v0)
      w=1/(1/v0+1/vm)
      m[0,0]+=w
      m[0,1]+=w*x
      m[1,0]+=w*x
      m[1,1]+=w*x*x
      r[0]+=w*y
      r[1]+=w*x*y
  mi=np.linalg.pinv(m)
  c=np.linalg.solve(m,r)
  cv=[mi[0,0],mi[1,1]]# This should be the variances of c[0],c[1]
  #print(c[1],sqrt(cv[1]))
  #print("Continuous growth rate = %.4f/day"%(c[1]))
  #print("Crossover on",daytodate(datetoday(dt[0])+int(-c[0]/c[1]+.5)))
  #print("%-20s  %7.4f   %s"%(mut,c[1],daytodate(minday+int(-c[0]/c[1]+.5))))
  growth[mut]=c[1],sqrt(cv[1])

sd=6
l=list(growth)
l.sort(key=lambda x:-(growth[x][0]-sd*growth[x][1]))
nm=0
for mut in l:
  gr=growth[mut]
  (g,gl,gh)=(gr[0],gr[0]-sd*gr[1],gr[0]+sd*gr[1])
  if gl<0: break
  print("%-20s  %6.3f (%6.3f - %6.3f) %8d"%(mut,g,gl,gh,mutcounts[mut]))
  nm+=1

nm=min(nm,10)
print()
days=set()
for mut in l[:nm]: days.update(mutdaycounts[mut])
print("                All",end='')
for mut in l[:nm]: print(" %20s"%mut,end='')
print()
for day in sorted(days):
  v0=daycounts[day]
  print(daytodate(day),"  %6d"%v0,end='')
  for mut in l[:nm]:
    vm=mutdaycounts[mut].get(day,0)
    if vm>0 and v0>0: print("         %6.3f"%(log(vm/v0)),end='')
    else: print("              -",end='')
    print(" %5d"%vm,end='')
  print()
