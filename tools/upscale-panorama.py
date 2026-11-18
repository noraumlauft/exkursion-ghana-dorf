import sys,torch,numpy as np
# Hochskalieren eines 360°-Panoramas: python3 tools/upscale-panorama.py EINGABE MODELL.pth AUSGABE ZIELFAKTOR
from PIL import Image
from spandrel import ModelLoader
src,model_path,out,target_scale=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4])
torch.set_num_threads(4)
m=ModelLoader().load_from_file(model_path).eval()
sc=m.scale
im=np.asarray(Image.open(src).convert('RGB')).astype(np.float32)/255
H,W,_=im.shape;PAD=32
# 360°: links/rechts umlaufend auffüllen, damit die Naht nahtlos bleibt
im=np.concatenate([im[:,-PAD:],im,im[:,:PAD]],1)
x=torch.from_numpy(im).permute(2,0,1)[None]
T,O=256,16;_,_,h,w=x.shape;res=torch.zeros(1,3,h*sc,w*sc)
with torch.no_grad():
  for y0 in range(0,h,T):
    for x0 in range(0,w,T):
      ya,xa=max(0,y0-O),max(0,x0-O);yb,xb=min(h,y0+T+O),min(w,x0+T+O)
      r=m(x[:,:,ya:yb,xa:xb])
      cy,cx=(y0-ya)*sc,(x0-xa)*sc;hh,ww=(min(h,y0+T)-y0)*sc,(min(w,x0+T)-x0)*sc
      res[:,:,y0*sc:y0*sc+hh,x0*sc:x0*sc+ww]=r[:,:,cy:cy+hh,cx:cx+ww]
    print('row',y0,flush=True)
a=(res[0].clamp(0,1).permute(1,2,0).numpy()*255+.5).astype(np.uint8)[:,PAD*sc:PAD*sc+W*sc]
img=Image.fromarray(a)
if sc!=target_scale:img=img.resize((W*target_scale,H*target_scale),Image.LANCZOS)
img.save(out,quality=92) if out.endswith('.webp') else img.save(out)
print(img.size)
