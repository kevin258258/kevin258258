"""Build the README's live, procedural ASCII stone (Python standard library only).

Run: python assets/render_hollow_stone.py

This writes a scene description, not video frames. The browser computes two
Perlin-noise displacement fields plus a grain field with native SVG filters.
Independent periods combine into evolving erosion and lighting. The solid
has a thick faceted shell, a recessed mouth and a smaller opening at depth.
Glyphs stay on an ASCII grid; only the masks and their shading are deformed.
No JavaScript, raster images, external fonts or external services are used.
"""

from pathlib import Path
import math

ROOT=Path(__file__).resolve().parent
OUTER='M 281 98 L 429 72 L 569 117 L 642 213 L 659 346 L 608 481 L 488 549 L 351 525 L 243 415 L 222 273 L 246 171 Z'
MOUTH='M 397 205 L 489 199 L 535 267 L 508 366 L 420 408 L 351 363 L 334 279 Z'
DEEP='M 431 254 L 481 245 L 510 290 L 486 354 L 434 371 L 386 345 L 382 292 Z'
TOP='M 281 98 L 429 72 L 569 117 L 642 213 L 489 199 L 397 205 L 246 171 Z'
LEFT='M 246 171 L 397 205 L 334 279 L 351 363 L 351 525 L 243 415 L 222 273 Z'
BOTTOM='M 351 363 L 420 408 L 508 366 L 608 481 L 488 549 L 351 525 Z'
CAVE_LEFT='M 397 205 L 431 254 L 382 292 L 386 345 L 351 363 L 334 279 Z'
CAVE_BOTTOM='M 351 363 L 386 345 L 434 371 L 486 354 L 508 366 L 420 408 Z'


def animate(attr,values,dur):
    count=len(values.split(';'))-1
    return f'<animate attributeName="{attr}" values="{values}" dur="{dur}s" repeatCount="indefinite" calcMode="spline" keyTimes="'+ ';'.join(str(i/count) for i in range(count+1))+ '" keySplines="'+ ';'.join(['.45 0 .55 1']*count)+'"/>'


def generate(theme):
    fg = '#e6edf3' if theme == 'dark' else '#18212c'
    background='#0d1117' if theme=='dark' else '#ffffff'
    # One shaded relief mask shares a single displacement field across every
    # face. This preserves depth alignment and avoids eight filter passes.
    masks = f'''<clipPath id="front-shell"><path d="{OUTER} {MOUTH}" fill-rule="evenodd" clip-rule="evenodd"/></clipPath>
<mask id="volume" maskUnits="userSpaceOnUse" x="0" y="0" width="900" height="660">
<g filter="url(#warp)">
<g transform="translate(42 38)"><path d="{OUTER}" fill="#404040"/><path d="{MOUTH}" fill="black"/></g>
<path d="{OUTER}" fill="#b0b0b0"/>
<g clip-path="url(#front-shell)"><path d="{TOP}" fill="white"/><path d="{LEFT}" fill="#d0d0d0"/><path d="{BOTTOM}" fill="#a0a0a0"/></g>
<path d="{MOUTH}" fill="#353535"/>
<path d="{CAVE_LEFT}" fill="#666666"/><path d="{CAVE_BOTTOM}" fill="#888888"/>
<path d="{DEEP}" fill="black"/>
</g></mask>'''
    rows=[]
    ramp='.,:;-=+*#%@'
    for y in range(60):
        chars=[]
        for x in range(126):
            f=.5+.19*math.sin(x*.16+y*.08)+.12*math.sin(x*.41-y*.33)+.10*math.sin(x*.91+y*1.2)
            chars.append(ramp[min(9,max(0,int(f*10)))])
        rows.append(f'<tspan x="34" y="{40+y*10}" textLength="832" lengthAdjust="spacingAndGlyphs">'+''.join(chars)+'</tspan>')
    plane='<text id="ascii" font-family="monospace" font-size="11" xml:space="preserve">'+''.join(rows)+'</text>'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="900" height="660" viewBox="0 0 900 660">
<defs>
<filter id="warp" x="0" y="0" width="900" height="660" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency=".004 .006" numOctaves="2" seed="37" result="continental">{animate('baseFrequency','.004 .006;.008 .004;.003 .009;.004 .006',11.313)}</feTurbulence>
<feTurbulence type="fractalNoise" baseFrequency=".012 .011" numOctaves="1" seed="83" result="erosion">{animate('baseFrequency','.012 .011;.005 .015;.010 .006;.012 .011',17.321)}</feTurbulence>
<feComposite in="continental" in2="erosion" operator="arithmetic" k1="0" k2=".72" k3=".28" k4="0" result="field"/>
<feDisplacementMap in="SourceGraphic" in2="field" scale="220" xChannelSelector="R" yChannelSelector="G">{animate('scale','220;110;360;220',23.719)}</feDisplacementMap>
</filter>
<filter id="grain" x="0" y="0" width="900" height="660" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency=".025 .04" numOctaves="2" seed="16" result="noise">{animate('baseFrequency','.025 .04;.038 .022;.025 .04',31.173)}</feTurbulence>
<feColorMatrix in="noise" type="saturate" values="0"/>
<feComponentTransfer result="grain"><feFuncR type="linear" slope=".8" intercept=".25"/><feFuncG type="linear" slope=".8" intercept=".25"/><feFuncB type="linear" slope=".8" intercept=".25"/><feFuncA type="linear" slope="0" intercept="1"/></feComponentTransfer>
<feComposite in="SourceGraphic" in2="grain" operator="arithmetic" k1="1" k2="0" k3="0" k4="0"/>
</filter>
<linearGradient id="light" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{fg}" stop-opacity=".95"/><stop offset=".45" stop-color="{fg}" stop-opacity=".75"/><stop offset="1" stop-color="{fg}" stop-opacity=".3"/></linearGradient>
{plane}
{masks}
</defs>
<rect width="900" height="660" fill="{background}"/>
<g>
<animateTransform attributeName="transform" type="rotate" values="-8 450 330;7 450 330;-4 450 330;-8 450 330" dur="35.411s" repeatCount="indefinite"/>
<use xlink:href="#ascii" fill="url(#light)" filter="url(#grain)" mask="url(#volume)"/>
</g>
</svg>'''
    p=ROOT/f'hollow-stone-{theme}.svg'
    p.write_text(svg)
    print(p.name,len(svg))

if __name__ == '__main__':
    for theme in ('dark', 'light'):
        generate(theme)
