"""Render the shared architecture elements as a clean PNG/SVG documentation preview.
The editable drawing is brain-architecture.excalidraw; this exporter needs Pillow.
"""
import json, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).parent
items=json.loads((root/'elements.json').read_text())
scale=2
im=Image.new('RGB',(3200,2400),'white');d=ImageDraw.Draw(im)
fontfile='/System/Library/Fonts/Supplemental/Arial.ttf'
if not Path(fontfile).exists():fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 1600 1200"><rect width="1600" height="1200" fill="white"/>']
def label(x,y,t,size,center=False):
 font=ImageFont.truetype(fontfile,int(size*scale));lines=t.split('\n');lh=size*1.3
 if center:y-=len(lines)*lh/2
 for line in lines:
  xx=x-d.textlength(line,font=font)/scale/2 if center else x
  d.text((xx*scale,y*scale),line,font=font,fill='#172b4d')
  svg.append(f'<text x="{xx}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" fill="#172b4d">{html.escape(line)}</text>')
  y+=lh
for e in items:
 kind=e['type'];x=e.get('x',0);y=e.get('y',0);w=e.get('width',0);h=e.get('height',0)
 if kind=='rectangle':
  color=e['backgroundColor'];d.rounded_rectangle((x*scale,y*scale,(x+w)*scale,(y+h)*scale),radius=18*scale,fill=color,outline='#34475e',width=2)
  svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{color}" stroke="#34475e"/>')
  label(x+w/2,y+h/2,e['label']['text'],e['label']['fontSize'],True)
 elif kind=='text':label(x,y,e['text'],e['fontSize'])
 elif kind=='arrow':
  dx,dy=e['points'][-1];ex=x+dx;ey=y+dy
  import math
  angle=math.atan2(dy,dx)
  a=(ex-12*math.cos(angle-.4),ey-12*math.sin(angle-.4));b=(ex-12*math.cos(angle+.4),ey-12*math.sin(angle+.4))
  d.line((x*scale,y*scale,ex*scale,ey*scale),fill='#4b6584',width=3)
  d.line((a[0]*scale,a[1]*scale,ex*scale,ey*scale,b[0]*scale,b[1]*scale),fill='#4b6584',width=3)
  svg.append(f'<path d="M{x} {y}L{ex} {ey}M{a[0]} {a[1]}L{ex} {ey}L{b[0]} {b[1]}" fill="none" stroke="#4b6584" stroke-width="2"/>')
  if e.get('label'):
   # Agent link is deliberately labelled separately to avoid collision with cards.
   t=e['label']['text'];label((x+ex)/2, min(y,ey)-25, t,14,True)
svg.append('</svg>');(root/'brain-architecture.svg').write_text('\n'.join(svg))
im.save(root/'brain-architecture.png')
