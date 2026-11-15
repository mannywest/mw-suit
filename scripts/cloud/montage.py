import sys
from PIL import Image, ImageDraw
prefix=sys.argv[1]; out=sys.argv[2]
names=['front','front34','frontclose','top','back','backhigh','back34L','back34R']
ims=[Image.open(f'{prefix}_{n}.png').convert('RGB') for n in names]
h=420
rs=[im.resize((int(im.width*h/im.height),h)) for im in ims]
W=max(sum(r.width for r in rs[:4]),sum(r.width for r in rs[4:]))
sheet=Image.new('RGB',(W,2*h),(255,255,255))
for row in (0,1):
    x=0
    for n,r in zip(names[row*4:row*4+4],rs[row*4:row*4+4]):
        sheet.paste(r,(x,row*h)); ImageDraw.Draw(sheet).text((x+6,row*h+4),n,fill=(255,0,0)); x+=r.width
sheet.save(out); print(sheet.size)
