import sys,pickle,os
from stuff import *
from scipy.stats import norm
import numpy as np
from math import sqrt,floor,log

cachedir="cogukcachedir"
datafile='cog_metadata.csv'
Vnames=["BA.1","BA.1.1","BA.2"]
mindate=Date('2000-01-01')
maxdate=Date('2099-12-31')
mincount=5
conf=0.95
load=1

if len(sys.argv)>1: Vnames=sys.argv[1].split(',')
if len(sys.argv)>2: mindate=Date(sys.argv[2])
if len(sys.argv)>3: maxdate=Date(sys.argv[3])

print("Variants considered:",' '.join(Vnames))
print("Initial date range:",mindate,"-",maxdate)
zconf=norm.ppf((1+conf)/2)
numv=len(Vnames)
cogdate=datetime.datetime.utcfromtimestamp(os.path.getmtime(datafile+'.gz')).strftime('%Y-%m-%d')

fn=os.path.join(cachedir,'_'.join(Vnames)+'__%s_%s_%s'%(mindate,maxdate,cogdate))
if os.path.isfile(fn):
  with open(fn,'rb') as fp:
    data=pickle.load(fp)
else:
  data={}
  for (date,p2,lin) in csvrows(datafile,['sample_date','is_pillar_2','lineage']):
    if lin not in Vnames or len(date)!=10: continue
    #if p2!='Y': continue
    i=Vnames.index(lin)
    if date not in data: data[date]=[0]*numv
    data[date][i]+=1
    #if date<mindate: break
  os.makedirs(cachedir,exist_ok=True)
  with open(fn,'wb') as fp:
    pickle.dump(data,fp)

mindate1=Date('2099-12-31')
maxdate1=Date('2000-01-01')
for date in data:
  if data[date][0]>=mincount and max(data[date][1:])>=mincount:
    mindate1=min(mindate1,Date(date))
    maxdate1=max(maxdate1,Date(date))
mindate=max(mindate,mindate1)
maxdate=min(maxdate,maxdate1)
print("Reduced date range:",mindate,"-",maxdate)

datafn='UK_%s'%('_'.join(Vnames))
VV=[]
visthr=2;ymin=50;ymax=-50
with open(datafn,'w') as fp:
  for date in Daterange(mindate,maxdate+1):
    v=data.get(str(date),[0]*numv)
    VV.append(v)
    print(date,' '.join("%6d"%x for x in v),end='',file=fp)
    for i in range(1,numv):
      a,b=v[0]+1e-30,v[i]+1e-30
      y=log(b/a)
      prec=sqrt(a*b/(a+b))
      print(" %12g %12g"%(y,prec),end='',file=fp)
      if prec>visthr: ymin=min(ymin,y);ymax=max(ymax,y)
    print(file=fp)
print("Written data to",datafn)
VV=np.transpose(VV)

def bestfit(V0,V1):
  # L(a,b) = -(1/2)sum_i w_i(a+bx_i-y_i)^2
  #      c = (a,b); can write L(c)
  # L is quadratic in a,b so
  # dL/dc = dL/dc(0) + (d^2L/dc^2).c = r - M.c, where M and r are as below (known and constant, i.e. independent of a,b).
  # So c*=M^{-1}r and L(x) = L(c*) - (1/2)(x-c*)^t.M.(x-c*)
  # To correct for dependence, we're going to deem the average residual to be equal to 1, which we're going to achieve by rescaling V0, V1.
  # So imagine: V0/=mult, V1/=mult, W/=mult, M/=mult, r/=mult, C*=mult, X, Y, a, b, c unchanged.
  # Then M/mult is the precision (inverse-covariance) matrix = observed Fisher information,
  # and (M/mult)^{-1} is the "observed covariance" matrix, and bottom right of this is est variance of b, the gradient.
  # Effectively our posterior is (a,b) ~ MVN(c,C)
  # We're interested in b (growth) and a/b (essentially the crossover point). Can get a/b by simulation
  # or can get it simply and analytically if we don't worry about the small chance of b going negative.
  V0=np.array(V0)+1e-30
  V1=np.array(V1)+1e-30
  n=len(V0)
  W=V0*V1/(V0+V1)
  X=np.arange(n)
  Y=np.log(V1/V0)
  M=np.array([[sum(W), sum(W*X)], [sum(W*X), sum(W*X*X)]])
  r=np.array([sum(W*Y),sum(W*X*Y)])
  C=np.linalg.inv(M)
  c=C@r
  res=c[0]+c[1]*X-Y
  mult=(W*res*res).sum()/n
  print("Residual multiplier = %.3f"%mult)
  qa=c[1]**2-zconf**2*C[1,1]*mult
  qb=c[0]*c[1]-zconf**2*C[0,1]*mult
  qc=c[0]**2-zconf**2*C[0,0]*mult
  descrim=qb**2-qa*qc
  # lam0=(-qb-sqrt(descrim))/qa
  # lam1=(-qb+sqrt(descrim))/qa
  # from scipy.stats import multivariate_normal as mvn
  # N=100000
  # test=mvn.rvs(mean=c,cov=C,size=N)
  # t=sorted(-test[:,0]/test[:,1])
  # print(t[int(N*(1-conf)/2)],t[int(N*(1+conf)/2)])
  grad=c[1]
  graderr=sqrt(mult*C[1,1])*zconf
  cross=-qb/qa
  crosserr=sqrt(descrim)/qa
  return grad,graderr,cross,crosserr

