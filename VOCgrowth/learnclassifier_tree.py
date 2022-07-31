#!/usr/bin/pypy3

from __future__ import print_function,division
# ^ To enable use of pypy when pypy3 isn't available

import sys,os,argparse
from stuff import *
from math import log
from variantaliases import aliases

parser=argparse.ArgumentParser()
parser.add_argument('-b', '--maxbad',      type=float, default=0.05, help="Maximum proportion of Ns allowed")
parser.add_argument('-f', '--mindate',     default="2019-01-01",     help="Min sample date of sequence")
parser.add_argument('-g', '--gisaid',      action="store_true",      help="Use GISAID data instead of COG-UK data")
parser.add_argument('-t', '--maxdate',     default="9999-12-31",     help="Max sample date of sequence")
parser.add_argument('-m', '--mincount',    type=int, default=50,     help="Min count of mutation: only consider mutations which have occurred at least this many times")
parser.add_argument('-M', '--maxleaves',   type=int, default=50,     help="Maximum number of leaves in the tree")
parser.add_argument('-l', '--lineages',                              help="Comma-separated list of lineages to classify (takes precedence over --numtop)")
parser.add_argument('-n', '--numtoplin',   type=int, default=5,      help="Classify the most prevalent 'n' lineages (alternative to --lineages)")
parser.add_argument('-p', '--printtree',   type=int, default=20,     help="Print decision tree with this many leaves")
parser.add_argument('-s', '--synperm',     type=int, default=1,      help="[Only applies to COG-UK] 0 = disallow all mutations that COG-UK designates as synSNPs, 1 = allow synSNPs that are non-synonymous in some overlapping and functional ORF (e.g., A28330G), 2 = allow all synSNPs")
args=parser.parse_args()

if args.gisaid:
  infile='metadata_sorted.tsv';inputsorted=True
else:
  infile='cog_metadata_sorted.csv';inputsorted=True

def prparams(prefix="",file=sys.stdout):
  print(prefix+"Command line:",' '.join(sys.argv),file=file)
  print(prefix+"Using input file:",infile,file=file)
  print(prefix+"From:",args.mindate,file=file)
  print(prefix+"To:",args.maxdate,file=file)
  print(prefix+"Mincount:",args.mincount,file=file)
  print(prefix+"Maxleaves:",args.maxleaves,file=file)
  print(prefix+"Database:","GISAID" if args.gisaid else "COG-UK",file=file)
  print(prefix+"synSNP permissiveness:",args.synperm,file=file)
  print(prefix+"Max N-content:",args.maxbad,file=file)
  print(prefix+"Number of leaves in decision tree:",args.printtree,file=file)

prparams()
print()

# List of overlapping ORFs for which there is evidence that they encode
# https://www.sciencedirect.com/science/article/pii/S0042682221000532
# https://virological.org/t/sars-cov-2-dont-ignore-non-canonical-genes/740/2
# 
accessorygenes=set(range(21744,21861)).union(range(25457,25580)).union(range(28284,28575))
def oksyn(m,perm):
  if args.gisaid or perm==2 or m[:6]!="synSNP": return True
  if perm==0: return False
  loc=int(m[8:-1])
  return loc in accessorygenes

ecache={}
def expandlin(lin):
  if lin in ecache: return ecache[lin]
  for (short,long) in aliases:
    s=len(short)
    if lin[:s+1]==short+".": ecache[lin]=long+lin[s:];return ecache[lin]
  ecache[lin]=lin
  return lin

ccache={}
def contractlin(lin):
  if lin in ccache: return ccache[lin]
  lin=expandlin(lin)
  for (short,long) in aliases:
    l=len(long)
    if lin[:l+1]==long+".": ccache[lin]=short+lin[l:];return ccache[lin]
  ccache[lin]=lin
  return lin

def mutationlist(mutations):
  if args.gisaid: return mutations[1:-1].split(',')
  else: return mutations.split('|')

print("Reading sequence metadata")
sys.stdout.flush()
allm={}
ml=[]
numl={}
if args.gisaid: keys=["Collection date","Pango lineage","AA Substitutions","N-Content"];sep='\t'
else: keys=["sample_date","lineage","mutations","ambiguities"];sep=','
t0=t1=0
for (date,lineage,mutations,Ncontent) in csvrows(infile,keys,sep=sep):
  if len(date)<10: continue
  if date>args.maxdate: continue
  if date<args.mindate:
    if inputsorted: break
    continue
  if lineage=="" or lineage=="Unassigned": continue
  if args.gisaid:
    if Ncontent!="": bad=float(Ncontent)
    else: bad=0
  else:
    t=0
    for x in Ncontent.split('|'):
      y=x.split('-')
      if len(y)==1: t+=1
      else: t+=int(y[1])-int(y[0])+1
    bad=t/29903
  t0+=1
  if bad>args.maxbad: t1+=1;continue
  for m in mutationlist(mutations): allm[m]=allm.get(m,0)+1
  ml.append((lineage,mutations))
  numl[lineage]=numl.get(lineage,0)+1

