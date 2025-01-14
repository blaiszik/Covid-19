import sys,os
from stuff import *

c=None
mindate='2020-01-01'
var=None

if len(sys.argv)>1: c=sys.argv[1]
if len(sys.argv)>2: mindate=sys.argv[2]
if len(sys.argv)>3: var=sys.argv[3]

try:
  t0=os.path.getmtime('metadata.tsv')
except FileNotFoundError:
  t0=-1e30

try:
  t1=os.path.getmtime('metadata_sorted.tsv')
except FileNotFoundError:
  t1=-1e30

if t0<0 and t1<0: raise FileNotFoundError("Could not find GISAID files metadata.tsv or metadata_sorted.tsv")
if t1>=t0:
  infile='metadata_sorted.tsv';inputsorted=True
else:
  infile='metadata.tsv';inputsorted=False

print('Using input file',infile,file=sys.stderr)
print("Country/region:",c,file=sys.stderr)
print("mindate:",mindate,file=sys.stderr)
print("Variant:",var,file=sys.stderr)

with open(infile) as fp: cr=csv.reader(fp,delimiter='\t');headings=next(cr)
cw=csv.writer(sys.stdout,delimiter='\t')
cw.writerow(headings)
for (date,loc,lineage,row) in csvrows(infile,['Collection date','Location','Pango lineage',None],sep='\t'):
  if c!=None and loc[:len(c)]!=c: continue
  if len(date)==7: date+='-XX'
  if date<mindate:
    if inputsorted: break
    continue
  if var!=None:
    if lineage!=var:
      if var[-1]!='*': continue
      if (lineage+'.')[:len(var)-1]!=var[:-1]: continue
  cw.writerow(row)
