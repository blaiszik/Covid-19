# Trying to replicate rcASMR calculation from bottom of https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/deaths/articles/comparisonsofallcausemortalitybetweeneuropeancountriesandregions/januarytojune2020
# Simplified version not handling week 53, leap years, or population projections to 2019, 2020 properly

# Population source: https://ec.europa.eu/eurostat/web/products-datasets/product?code=urt_pjangrp3 giving urt_pjangrp3.tsv
# (https://ec.europa.eu/eurostat/en/web/products-datasets/-/demo_pjangroup goes back further but doesn't have a 85-89 age group)
# For population projections (not currently used), can use
# EU: https://ec.europa.eu/eurostat/web/products-datasets/product?code=proj_19np
# UK: (uses midpoints of years): https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections/datasets/tablea21principalprojectionukpopulationinagegroups
#     or                         https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections/datasets/tablel21oldagestructurevariantukpopulationinagegroups
# but for simplicity not using these to start with (instead linearly interpolate off the end of the actuals)
# Going to be simpler to switch to using:
# https://population.un.org/wpp/Download/Files/1_Indicators%20(Standard)/EXCEL_FILES/1_Population/WPP2019_POP_F15_1_ANNUAL_POPULATION_BY_AGE_BOTH_SEXES.xlsx
# from https://population.un.org/wpp/Download/Standard/Population/
# (though I think the linear interpolation off the end isn't actually that bad an estimate)

# Mortality source: https://data.europa.eu/euodp/en/data/dataset/QrtzdXsI5w26vnr54SIzpQ giving demo_r_mwk_05.tsv
# Explanation: https://ec.europa.eu/eurostat/cache/metadata/en/demomwk_esms.htm
# Ignoring week 99, which appears to contain no data in the examples I've looked at.
# The week number (1-53) is the ISO 8601 week: weeks run Mon-Sun and are assigned to the year in which Thursday falls.
# For the moment just ignore week 53 and (slightly wrongly) pretend that week i is aligned at the same point in the year for any year.

# Following https://www.actuaries.org.uk/system/files/field/document/CMI%20WP111%20v02%202019-04-25-%20Regular%20monitoring%20of%20England%20%20Wales%20population%20mortality.pdf
# and https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/deaths/articles/comparisonsofallcausemortalitybetweeneuropeancountriesandregions/januarytojune2020
# The former (actuaries) is more detailed, but using the notation of the latter (ONS), i.e., ASMR rather than SMR; csASMR etc.

# "Standard" day and week refer to idealised years that always have exactly 365 days and always start at the same week alignment (week 0 is 1-7 Jan).

import os,csv,sys,time,calendar,datetime
from collections import defaultdict
from subprocess import Popen,PIPE

# See https://ec.europa.eu/eurostat/cache/metadata/en/demomwk_esms.htm for country codes
#countrycode='UK';countryname='UK'
countrycode='FR';countryname='France'
#countrycode='ES';countryname='Spain'
meanyears=range(2015,2020)
targetyear=2020
assert targetyear not in meanyears and 2020 not in meanyears
update=False

print("Country:",countryname)
print("meanyears:",list(meanyears))
print("targetyear:",targetyear)
allyears=list(meanyears)+[targetyear]
minyear=min(allyears)

# YYYY-MM-DD -> day number
def datetoday(x):
  t=time.strptime(x+'UTC','%Y-%m-%d%Z')
  return calendar.timegm(t)//86400

def daytodate(r):
  t=time.gmtime(r*86400)
  return time.strftime('%Y-%m-%d',t)

deathsfn='demo_r_mwk_05.tsv'
if update or not os.path.isfile(deathsfn):
  if os.path.exists(deathsfn): os.remove(deathsfn)
  Popen("wget https://ec.europa.eu/eurostat/estat-navtree-portlet-prod/BulkDownloadListing?file=data/demo_r_mwk_05.tsv.gz -O -|gunzip -c > %s"%deathsfn,shell=True).wait()

popfn='urt_pjangrp3.tsv'
if update or not os.path.isfile(popfn):
  if os.path.exists(popfn): os.remove(popfn)
  Popen("wget https://ec.europa.eu/eurostat/estat-navtree-portlet-prod/BulkDownloadListing?file=data/urt_pjangrp3.tsv.gz -O -|gunzip -c > %s"%popfn,shell=True).wait()

ages="Y_LT5, Y5-9, Y10-14, Y15-19, Y20-24, Y25-29, Y30-34, Y35-39, Y40-44, Y45-49, Y50-54, Y55-59, Y60-64, Y65-69, Y70-74, Y75-79, Y80-84, Y85-89, Y_GE90".split(", ")
# (Also TOTAL, UNK)

