from stuff import *

# Get weekday pattern from case data in order to identify exact date on SGTF graph
# 0 mod 7 is Thursday in daytodate notation (being 1970-01-01)
nc={}
with open('SAcases','r') as fp:
  for x in fp:
    y=x.split()
    nc[datetoday(y[0])]=int(y[1])

minday=min(nc)
maxday=max(nc)
c0=[0]*7
c1=[0]*7
for d in range(minday+3,maxday-3):
  ex=[nc[r] for r in range(d-3,d+4)]
  if min(ex)>=50:
    i=d%7
    c0[i]+=1
    c1[i]+=nc[d]*7/sum(ex)

#for i in range(7):
#  print(i,c1[i]/c0[i])
# Thur 1.184
# Fri  1.170
# Sat  1.122
# Sun  0.913
# Mon  0.655
# Tue  0.766
# Wed  1.158

dateorigin=datetoday('2021-10-01')-564
y0=(0,358)
y1=(50,43)

# SGTF image from slide 12 of https://sacoronavirus.co.za/2021/11/25/sars-cov-2-sequencing-new-variant-update-25-november-2021/
# resized down by a factor of 2/3 in order to get 1 horizontal pixel = 1 day.
from PIL import Image
import numpy as np
im_frame = Image.open('OmicronSGTF.png')
cc = np.array(im_frame,dtype=int)
im_frame.close()
# Top-leftian, row before column

row0=23;row1=359
r=cc.shape[0]
c=cc.shape[1]

# Get blueness
bb=cc[:,:,2]*2-(cc[:,:,0]+cc[:,:,1])

def process(bb,name):
  bb1=bb[row0:row1,:]
  mm=row0+np.argmax(bb1,axis=0)
  im=Image.fromarray(((bb-bb.min())/(bb.max()-bb.min())*255.999+0.0005).astype(np.dtype('uint8')))
  im.save(name+'_filtered.png')

  oo=cc.astype(np.dtype('uint8'))
  for x in range(81,614): oo[mm[x],x]=[255,0,0]
  im=Image.fromarray(oo)
  im.save(name+'_sgtf.png')

  sgtf={}
  for x in range(81,614):
    sgtf[daytodate(dateorigin+x)]=(mm[x]-y1[1])/(y0[1]-y1[1])*(y0[0]-y1[0])+y1[0]
  with open(name+'_sgtf','w') as fp:
    for date in sorted(list(sgtf)):
      print(date,"%6.2f"%sgtf[date],file=fp)

  return sgtf

process(bb,'simple')

lrantialias=bb-np.maximum(np.roll(bb,1,1),np.roll(bb,-1,1))
process(lrantialias,'LRantialias')

# Hybrid because deantialiasing method is likely to work well for the vertical spike, but not when derivative is low.
spike=605
hybrid=np.concatenate([bb[:,:spike],lrantialias[:,spike:]],axis=1)
process(hybrid,'hybrid')