print("Found",len(ml),"relevant entries since",args.mindate)
print("Discarded",t1,"from",t0,"(%.1f%%) due to bad coverage"%(t1/t0*100))
okm=set(m for m in allm if m!="" and allm[m]>=args.mincount and oksyn(m,args.synperm))
print("Found",len(allm),"mutations, of which",len(okm),("pass synSNP permissiveness %d and"%args.synperm if not args.gisaid else ""),"have occurred at least",args.mincount,"times")

if args.lineages==None:
  lineages=list(set(lineage for (lineage,mutations) in ml))
  lineages.sort(key=lambda l: -numl[l])
  lineages=lineages[:args.numtoplin]
else:
  lineages=args.lineages.split(',')
print("Classifying lineages:",lineages)
sys.stdout.flush()
# Wildcard ending is replaced with '.'. It's a match if it's equal to a prefix of (database lineage)+'.'
# Note that BA.5* will match BA.5.1 and BA.5 but not BA.53
#           BA.5.* will match BA.5.1 but not BA.5 or BA.53
targlinsexact=[]
targlinsprefix=[]
for lin in lineages:
  if lin[-2:]=='.*': exact="-";prefix=lin[:-1]
  elif lin[-1]=='*': exact=lin[:-1];prefix=lin[:-1]+'.'
  else: exact=lin;prefix="-"
  targlinsexact.append(expandlin(exact))
  targlinsprefix.append(expandlin(prefix))
print()

mml=[]
for (lineage,mutations) in ml:
  dblin=expandlin(lineage)
  for i in range(len(lineages)):
    exact=targlinsexact[i]
    prefix=targlinsprefix[i]
    if dblin==exact or (dblin+'.')[:len(prefix)]==prefix: ind=i;break
  else: i=len(lineages)
  #print("Assigning",lineage,"to",lineages[i] if i<len(lineages) else "Other")
  mml.append((i,set(mutationlist(mutations)).intersection(okm)))
lineages.append("Others")

def getstats(indexlist):
  nl=len(lineages)
  count=[0]*nl
  for i in indexlist:
    count[mml[i][0]]+=1
  s=float(sum(count))
  ent=0
  for x in count:
    if x>0: ent+=x*log(x/s)
  return (count,ent)

def splitindexlist(indexlist,mutation):
  withm=[];withoutm=[]
  for i in indexlist:
    if mutation in mml[i][1]: withm.append(i)
    else: withoutm.append(i)
  return (withm,withoutm)