# Convert ISO 8601 year,week to weighted list of year,day
# Resample leap years to range(365)
# (Not using datetime.date.fromisocalendar to avoid creating a dependancy on too recent a python version)
def isoweektodates(y,w):
  day=datetime.date.toordinal(datetime.date(y,1,1))+7*(w-2)
  while 1:
    dt=datetime.date.fromordinal(day)
    iso=datetime.date.isocalendar(dt)
    if iso[0]==y and iso[1]==w: break
    day+=1
  year2wd=defaultdict(int)# working days for each year present in week
  year2days=defaultdict(int)# total days for each year present in week
  for d in range(7):
    dt=datetime.date.fromordinal(day+d)
    year2days[dt.year]+=1
    # Only care about determining working days when crossing year boundary, in which case the week lies between 29 Dec and 6 Jan, inclusive.
    # Assume the only public holiday in this range is 1st Jan, or 2nd or 3rd Jan if 1st Jan falls on a Sunday, Saturday respectively.
    # Of course getting this wrong is only going to make a microscopic difference overall.
    if dt.weekday()>=6: holiday=True
    elif dt.month>1 or dt.day>3: holiday=False
    elif dt.day==1: holiday=True
    else: holiday=(dt.weekday()==0)
    if not holiday: year2wd[dt.year]+=1
  twd=sum(year2wd.values())
  l=defaultdict(float)
  for i in range(7):
    dt=datetime.date.fromordinal(day+i)
    wt=year2wd[dt.year]/twd/year2days[dt.year]
    day0=datetime.date.toordinal(datetime.date(dt.year,1,1))
    (y,d)=dt.year,day+i-day0
    # Resample leap year to range(365)
    if y%4:
      l[y,d]+=wt
    else:
      if d>0: l[y,d-1]+=d/366*wt
      if d<365: l[y,d]+=(365-d)/366*wt
  return [(y,d,l[y,d]) for (y,d) in l]

wd={age:{} for age in ages}
with open(deathsfn,'r') as fp:
  r=csv.reader(fp,delimiter='\t')
  first=True
  ok={age:{y:set() for y in allyears} for age in ages}
  for row in r:
    if first:
      assert row[0][:16]=='age,sex,unit,geo'
      # row[1:] is a list of strings like '2012W39 '; weeks are 01, 02, ..., 52, 53, 99.
      # Construct datelist and indexes
      dates=[]
      for i in range(len(row)-1,0,-1):
        y0,w0=map(int,row[i].strip().split('W'))
        if w0<=53:
          for (y,d,wt) in isoweektodates(y0,w0):
            if y in allyears:
              dates.append((i,y,d,wt))
      first=False
    else:
      (age,sex,unit,geo)=row[0].split(',')
      if sex=='T' and geo==countrycode and age[0]=='Y':
        for (i,y,d,wt) in dates:
          x=row[i].strip()
          if x[-1]=='p' or x[-1]=='e': x=x[:-1].strip()
          if x!=':':
            wd[age][y,d]=wd[age].get((y,d),0)+wt*float(x)
            ok[age][y].add(d)
  for age in ages:
    for y in meanyears:
      if len(ok[age][y])!=365: print("Missing data in year %d at age %s"%(y,age),file=sys.stderr);sys.exit(1)

laststdday=min(len(ok[age][targetyear]) for age in ages)
numstdweeks=laststdday//7# last+1 centered standardised week

def stddaytostring(y,d0):
  d=int(d0*(365+(y%4==0))/365+.5)
  return datetime.date.fromordinal(datetime.date.toordinal(datetime.date(y,1,1))+d).strftime("%Y-%m-%d")

def int2(s):
  if s[-2:]==' p': return int(s[:-2])
  return int(s)

pp={}
with open(popfn,'r') as fp:
  r=csv.reader(fp,delimiter='\t')
  first=True
  for row in r:
    if first:
      assert row[0]=='unit,sex,age,terrtypo,geo\\time'
      # Expecting row[1:] = 2019, 2018, 2017, 2016, 2015, 2014
      nyears_pop=len(row)-1
      minyear_pop=int(row[-1])
      # Something
      first=False
    else:
      (unit,sex,age,terr,geo)=row[0].split(',')
      # TOTAL territory not available, so construct it from URB+RUR+INT
      if sex=='T' and geo==countrycode and age[0]=='Y'and (terr=='URB' or terr=='RUR' or terr=='INT'):
        if age not in pp: pp[age]=[0]*nyears_pop
        assert len(row)==nyears_pop+1
        assert ': z' not in row# Insist all data present
        for i in range(nyears_pop): pp[age][i]+=int2(row[nyears_pop-i])

# Number of deaths at age group a, year y0, in a 1 week interval centered around day d0 (0-364)
def D(y0,d0,a):
  t=0
  for x in range(y0*365+d0-3,y0*365+d0+4):
    y=x//365;d=x%365
    t+=wd[a][y,d]
  return t

