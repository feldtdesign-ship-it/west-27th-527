"""make_template_527.py: builds build/w27_template.html from the Broome page (lafayette-188/build/laf_template.html): same styles, charts and
scroll-driven model, with 527 West 27th's words (w27_body.html), model, camera path and colours (7-train purple)."""
import os, re
S = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(S, '..', '..', 'lafayette-188', 'build', 'laf_template.html')).read()
head = src[:src.index('<style>')]; css = src[src.index('<style>'):src.index('</style>') + 8]
js = src[src.index('<script>\nconst D = __DATA__'):]
def sub(s, pairs):
    for a, b in pairs:
        assert a in s, a[:80]; s = s.replace(a, b)
    return s
URL = 'https://feldtdesign-ship-it.github.io/west-27th-527/'
DESC = "527 West 27th Street: the retail floor of Jardim, Isay Weinfeld's concrete condominium a half block west of the High Line. 61 feet of glass, finished 2019, never let. The building, the space, the block's dark doors, the trains, from public data."
head = sub(head, [
 ('<title>The Small Pink Store</title>', '<title>Never Opened</title>'),
 ('https://feldtdesign-ship-it.github.io/broome-413/og.jpg', URL + 'og.jpg'),
 ('https://feldtdesign-ship-it.github.io/broome-413/', URL),
 ('413 Broome Street · The Small Pink Store', '527 West 27th Street · Never Opened'),
])
for k in ('name="description"', 'property="og:description"', 'name="twitter:description"'):
    head = re.sub(r'<meta ' + re.escape(k) + r' content="[^"]*">', f'<meta {k} content="{DESC}">', head)
# 7-train purple replaces the 6-train green as the page's accent
css = css.replace('--f:#2DBE6C;--six:#00933C;', '--f:#C56BD3;--six:#B933AD;')
css = css.replace('h1 em{font-style:normal;font-weight:300;color:#E0679A}', 'h1 em{font-style:normal;font-weight:300;color:var(--f)}')
js = sub(js, [
 ("$('sub').innerHTML=`Entries at Spring Street and Canal Street added together and doubled to include exits, summer 2026 average. The nearest stairs are <b>192 m</b> away.",
  "$('sub').innerHTML=`Entries at 34 St-Hudson Yards and 23 St added together and doubled to include exits, summer 2026 average. The nearest stairs are <b>543 m</b> away."),
 ("const MODEL='assets/lafayette_188.glb';", "const MODEL='assets/west_27th_527.glb';"),
 ("const P=__POINTS__; const DOOR=P.door, N=[0.842,0.541];   // N = the way the pink store's Lafayette window faces",
  "const P=__POINTS__; const DOOR=P.door, N=P.facing;   // N = the way the glass faces, out over 27th Street (glTF x east, z south)"),
 ("BOW=G('canal_st'), SPR=G('spring_6'), GRD=G('prince_rw'); const MID=[(BOW[0]+SPR[0]+GRD[0])/3,0,(BOW[2]+SPR[2]+GRD[2])/3];",
  "BOW=G('hudson_yards_7'), SPR=G('st23_ce'), GRD=G('highline_28'); const MID=[(BOW[0]+SPR[0]+GRD[0])/3,0,(BOW[2]+SPR[2]+GRD[2])/3];"),
 ("if(n.startsWith('SOHO_MASSING'))", "if(n.startsWith('CHELSEA_MASSING'))"),
 ("else if(n.startsWith('SITE_188')){o.castShadow=true;if(m){m.color=new THREE.Color(0xB89B72);m.emissive=new THREE.Color(0xB89B72);m.emissiveIntensity=.38;}}",
  "else if(n.startsWith('SITE_527')||n.startsWith('B527_FACE')||n.startsWith('B527_TRAYS')){o.castShadow=true;if(m){m.color=new THREE.Color(0xB4AFA5);m.emissive=new THREE.Color(0xB4AFA5);m.emissiveIntensity=.3;}}\n   else if(n.startsWith('B527_FINS')){if(m){m.color=new THREE.Color(0x8E897F);m.emissive=new THREE.Color(0x8E897F);m.emissiveIntensity=.2;}}\n   else if(n.startsWith('B527_SHOPGLASS')){if(m){m.color=new THREE.Color(0xB933AD);m.emissive=new THREE.Color(0xC56BD3);m.emissiveIntensity=.8;m.transparent=false;m.opacity=1;}}\n   else if(n.startsWith('B527_CORTEN')){if(m){m.color=new THREE.Color(0x6B3F26);m.emissive=new THREE.Color(0x6B3F26);m.emissiveIntensity=.3;}}\n   else if(n.startsWith('B527_SIGN')){if(m){m.color=new THREE.Color(0xB08D4A);m.emissive=new THREE.Color(0xB08D4A);m.emissiveIntensity=.5;}}\n   else if(n.startsWith('B527_GARDEN')||n.startsWith('HIGH_LINE_DECK')){if(m){m.color=new THREE.Color(0x3B4F38);m.emissive=new THREE.Color(0x3B4F38);m.emissiveIntensity=.35;}}\n   else if(n.startsWith('HIGH_LINE')){o.castShadow=true;if(m)m.color=new THREE.Color(0x121212);}\n   else if(n.startsWith('B527_')){if(m){m.color=new THREE.Color(0x0D1714);m.transparent=false;m.opacity=1;}}"),
 ("else if(n.startsWith('B188_')&&n.includes('PINK')){if(m){m.color=new THREE.Color(0xE0679A);m.emissive=new THREE.Color(0xE0679A);m.emissiveIntensity=.8;}}", ""),
 ("else if(n.startsWith('B188_')&&n.includes('TAN')){if(m){m.color=new THREE.Color(0xB89B72);m.emissive=new THREE.Color(0xB89B72);m.emissiveIntensity=.38;}}", ""),
 ("else if(n.startsWith('B188_')&&(n.includes('IRON')||n.includes('GLASS'))){if(m){m.color=new THREE.Color(0x0A0A0A);m.transparent=false;m.opacity=1;}}", ""),
 ("else if(n.startsWith('B188_')&&n.includes('SHOPGLASS')){if(m){m.color=new THREE.Color(0x0D1714);m.transparent=false;m.opacity=1;}}", ""),
])
body = open(os.path.join(S, 'w27_body.html')).read()
open(os.path.join(S, 'w27_template.html'), 'w').write(head + css + '</head><body>\n' + body + js)
print('template written', len(head + css + body + js) // 1024, 'KB')