class tree:
  mutation=None
  left=None# With mutation
  right=None# Without mutation
  def __init__(self,indexlist=range(len(mml)),parent=None):
    self.parent=parent
    self.indexlist=list(indexlist)
    self.count,self.ent=getstats(self.indexlist)
  def pr(self,level=0,label="Top"):
    step=4
    maxcol=30
    nl=len(lineages)
    wid=[max(len(lineages[j])+1,7) for j in range(min(nl,maxcol))]
    if label=="Top":
      for j in range(min(nl,maxcol)): print(" %*s"%(wid[j],lineages[j]),end="")
      if nl>maxcol: print(" ...",end="")
      print()
    for j in range(min(nl,maxcol)):
      print(" %*d"%(wid[j],self.count[j]),end="")
    if nl>maxcol: print(" ...",end="")
    print(" %12.1f"%self.ent,end="  ")
    for i in range(level): print("."+" "*(step-1),end="")
    print(label)
    if self.mutation!=None:
      self.left.pr(level+1,"+"+self.mutation)
      self.right.pr(level+1,"-"+self.mutation)
  def pr2(self,mlist=[]):
    maxcol=30
    nl=len(lineages)
    wid=[max(len(lineages[j])+1,7) for j in range(min(nl,maxcol))]
    if mlist==[]:
      for j in range(min(nl,maxcol)): print(" %*s"%(wid[j],lineages[j]),end="")
      if nl>maxcol: print(" ...",end="")
      print()
    if self.mutation!=None:
      self.left.pr2(mlist+["+"+self.mutation])
      self.right.pr2(mlist+["-"+self.mutation])
      return
    for j in range(min(nl,maxcol)):
      print(" %*d"%(wid[j],self.count[j]),end="")
    if nl>maxcol: print(" ...",end="")
    print(" %12.1f"%self.ent,end="  ")
    for m in mlist: print(m.replace("Spike","S"),end=" ")
    print()
  def split(self,mutation):
    if self.mutation!=None: raise RuntimeError("Can't split already-split node")
    (left,right)=splitindexlist(self.indexlist,mutation)
    self.mutation=mutation
    self.left=tree(left,self)
    self.right=tree(right,self)
  def getleaves(self):
    if self.mutation==None: yield self;return
    for leaf in self.left.getleaves(): yield leaf
    for leaf in self.right.getleaves(): yield leaf
  # Merge indexlist into the tree self, returning a new allocated tree
  def merge(self,indexlist):
    if self.mutation==None:
      tr=tree(self.indexlist+indexlist,self.parent)
      return tr
    else:
      left,right=splitindexlist(indexlist,self.mutation)
      l=self.left.merge(left)
      r=self.right.merge(right)
      p=tree(l.indexlist+r.indexlist,self.parent)
      p.mutation=self.mutation
      p.left=l
      p.right=r
      l.parent=p
      r.parent=p
      return p
  def check(self):
    count,ent=getstats(self.indexlist)
    if count!=self.count or abs(ent-self.ent)>1e-6: return False
    if self.mutation==None:
      return self.left==None and self.right==None
    if self.left==None or self.right==None: return False
    if self.left.parent!=self or self.right.parent!=self: return False
    return self.left.check() and self.right.check()
  def leafent(self):
    return sum(leaf.ent for leaf in self.getleaves())
  def printdecisiontree(self,depth=0,file=sys.stdout):
    wid=2
    ind=" "*((depth+1)*wid)
    if depth==0:
      print("lineages =",lineages,file=file)
      print(file=file)
      print("def treeclassify(mutations):",file=file)
      print(ind+"# Classification run at",datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S"),file=file)
      prparams(prefix=ind+"# ",file=file)
    if self.mutation==None:
      print(ind+'return "%s"'%(max(zip(self.count,lineages))[1]),file=file)
    else:
      print(ind+'if "%s" in mutations:'%(self.mutation),file=file)
      self.left.printdecisiontree(depth+1,file=file)
      print(ind+"else:",file=file)
      self.right.printdecisiontree(depth+1,file=file)

tr=tree()
print("Ent per sequence %g"%(tr.leafent()/len(ml)))
tr.pr2();print();sys.stdout.flush()
leaves=1
while leaves<args.maxleaves:
  worst=None
  for leaf in tr.getleaves():
    if worst==None or leaf.ent<worst.ent: worst=leaf
  if worst==None: break
  best=(0,None)
  for m in okm:
    (withm,withoutm)=splitindexlist(worst.indexlist,m)
    improvement=getstats(withm)[1]+getstats(withoutm)[1]-worst.ent
    #print("XXX",m,improvement)
    if improvement>best[0]: best=(improvement,m)
  if best[1]==None: print("Couldn't improve worst node");break
  worst.split(best[1])
  leaves+=1
  print("Ent per sequence %g"%(tr.leafent()/len(ml)))
  tr.pr2();print();sys.stdout.flush()
print()

print("Pruning")
print()
dectree=None
while leaves>1:
  best=(-1e10,)
  if not tr.check(): raise RuntimeError("A")
  for leaf in tr.getleaves():
    par=leaf.parent
    assert par!=None
    if par.left is leaf: 
      go=par.left
      keep=par.right
    else:
      go=par.right
      keep=par.left
    mer=keep.merge(go.indexlist)
    if not mer.check(): raise RuntimeError("B")
    entchg=mer.leafent()-par.leafent()
    if entchg>best[0]: best=(entchg,par,mer)
  entchg,par,mer=best
  par.left=mer.left
  par.right=mer.right
  par.mutation=mer.mutation
  if par.mutation is not None:
    par.left.parent=par
    par.right.parent=par
  par.count=mer.count
  par.indexlist=mer.indexlist
  if not par.check(): raise RuntimeError("C")
  if not tr.check(): raise RuntimeError("D")
  leaves-=1
  print("Ent per sequence %g"%(tr.leafent()/len(ml)))
  tr.pr2();print();sys.stdout.flush()
  if leaves==args.printtree:
    dectree="decisiontree"
    if args.gisaid: dectree+=".GISAID"
    else: dectree+=".COG-UK"
    dectree+=".from"+args.mindate
    dectree+=".leaves%d"%leaves
    dectree+=".maxbad%g"%args.maxbad
    with open(dectree,"w") as fp: tr.printdecisiontree(file=fp)

if dectree!=None: print("Written decision tree to \"%s\""%dectree)