# Estimated population at age group a, year y, day d (0-364)
def E(y,d,a):
  yy=y-minyear_pop
  if yy<nyears_pop-1: y0=yy;y1=yy+1
  else: y0=nyears_pop-2;y1=nyears_pop-1
  yf=yy+d/365
  return (y1-yf)*pp[a][y0]+(yf-y0)*pp[a][y1]

# European Standard Population 2013
# https://webarchive.nationalarchives.gov.uk/20160106020035/http://www.ons.gov.uk/ons/guide-method/user-guidance/health-and-life-events/revised-european-standard-population-2013--2013-esp-/index.html
# ESP[i] = std pop for age group [5i,5(i+1)), except last one is [90,infinty)
ESP=[5000, 5500, 5500, 5500, 6000, 6000, 6500, 7000, 7000, 7000, 7000, 6500, 6000, 5500, 5000, 4000, 2500, 1500, 1000]
nages=len(ESP)
    
def age_s2i(s):
  assert s[0]=='Y'
  if s=='Y_LT5': return 0
  i=0
  while i<len(s) and not s[i].isdigit(): i+=1
  j=i
  while j<len(s) and s[j].isdigit(): j+=1
  return int(s[i:j])//5

def age_i2s(i):
  if i==0: return 'Y_LT5'
  if i==nages-1: return 'Y_GE%d'%(5*i)
  return 'Y%d-%d'%(5*i,5*i+4)

# Print populations by age
if 1:
  print()
  print("                "+"        ".join("%4d"%y for y in allyears))
  s={y:0 for y in allyears}
  for a in range(nages): 
    aa=age_i2s(a)
    print("%8s"%aa,end="")
    for y in allyears: n=E(y,0.5,aa);s[y]+=n;print("   %9d"%n,end="")
    print()
  print("   TOTAL   ",end="")
  print("   ".join("%9d"%s[y] for y in allyears))
  print()

ASMR={y:[] for y in allyears}#      ASMR[y][w] = ASMR at year y, standardised week w (0-51)
cASMR={y:[0] for y in allyears}# cASMR[y][w+1] = cASMR at year y, standardised week w (0-51)
STDPOP=ESP
#STDPOP=[E(2020,3+(numstdweeks-1)*7,age_i2s(a)) for a in range(nages)]
for y in allyears:
  numw=numstdweeks if y==targetyear else 52
  for w in range(numw):
    d=3+w*7
    t=0
    for a in range(nages):
      aa=age_i2s(a)
      t+=D(y,d,aa)/E(y,d,aa)*STDPOP[a]
    ASMR[y].append(t/sum(STDPOP))
    cASMR[y].append(cASMR[y][-1]+ASMR[y][-1])

ASMR_bar=[]
for w in range(52):
  t=0
  for y in meanyears: t+=ASMR[y][w]
  ASMR_bar.append(t/len(meanyears))

cASMR_bar=[]
for w in range(53):
  t=0
  for y in meanyears: t+=cASMR[y][w]
  cASMR_bar.append(t/len(meanyears))

rcASMR=[]
for w in range(numstdweeks+1):
  rcASMR.append((cASMR[targetyear][w]-cASMR_bar[w])/cASMR_bar[52])

dASMR=[]
for w in range(numstdweeks):
  dASMR.append(ASMR[targetyear][w]-ASMR_bar[w])

# Use this to cater for earlier versions of Python whose Popen()s don't have the 'encoding' keyword
def write(*s): p.write((' '.join(map(str,s))+'\n').encode('utf-8'))

fn=countryname+'_rcASMR.png'
po=Popen("gnuplot",shell=True,stdin=PIPE);p=po.stdin
write('set terminal pngcairo font "sans,13" size 1920,1280')
write('set bmargin 5;set lmargin 15;set rmargin 15;set tmargin 5')
write('set output "%s"'%fn)
write('set key left')
#write('set logscale y')
title="Mortality in %s for %d"%(countryname,targetyear)
title+=' compared with %d-year average'%len(meanyears)+' for corresponding week of year, using rcASMR measure\\n'
title+='Last date: %s. '%stddaytostring(targetyear,laststdday)
title+='Sources: Eurostat urt\\\_pjangrp3 and demo\\\_r\\\_mwk\\\_05'
write('set title "%s"'%title)
write('set grid xtics lc rgb "#e0e0e0" lt 1')
write('set grid ytics lc rgb "#e0e0e0" lt 1')
write('set xtics nomirror')
write('set y2tics mirror')
write('set xtics rotate by 45 right offset 0.5,0')
write('set xdata time')
write('set format x "%Y-%m"')
write('set timefmt "%Y-%m-%d"')
write('plot "-" using 1:2 w lines title "rcASMR"')
for w in range(numstdweeks): write(stddaytostring(targetyear,3+w*7),dASMR[w]*sum(STDPOP))
#for w in range(numstdweeks+1): write(stddaytostring(targetyear,w*7),rcASMR[w]*100)
write("e")
p.close()
po.wait()
print("Written %s"%fn)