out=[None]
for i in range(1,numv):
  print()
  grad,graderr,cross,crosserr=bestfit(VV[0],VV[i])
  growthstr=f"Relative growth in {Vnames[i]} vs {Vnames[0]} of {grad:.3f} ({grad-graderr:.3f} - {grad+graderr:.3f}) per day"
  doubstr=f"Doubling of ratio {Vnames[i]}/{Vnames[0]} every {log(2)/grad:.1f} ({log(2)/(grad+graderr):.1f} - {log(2)/(grad-graderr):.1f}) days"
  print(growthstr)
  print(doubstr)
  cr1=int(floor(cross))
  crossstr=f"Est'd %s/%s crossover on %s.%d +/- %.1f days"%(Vnames[i],Vnames[0],mindate+cr1,int((cross-cr1)*10),crosserr)
  print(crossstr)
  out.append((grad,graderr,cross,crosserr,growthstr,doubstr,crossstr))

graphfn=datafn+'.png'
ndates=maxdate-mindate+1
allothers=' and '.join(Vnames[1:])
oneother=' or '.join(Vnames[1:])
number="they are" if numv>2 else "it is"

cmd=f"""
set xdata time
set key left Left reverse
set key spacing 2.5
fmt="%Y-%m-%d"
set timefmt fmt
set format x fmt
set xtics "2020-01-06", 604800
set xtics rotate by 45 right offset 0.5,0
set xtics nomirror
set grid xtics ytics lc rgb "#dddddd" lt 1
set terminal pngcairo font "sans,13" size 1728,1296
set bmargin 5.5;set lmargin 13;set rmargin 13;set tmargin 7.5
set ylabel "log(New {oneother} per day / New {Vnames[0]} per day)"

set output "{graphfn}"
set title "New cases per day in the UK of {allothers} compared with {Vnames[0]}\\nNB: This is the est'd relative growth of {allothers} compared to {Vnames[0]}, not their absolute growth. It indicates how fast {number} taking over from {Vnames[0]}\\nNB2: Growth estimates assume that sequenced cases are representative of infections\\nStats/analysis: https://github.com/alex1770/Covid-19/blob/master/VOCgrowth/uk\\\\_var\\\\_comp.py\\nSource: Sequenced cases from COG-UK {cogdate}"
min(a,b)=(a<b)?a:b
plot [:] [{ymin-0.5}:{ymax+1}]"""

for i in range(1,numv):
  (grad,graderr,cross,crosserr,growthstr,doubstr,crossstr)=out[i]
  cmd+=f"""  "{datafn}" u 1:{numv+2*i}:(min(${numv+2*i+1},20)/{ndates/5}) pt 5 lc {i} ps variable title "log(Daily {Vnames[i]} / Daily {Vnames[0]}); larger blobs indicate more certainty (more samples)", (x/86400-{int(mindate)+cross})*{grad} lc {i} lw 2 w lines title "{growthstr}\\n{doubstr}\\n{crossstr}", """
cmd+=" 0/0 notitle"

po=subprocess.Popen("gnuplot",shell=True,stdin=subprocess.PIPE)
p=po.stdin
p.write(cmd.encode('utf-8'))
p.close()
po.wait()
print()
print("Written graph to",graphfn)
