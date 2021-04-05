import sys,csv,time,calendar
from math import log,sqrt
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

keephalfterm=True
#maxdate='9999-99-99'
maxdate='2021-03-08'

def datetoday(x):
  t=time.strptime(x+'UTC','%Y-%m-%d%Z')
  return calendar.timegm(t)//86400

def daytodate(r):
  t=time.gmtime(r*86400)
  return time.strftime('%Y-%m-%d',t)

# wget 'https://api.coronavirus.data.gov.uk/v2/data?areaType=nation&areaCode=E92000001&metric=newCasesLFDConfirmedPCRBySpecimenDate&metric=newCasesLFDOnlyBySpecimenDate&metric=newLFDTests&metric=newCasesBySpecimenDate&format=csv' -O engcasesbyspecimen.csv
# wget 'https://api.coronavirus.data.gov.uk/v2/data?areaType=overview&metric=newCasesByPublishDate&format=csv' -O casesbypublication.csv
# wget 'https://api.coronavirus.data.gov.uk/v2/data?areaType=nation&areaName=England&metric=maleCases&metric=femaleCases&format=csv' -O casesbyage.csv

def loadcsv(fn,keephalfterm=True,maxdate='9999-99-99'):
  dd={}
  with open(fn,"r") as fp:
    reader=csv.reader(fp)
    headings=[x.strip() for x in next(reader)]
    for row in reader:
      if (keephalfterm or row[0]!='2021-02-17') and row[0]<=maxdate:
        for (name,x) in zip(headings,row):
          x=x.strip()
          if x.isdigit(): x=int(x)
          dd.setdefault(name,[]).append(x)
  return dd

print("Using LFD school numbers from table 7 of https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/973128/tests_conducted_2021_03_25.ods")
if keephalfterm: print("Keeping half term 14-20 February")
else: print("Discarding half term 14-20 February")
dd=loadcsv("LFDschooltests.csv",keephalfterm=keephalfterm,maxdate=maxdate)
dd['LFDnum']=list(map(sum,zip(dd['LFDpos'],dd['LFDneg'])))# Denominator = positive tests + negative tests (ignore unknown/void tests)

# cc=loadcsv("engcasesbyspecimen.csv")
# datetocases=dict(zip(cc['date'],cc['newCasesBySpecimenDate']))
# print("Using England cases by specimen date")

# cc=loadcsv("casesbypublication.csv")
# datetocases=dict(zip(cc['date'],cc['newCasesByPublishDate']))
# print("Using UK cases by publication date from https://api.coronavirus.data.gov.uk/v2/data?areaType=overview&metric=newCasesByPublishDate&format=csv")
# print()

cc=loadcsv("casesbyage.csv")
cumdatetocases={}
for (date,metric,age,value) in zip(cc['date'],cc['metric'],cc['age'],cc['value']):
  #if age=="10_to_14" or age=="15_to_19": cumdatetocases[date]=cumdatetocases.get(date,0)+value
  if age=="15_to_19": cumdatetocases[date]=cumdatetocases.get(date,0)+value
  #if age=="5_to_9": cumdatetocases[date]=cumdatetocases.get(date,0)-value*.5
print("Using England cases by age from https://api.coronavirus.data.gov.uk/v2/data?areaType=nation&areaName=England&metric=maleCases&metric=femaleCases&format=csv")
print()

# Work out Poisson denominator. It doesn't affect the optimisation, but it makes the log likelihood output more meaningful
LL0=sum(gammaln(a+1) for a in dd['LFDpos'])

# SLSQP seems to be happier if the variables we are optimising over are of order 1, so use scale factors
scale0=1e4
population=6.3e6# Estimated population of age 10-19 in England

# Return -log(likelihood)
def err(xx):
  LL=0
  for (a,b,c) in zip(dd['LFDpos'],dd['LFDnum'],cases):
    lam=(xx[0]/scale0+xx[1]*c/population)*b
    LL+=a*log(lam)-lam
  return LL0-LL

# Return negative second derivative of log(likelihood) wrt xx[0]/scale0 (observed Fisher information)
def LL2(xx):
  ll2=0
  for (a,b,c) in zip(dd['LFDpos'],dd['LFDnum'],cases):
    ll2+=a/(xx[0]/scale0+xx[1]*c/population)**2
  return ll2

best=(-1e9,)
for offset in range(0,5):# -15,7):
  cases=[]
  for date in dd["WeekEnding"]:
    day=datetoday(date)
    #cases.append(sum(datetocases[daytodate(d)] for d in range(day+offset-6,day+offset+1)))
    cases.append(cumdatetocases[daytodate(day+offset)]-cumdatetocases[daytodate(day+offset-7)])
  #cases=cases[1:]+[cases[-1]*0.95]#alter
  if 0:# Sensitivity check, to check that the correlation between LFDpos and cases is not due to LFDpos feeding directly into cases, or possibly a correction term
    for i in range(len(cases)): cases[i]-=dd['LFDpos'][i]*0.3
  
  res=minimize(err,[1,1],method="SLSQP",bounds=[(1e-9,scale0),(1e-9,100)],options={"maxiter":1000})
  if not res.success: raise RuntimeError(res.message)
  LL=-res.fun
  xx=res.x
  fisher=LL2(xx)
  print("Offset %3d. Log likelihood = %8.3f. al = %6.4f%% . be = %8.3f"%((offset,LL,xx[0]/scale0*100,xx[1])))
  if 1:
    for (a,b,c,w) in zip(dd['LFDpos'],dd['LFDnum'],cases,dd['WeekEnding']):
      lam=(xx[0]/scale0+xx[1]*c/population)*b
      print("   w/e %s %8.3f  %6d"%(w,a*log(lam)-lam-gammaln(a+1),c))
    print()
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