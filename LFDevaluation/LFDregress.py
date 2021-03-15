import sys,csv,time,calendar
from math import log,sqrt
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

def datetoday(x):
  t=time.strptime(x+'UTC','%Y-%m-%d%Z')
  return calendar.timegm(t)//86400

def daytodate(r):
  t=time.gmtime(r*86400)
  return time.strftime('%Y-%m-%d',t)

# wget 'https://api.coronavirus.data.gov.uk/v2/data?areaType=nation&areaCode=E92000001&metric=newCasesLFDConfirmedPCRBySpecimenDate&metric=newCasesLFDOnlyBySpecimenDate&metric=newLFDTests&metric=newCasesBySpecimenDate&format=csv' -O engcasesbyspecimen.csv
# wget 'https://api.coronavirus.data.gov.uk/v2/data?areaType=overview&metric=newCasesByPublishDate&format=csv' -O casesbypublication.csv

def loadcsv(fn):
  dd={}
  with open(fn,"r") as fp:
    reader=csv.reader(fp)
    headings=[x.strip() for x in next(reader)]
    for row in reader:
      for (name,x) in zip(headings,row):
        x=x.strip()
        if x.isdigit(): x=int(x)
        dd.setdefault(name,[]).append(x)
  return dd

print("Using LFD school numbers from table 6 of https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/968462/tests_conducted_2021_03_11.ods")
dd=loadcsv("LFDschooltests.csv")
#cases=dd["Cases"]

# cc=loadcsv("engcasesbyspecimen.csv")
# datetocases=dict(zip(cc['date'],cc['newCasesBySpecimenDate']))
# print("Using England cases by specimen date")

cc=loadcsv("casesbypublication.csv")
datetocases=dict(zip(cc['date'],cc['newCasesByPublishDate']))
print("Using UK cases by publication date from https://api.coronavirus.data.gov.uk/v2/data?areaType=overview&metric=newCasesByPublishDate&format=csv")
print()

# Work out Poisson denominator. It doesn't affect the optimisation, but it makes the log likelihood output more meaningful
LL0=sum(gammaln(a+1) for a in dd['LFDpos'])

# SLSQP seems to be happier if the variables we are optimising over are of order 1, so use scale factors
scale0=1e4
population=67e6

# Return -log(likelihood)
def err(xx):
  LL=0
  for (a,b,c) in zip(dd['LFDpos'],dd['LFDnum'],cases):
    lam=(xx[0]/scale0+xx[1]*c/population)*b
    LL+=a*log(lam)-lam
  return LL0-LL

# Return second derivative of log(likelihood) wrt xx[0]/scale0 (Fisher information)
def LL2(xx):
  ll2=0
  for (a,b,c) in zip(dd['LFDpos'],dd['LFDnum'],cases):
    ll2+=a/(xx[0]/scale0+xx[1]*c/population)**2
  return ll2

best=(-1e9,)
for offset in range(-2,10):
  cases=[]
  for date in dd["WeekEnding"]:
    day=datetoday(date)
    cases.append(sum(datetocases[daytodate(d)] for d in range(day+offset-6,day+offset+1)))
  if 0:# Sensitivity check, to check that the correlation between LFDpos and cases is not due to LFDpos feeding directly into cases
    for i in range(len(cases)): cases[i]-=dd['LFDpos'][i]
  
  res=minimize(err,[1,1],method="SLSQP",bounds=[(1e-9,scale0),(1e-9,100)],options={"maxiter":1000})
  if not res.success: raise RuntimeError(res.message)
  LL=-res.fun
  fisher=LL2(res.x)
  print("Offset %2d. Log likelihood = %g"%(offset,LL))
  if LL>best[0]: best=(LL,offset,res,fisher,cases)
print()

(LL,offset,res,fisher,cases)=best
print("Best offset %d. Log likelihood = %g"%(offset,LL))
date=dd["WeekEnding"][-1]
day=datetoday(date)-6
print("Offset %d means LFD numbers for week %s - %s are related to national case numbers in the week %s - %s"%(offset,daytodate(day),date,daytodate(day+offset),daytodate(day+offset+6)))
xx=res.x
fpr=xx[0]/scale0*100
error=1.96/sqrt(fisher)*100
print("Best estimate: LFDpos/LFDnum = %.3g + %.3g*(weekly case rate)"%(xx[0]/scale0,xx[1]))
print("               where (weekly case rate) = (number of confirmed cases in a week) / %g"%population)
print("False positive rate estimate: %.2g%% (%.2g%% - %.2g%%)"%(fpr,fpr-error,fpr+error))

with open("graph","w") as fp:
  for (pos,num,ncases) in zip(dd['LFDpos'],dd['LFDnum'],cases):
    print(pos,num,ncases,1.96*sqrt(pos),file=fp)
