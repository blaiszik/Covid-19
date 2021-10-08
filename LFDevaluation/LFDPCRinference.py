import os,json
from scipy.special import gammaln
from math import log
import numpy as np

np.set_printoptions(precision=3,suppress=True)
np.set_printoptions(edgeitems=30, linewidth=100000)

# Try to reverse-engineer PCR-retest-negatives using the assumption that the LFD+ves and PCR-retest+ves follow newLFDTests
# in a uniform way

# https://api.coronavirus.data.gov.uk/v2/data?areaType=nation&areaName=England&metric=newCasesLFDConfirmedPCRBySpecimenDate&metric=newCasesLFDOnlyBySpecimenDate&metric=newCasesPCROnlyBySpecimenDate&metric=newLFDTests&metric=newCasesBySpecimenDate&format=csv&release=2021-04-18
# https://docs.google.com/spreadsheets/d/1yItIPgFTItAM29BZ6D8unah53EkOWMkiCW-T5TcGePI/edit#gid=0

lfddir='../apidata_lfd'

#mindate='2021-04-01'
mindate='2021-08-16'

dates=sorted(x for x in os.listdir(lfddir) if x[:2]=='20' and x>=mindate)

dd={}
for fn in dates:
  with open(os.path.join(lfddir,fn),'r') as fp:
    dd[fn]={y['date']: y for y in json.load(fp) if y['date']>=mindate}

# dd[adjustedpublishdate][historicaldate]={historical data}

now=dates[-1]

def lbin(n,r): return gammaln(n+1)-gammaln(r+1)-gammaln(n-r+1)

if 0:
  for specdate in dates:
    (o0,c0)=dd[now][specdate]['newCasesLFDOnlyBySpecimenDate'], dd[now][specdate]['newCasesLFDConfirmedPCRBySpecimenDate']
    for repdate in dates:
      if repdate>=specdate:
        (t,o,c)=dd[repdate][specdate]['newLFDTests'], dd[repdate][specdate]['newCasesLFDOnlyBySpecimenDate'], dd[repdate][specdate]['newCasesLFDConfirmedPCRBySpecimenDate']
        print(specdate,repdate," %7d %4d %4d %4d  %5.3f"%(t,o,c,o+c,(o+c)/t*1000))
    print()
  print()
  
if 0:
  for specdate in dates:
    nn=[0]+[dd[repdate][specdate]['newLFDTests'] for repdate in dates if repdate>=specdate]
    oo=[0]+[dd[repdate][specdate]['newCasesLFDOnlyBySpecimenDate'] for repdate in dates if repdate>=specdate]
    cc=[0]+[dd[repdate][specdate]['newCasesLFDConfirmedPCRBySpecimenDate'] for repdate in dates if repdate>=specdate]
    n=len(oo)
    for i in range(1,n):
      if cc[i]<cc[i-1] or nn[i]==nn[i-1]:
        nn=nn[:i]
        oo=oo[:i]
        cc=cc[:i]
        n=i;break
    print(nn)
    print(oo)
    print(cc)
    # tr=total removed for PCR testing
    for tr in range(cc[-1],cc[-1]+10):
      rr=[int(c*tr/cc[-1]+.5) for c in cc]
      ll=[o+r for (o,r) in zip(oo,rr)]
      if not all(ll[i]<=ll[i+1] for i in range(n-1)): continue
      al=ll[-1]/nn[-1]
      p=cc[-1]/rr[-1]
      LL=0
      for i in range(n-1):
        dn=nn[i+1]-nn[i]
        dl=ll[i+1]-ll[i]
        dc=cc[i+1]-cc[i]
        dr=rr[i+1]-rr[i]
        LL+=-al*dn+dl*log(al*dn)-gammaln(dl+1)
        LL+=lbin(dr,dc)+(dc*log(p) if dc>0 else 0)+((dr-dc)*log(1-p) if dr-dc>0 else 0)
      print(tr,al,p,LL)
    print()
    pio

if 1:
  nhist=3
  for specdate in dates[:-3]:
  #for specdate in ['2021-10-01']:
    nn=np.array([dd[repdate][specdate]['newLFDTests'] for repdate in dates if repdate>=specdate])
    oo=np.array([dd[repdate][specdate]['newCasesLFDOnlyBySpecimenDate'] for repdate in dates if repdate>=specdate])
    cc=np.array([dd[repdate][specdate]['newCasesLFDConfirmedPCRBySpecimenDate'] for repdate in dates if repdate>=specdate])
    # Try to find (e.g., nhist=3) best a,b,c,lam s.t. a*nn+b*(0,nn[:-1])+c*(0,0,nn[:-2]) is close to oo+lam*cc
    # lam should be 1/PPV
    if specdate=='2021-10-01': nn=nn[1:];cc=cc[1:];oo=oo[1:]# Workaround presumed error in LFD test count on 2021-10-01
    nnl=[]
    for i in range(nhist):
      nnl.append(np.concatenate([[0]*i,nn[:len(nn)-i]]))
    nnl.append(-cc)
    nnn=np.transpose(np.array(nnl,dtype=float))
    condition=100
    nnn[:,:nhist]=nnn[:,:nhist]/condition
    rr=np.linalg.lstsq(nnn,oo)
    r=rr[0];r[:nhist]=r[:nhist]/condition
    
    print(specdate,"%5.3f %6.1f"%(1/r[nhist],cc[-1]*(r[nhist]-1)),end='')
    ccn=cc/nn;oon=oo/nn
    for i in range(min(len(nn)-1,5)):
      ppv=(ccn[-1]-ccn[i])/(oon[i]-oon[-1])
      print(" %5.3f"%ppv,end='')
    print(" ",rr[1],r[:nhist]*1000,r[1:nhist]/r[0]*100)
