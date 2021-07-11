import time,calendar,os,json,sys,datetime
from stuff import *

# Go back this number of days
nprev=50

# Convert (eg) string ages '15_19', '15_to_19', '60+' to (15,20), (15,20), (60,150) respectively
def parseage(x):
  if x[-1]=='+': return (int(x[:-1]),150)
  x=x.replace('_to_','_')# cater for 65_to_69 and 65_69 formats
  aa=[int(y) for y in x.split("_")]
  return (aa[0],aa[1]+1)

now=max(os.listdir('apidata'))
casedata=[]
for day in range(datetoday(now)-nprev,datetoday(now)+1):
  dt=daytodate(day)
  with open('apidata/'+dt,'r') as fp: td=json.load(fp)
  d={}
  for x in td[-1]:
    if x=='date': assert td[-1][x]==dt
    else: d[parseage(x)]=td[-1][x]
  casedata.append(d)

ages=sorted(list(casedata[-1]))

newcases=[]
dates=[]
n=len(casedata)
for i in range(1,n):
  dates.append(daytodate(datetoday(now)+i-n+1))
  newcases.append({})
  for a in ages:
    newcases[-1][a]=casedata[i][a]-casedata[i-1][a]

agestr="     Age:"+'   '.join("%3d"%a[0] for a in ages)

print(agestr)
for i in range(n-1):
  print(dates[i],end=' ')
  t=sum(newcases[i].values())
  for a in ages:
    print("%5d"%(newcases[i][a]+.5),end=' ')
  print("= %d"%(t+.5))
print()

print(agestr)
for i in range(n-1):
  print(dates[i],end=' ')
  t=sum(newcases[i].values())
  for a in ages:
    print("%5d"%(newcases[i][a]/t*1000+.5),end=' ')
  print("= 1000")
print()

print(agestr)
ave=3
for i in range(7+ave-1,n-1):
  print(dates[i],end=' ')
  for a in ages:
    A,B=sum(newcases[i-j][a] for j in range(ave)),sum(newcases[i-7-j][a] for j in range(ave))
    tA,tB=sum(sum(newcases[i-j].values()) for j in range(ave)),sum(sum(newcases[i-7-j].values()) for j in range(ave))
    if B>0:
      print("%5.2f"%(A/B),end=' ')
    else:
      print(" ????",end=' ')
  print(": %5.2f"%(tA/tB))
print(agestr)
print()