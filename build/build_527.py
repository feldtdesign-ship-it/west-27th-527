"""
build_527.py
Block model for 527 West 27th Street (Jardim retail, Centaur) from the NYC Open Data layers in data/ (pulled by build/pull.py).
Same build as lafayette-188/build/build_188.py, re-pointed, with stage_building() for Jardim and stage_highline() for the High Line.
Headless (never his open Blender):  /Applications/Blender.app/Contents/MacOS/Blender --background --python build/build_527.py
Facade detail is INFERRED from the SBLM plan (61'-7" retail frontage, 33'-4" deep) + Google Street View Apr 2026 (listing/streetview/).
"""
import bpy, bmesh, json, math, os
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else "/Users/michaelweinfeld/Documents/2026/PJ O'Rourke/Location Research/west-27th-527"
DATA_DIR = os.path.join(OUT_DIR, "data")
SITE_LAT, SITE_LON = 40.751109, -74.003437
SITES = {"1006990049": ("SITE_527", "PJ_CONCRETE")}      # footprints carry the pre-condo base lot, not 7504
FT = 0.3048; H_FALLBACK = 9.0; COLLECTION = "W27_527"
# dark ground; Jardim in its board-formed concrete, the retail in stainless + clear glass, High Line in black iron with a planted top.
# Accent for the page is the 7-train purple (34 St-Hudson Yards, 543 m). Colours are one line to change.
PALETTE = {"PJ_INK": "2A2724", "PJ_GROUND": "141210", "PJ_ROAD": "1C1A18", "PJ_WALK": "2B2823", "PJ_MEDIAN": "34302A", "PJ_TREE": "4A5A3A",
           "PJ_LABEL": "8A857C", "PJ_GLASS": "0D1714", "PJ_SHOPGLASS": "A9B8B4", "PJ_IRON": "121212", "PJ_HLDECK": "3B4F38",
           "PJ_CONCRETE": "B4AFA5", "PJ_CONCRETE_DK": "8E897F", "PJ_STEEL": "C9CDCE", "PJ_BRASS": "B08D4A", "PJ_PURPLE": "B933AD",
           "PJ_FLOOR": "8C8A86", "PJ_WHITE": "E8E5DE", "PJ_TUNNEL": "0A0908", "PJ_CORTEN": "6B3F26"}
COSL = math.cos(math.radians(SITE_LAT))

def proj(lon, lat): return ((lon - SITE_LON) * 111320.0 * COSL, (lat - SITE_LAT) * 110540.0)
def hex_to_linear(h):
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i+2], 16) / 255.0; out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)
def make_materials():
    for name, hexc in PALETTE.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b: b.inputs["Base Color"].default_value = hex_to_linear(hexc); b.inputs["Roughness"].default_value = 0.95
        m.diffuse_color = hex_to_linear(hexc)
        if name == "PJ_STEEL" and b:
            b.inputs["Roughness"].default_value = 0.35
            if "Metallic" in b.inputs: b.inputs["Metallic"].default_value = 0.8
        if name == "PJ_SHOPGLASS" and b:                                                      # clear storefront glass
            b.inputs["Alpha"].default_value = 0.10; b.inputs["Roughness"].default_value = 0.04
            for k in ("Specular IOR Level", "Specular"):
                if k in b.inputs: b.inputs[k].default_value = 0.0
            for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND"), ("use_backface_culling", False), ("show_transparent_back", True), ("use_transparency_overlap", True)):
                try: setattr(m, attr, val)
                except Exception: pass
def load(key):
    """data/<key>.json is a list of Socrata rows with the geometry in the_geom (or multipolygon). Return GeoJSON-ish features."""
    rows = json.load(open(os.path.join(DATA_DIR, key + ".json")))
    out = []
    for r in rows:
        g = r.get("the_geom") or r.get("multipolygon") or r.get("geometry")
        if g: out.append({"properties": r, "geometry": g})
    return out
def rings(geom):
    t = geom.get("type"); c = geom.get("coordinates", [])
    if t == "Polygon": return [c[0]] if c else []
    if t == "MultiPolygon": return [p[0] for p in c if p]
    return []
def contours(geom):
    t = geom.get("type"); c = geom.get("coordinates", [])
    src = [c] if t == "Polygon" else (c if t == "MultiPolygon" else [])
    for poly in src:
        out = []
        for ring in poly:
            pts = [proj(a, b) for a, b in ring]; cl = []
            for p in pts:
                if not cl or abs(p[0]-cl[-1][0]) > 1e-7 or abs(p[1]-cl[-1][1]) > 1e-7: cl.append(p)
            if len(cl) > 2 and abs(cl[0][0]-cl[-1][0]) < 1e-7 and abs(cl[0][1]-cl[-1][1]) < 1e-7: cl = cl[:-1]
            if len(cl) >= 3: out.append(cl)
        if out: yield out

def get_collection():
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for o in list(old.objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(COLLECTION); bpy.context.scene.collection.children.link(col); return col
def col(): return bpy.data.collections.get(COLLECTION) or get_collection()

def extrude_ring(bm, xy, z0, z1):
    cl = []
    for p in xy:
        if not cl or abs(p[0]-cl[-1][0]) > 1e-6 or abs(p[1]-cl[-1][1]) > 1e-6: cl.append(p)
    if len(cl) > 2 and abs(cl[0][0]-cl[-1][0]) < 1e-6 and abs(cl[0][1]-cl[-1][1]) < 1e-6: cl = cl[:-1]
    if len(cl) < 3: return False
    vs = [bm.verts.new((p[0], p[1], z0)) for p in cl]
    try: face = bm.faces.new(vs)
    except ValueError: return False
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=[v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)])
    return True
def mesh_from_bm(bm, name, mat):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col().objects.link(ob); ob.data.materials.append(bpy.data.materials[mat]); return ob

def stage_massing():
    make_materials(); get_collection(); feats = load("footprints")
    bases = [float(f["properties"].get("ground_elevation") or 0) for f in feats if f["properties"].get("base_bbl") in SITES]
    base = sum(bases) / len(bases) if bases else 0.0
    bm = bmesh.new(); n = 0; guessed = 0
    for f in feats:
        p = f["properties"]
        if p.get("base_bbl") in SITES: continue                      # Jardim is built by stage_building()
        try: h_ft = float(p.get("height_roof") or 0)
        except ValueError: h_ft = 0.0
        h = h_ft * FT
        if h <= 0: h = H_FALLBACK; guessed += 1
        ge = (float(p.get("ground_elevation") or base) - base) * FT
        for ring in rings(f["geometry"]):
            if extrude_ring(bm, [proj(a, b) for a, b in ring], ge, ge + h): n += 1
    mesh_from_bm(bm, "CHELSEA_MASSING", "PJ_INK")
    return "massing: {} solids, {} without height".format(n, guessed)

def build_flat(key, name, z, mat):
    feats = load(key); verts, faces = [], []
    for f in feats:
        for cont in contours(f["geometry"]):
            vecs = [[Vector((x, y, 0.0)) for (x, y) in ring] for ring in cont]; flat = [v for ring in vecs for v in ring]; b = len(verts)
            try: idx = tessellate_polygon(vecs)
            except Exception: continue
            verts.extend([(v.x, v.y, z) for v in flat]); faces.extend([(b+t[0], b+t[1], b+t[2]) for t in idx])
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me); col().objects.link(ob); ob.data.materials.append(bpy.data.materials[mat])
    return "{}: {} tris".format(name, len(faces))
def stage_flat():
    return "; ".join([build_flat("roadbed", "ROADBED", 0.02, "PJ_ROAD"), build_flat("sidewalk", "SIDEWALK", 0.14, "PJ_WALK"), build_flat("median", "MEDIAN", 0.18, "PJ_MEDIAN")])

def at_fraction(pts, frac):
    segs = [math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1)]; total = sum(segs); want = total * frac; run = 0.0
    for i, s in enumerate(segs):
        if run + s >= want:
            t = (want - run) / s if s else 0.0; a, b = pts[i], pts[i+1]
            return ((a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t), math.atan2(b[1]-a[1], b[0]-a[0]))
        run += s
    return pts[-1], math.atan2(pts[-1][1]-pts[0][1], pts[-1][0]-pts[0][0])
def stage_labels(size=12.0, min_gap=34.0):
    feats = load("centerline"); longest = {}
    for f in feats:
        n = (f["properties"].get("stname_label") or "").strip()
        if not n: continue
        g = f["geometry"]; parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for line in parts:
            pts = [proj(a, b) for a, b in line]; L = sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
            if n not in longest or L > longest[n][0]: longest[n] = (L, pts)
    placed = []
    for name, (L, pts) in sorted(longest.items(), key=lambda kv: -kv[1][0]):
        if L < 40: continue
        spot = None
        for frac in (0.5, 0.3, 0.7, 0.18, 0.82):
            p, ang = at_fraction(pts, frac)
            if all(math.dist(p, q) > min_gap for q in placed): spot = (p, ang); break
        if spot is None: spot = at_fraction(pts, 0.5)
        p, ang = spot
        if ang > math.pi/2: ang -= math.pi
        if ang < -math.pi/2: ang += math.pi
        cu = bpy.data.curves.new("ST_" + name, type='FONT'); cu.body = name; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = size; cu.extrude = 0.04; cu.space_character = 1.15
        ob = bpy.data.objects.new("ST_" + name, cu); col().objects.link(ob); ob.location = (p[0], p[1], 0.6); ob.rotation_euler = (0, 0, ang); ob.data.materials.append(bpy.data.materials["PJ_LABEL"]); placed.append(p)
    return "labels: {}".format(len(placed))

def stage_trees():
    rows = [r for r in json.load(open(os.path.join(DATA_DIR, "trees.json"))) if r.get("status") == "Alive"]
    bm = bmesh.new(); n = 0
    for t in rows:
        try: x, y = proj(float(t["longitude"]), float(t["latitude"])); dbh = float(t.get("tree_dbh") or 6)
        except (TypeError, ValueError, KeyError): continue
        r = max(1.4, min(4.2, 1.2 + dbh * 0.12)); h = max(4.0, min(11.0, 3.5 + dbh * 0.35))
        tb = bmesh.new(); bmesh.ops.create_icosphere(tb, subdivisions=1, radius=1.0); bmesh.ops.scale(tb, vec=(r, r, r * 0.8), verts=tb.verts); bmesh.ops.translate(tb, vec=(x, y, h), verts=tb.verts)
        me = bpy.data.meshes.new("t"); tb.to_mesh(me); tb.free(); bm.from_mesh(me); bpy.data.meshes.remove(me); n += 1
    mesh_from_bm(bm, "TREES", "PJ_TREE")
    return "trees: {}".format(n)

def stage_ground():
    bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -0.3)); g = bpy.context.active_object; g.name = "GROUND"
    for c in g.users_collection: c.objects.unlink(g)
    col().objects.link(g); g.data.materials.append(bpy.data.materials["PJ_GROUND"]); return "ground"

# ---------- the High Line (NYC Parks property M360 outline, deck ~30 ft over the street) ----------
HL_DECK = 30 * FT; HL_UNDER = 18 * FT
def stage_highline():
    feats = load("highline_parks")
    if not feats: return "highline: no outline"
    bm = bmesh.new(); top = bmesh.new(); n = 0
    for f in feats:
        for ring in rings(f["geometry"]):
            xy = [proj(a, b) for a, b in ring]
            if min(math.hypot(x, y) for x, y in xy) > 1200: continue
            if extrude_ring(bm, xy, HL_UNDER, HL_DECK): n += 1
            extrude_ring(top, xy, HL_DECK, HL_DECK + 0.25)
    mesh_from_bm(bm, "HIGH_LINE", "PJ_IRON"); mesh_from_bm(top, "HIGH_LINE_DECK", "PJ_HLDECK")
    return "highline: {} pieces".format(n)

# ---------- Jardim itself ----------
# The city outline is one 100 x 197.5 ft rectangle for both buildings. Local frame: origin = SW corner (west end of the 27th St front),
# x east along 27th Street, y north toward 28th. South building = 527 W 27th (11 fl, 135 ft), garden in the middle, north building = 528 W 28th.
ROOF = 135 * FT; GF = 14 * FT; NFL = 11; SOUTH_D = 78 * FT; NORTH_D = 78 * FT
# 27th St front, west -> east, from PJ's photo + Street View Apr 2026: corten service door, the glass storefront with the lease sign,
# a run of bare concrete with the brass "Jardim" script, the through-block tunnel, the "527" pier. The curved steel bays east of that are 519-521, not Jardim.
RETAIL_X0, RETAIL_X1 = 0.0 * FT, 61.6 * FT          # SBLM plan: 61'-7" x 33'-4" room at the west end
CORTEN = (1.5 * FT, 14.0 * FT)                       # corten door (service / elevator lobby)
GLASS = (14.0 * FT, 46.0 * FT); PANES = 3            # three panes in a dark bronze frame; door in the east pane
TUNNEL_X0, TUNNEL_X1 = 60.0 * FT, 78.0 * FT
SIGN_X = 53.0 * FT
FRAME = None
def _frame():
    """(origin, ex, ey) in model metres from the footprint corners."""
    global FRAME
    if FRAME: return FRAME
    for f in load("footprints"):
        if f["properties"].get("base_bbl") in SITES:
            pts = [proj(a, b) for a, b in rings(f["geometry"])[0]][:4]
            D = min(pts, key=lambda p: p[1] * 0.3 - p[0] * -1.0)      # west end of the south front: smallest x+... use explicit picks below
            S = min(pts, key=lambda p: p[1])                           # southmost = east end of the 27th front
            W = min(pts, key=lambda p: p[0])                           # westmost = west end of the 27th front
            N = max(pts, key=lambda p: p[1])                           # northmost = west end of the 28th front
            ex = (Vector(S) - Vector(W)); ey = (Vector(N) - Vector(W)); L = ex.length; Dp = ey.length
            FRAME = (Vector(W), ex.normalized(), ey.normalized(), L, Dp); return FRAME
    raise RuntimeError("site footprint not found")
def _world(x, y, z):
    o, ex, ey, L, Dp = _frame(); p = o + ex * x + ey * y; return (p.x, p.y, z)
def _box(bm, x0, x1, y0, y1, z0, z1):
    vs = [bm.verts.new(_world(x, y, z)) for (x, y, z) in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for idx in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)): bm.faces.new([vs[i] for i in idx])
def _rounded_rect(bm, x0, x1, z0, z1, r, y0, y1):
    """A rounded-rectangle plate in the x-z plane (the 27th St face), thick from y0 to y1. Used as a boolean cutter."""
    pts = []
    cx = [(x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180), (x1 - r, z0 + r, 270)]
    for (cxx, czz, a0) in cx:
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6); pts.append((cxx + r * math.cos(a), czz + r * math.sin(a)))
    lo = [bm.verts.new(_world(x, y0, z)) for x, z in pts]; hi = [bm.verts.new(_world(x, y1, z)) for x, z in pts]
    bm.faces.new(lo); bm.faces.new(list(reversed(hi)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts); bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
def _cut(target, cutter):
    m = target.modifiers.new("cut", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter
    try: m.solver = 'EXACT'
    except Exception: pass
    with bpy.context.temp_override(object=target, active_object=target): bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def stage_building():
    for o in [o for o in bpy.data.objects if o.name.startswith("B527_") or o.name == "SITE_527"]: bpy.data.objects.remove(o, do_unlink=True)
    o, ex, ey, L, Dp = _frame(); garden0, garden1 = SOUTH_D, Dp - NORTH_D
    # ground floor: full through-block slab of concrete, GF high
    bm = bmesh.new(); _box(bm, 0, L, 0, Dp, 0, GF); gf = mesh_from_bm(bm, "SITE_527", "PJ_CONCRETE")
    # tunnel: cut straight through the ground floor
    bm = bmesh.new(); _box(bm, TUNNEL_X0, TUNNEL_X1, -1, Dp + 1, 0, GF - 0.6 * FT); _cut(gf, mesh_from_bm(bm, "B527_CUT_TUNNEL", "PJ_TUNNEL"))
    # retail: cut the 61'-7" x 33'-4" room out of the slab at the west end; corten door, then the glass, concrete above and east of it
    bm = bmesh.new(); _box(bm, RETAIL_X0 + 0.5 * FT, RETAIL_X1, -0.5, 33.3 * FT, 0.5 * FT, GF - 1.0 * FT); _cut(gf, mesh_from_bm(bm, "B527_CUT_RETAIL", "PJ_TUNNEL"))
    bm = bmesh.new(); _box(bm, GLASS[0], GLASS[1], -0.02, 0.0, 0.5 * FT, 11.5 * FT); mesh_from_bm(bm, "B527_SHOPGLASS", "PJ_SHOPGLASS")
    bm = bmesh.new()
    pw = (GLASS[1] - GLASS[0]) / PANES
    for k in range(PANES + 1): _box(bm, GLASS[0] + k * pw - 0.06, GLASS[0] + k * pw + 0.06, -0.12, 0.02, 0.4 * FT, 11.6 * FT)
    _box(bm, GLASS[0], GLASS[1], -0.12, 0.02, 11.4 * FT, 11.7 * FT); _box(bm, GLASS[0], GLASS[1], -0.12, 0.02, 0.4 * FT, 0.6 * FT)
    mesh_from_bm(bm, "B527_FRAME", "PJ_IRON")
    bm = bmesh.new(); _box(bm, GLASS[1] - pw + 0.3, GLASS[1] - 0.3, -0.08, -0.02, 0.6 * FT, 9.0 * FT); mesh_from_bm(bm, "B527_DOOR", "PJ_GLASS")
    bm = bmesh.new(); _box(bm, GLASS[0], GLASS[1], -0.3, 0.0, 11.7 * FT, GF); _box(bm, RETAIL_X0, GLASS[0], -0.3, 0.0, 0.0, GF); _box(bm, GLASS[1], RETAIL_X1 + 0.5 * FT, -0.3, 0.0, 0.0, GF)
    mesh_from_bm(bm, "B527_FACE", "PJ_CONCRETE")
    bm = bmesh.new(); _box(bm, CORTEN[0], CORTEN[1], -0.36, -0.28, 0.0, 11.5 * FT); mesh_from_bm(bm, "B527_CORTEN", "PJ_CORTEN")
    bm = bmesh.new(); _box(bm, RETAIL_X0 + 0.5 * FT, RETAIL_X1, 0.0, 33.3 * FT, 0.45 * FT, 0.5 * FT); mesh_from_bm(bm, "B527_FLOOR", "PJ_FLOOR")
    # brass script on the concrete between the glass and the tunnel
    cu = bpy.data.curves.new("B527_SIGN", type='FONT'); cu.body = "Jardim"; cu.size = 1.1; cu.extrude = 0.02; cu.align_x = 'CENTER'
    sign = bpy.data.objects.new("B527_SIGN", cu); col().objects.link(sign); sign.data.materials.append(bpy.data.materials["PJ_BRASS"])
    ang = math.atan2(ex.y, ex.x); sign.location = _world(SIGN_X, -0.06, 9.0 * FT); sign.rotation_euler = (math.radians(90), 0, ang)
    # uppers: two glass bodies set back a foot, with a concrete tray at every floor (Weinfeld's horizontal slabs); garden between
    fl = (ROOF - GF) / (NFL - 1); s = 1.0 * FT
    for name, y0, y1 in (("S", 0, garden0), ("N", garden1, Dp)):
        bm = bmesh.new(); _box(bm, s, L - s, y0 + s, y1 - s, GF, ROOF); mesh_from_bm(bm, "B527_BODY_" + name, "PJ_GLASS")
        bm = bmesh.new()
        for k in range(NFL):
            z = GF + k * fl; _box(bm, 0, L, y0, y1, z, z + 1.2 * FT)
        mesh_from_bm(bm, "B527_TRAYS_" + name, "PJ_CONCRETE")
        bm = bmesh.new()
        for k in range(NFL - 1):                                    # a few concrete fins so it is not a bare glass box
            z = GF + k * fl
            for fx in (0.18, 0.5, 0.82): _box(bm, L * fx - 0.9 * FT, L * fx + 0.9 * FT, y0, y0 + 0.4, z, z + fl)
        mesh_from_bm(bm, "B527_FINS_" + name, "PJ_CONCRETE_DK")
    bm = bmesh.new(); _box(bm, 0, L, garden0, garden1, GF, GF + 2.0 * FT); mesh_from_bm(bm, "B527_GARDEN", "PJ_HLDECK")
    return "building: front {:.1f} ft, depth {:.1f} ft, roof {:.0f} ft, retail {:.1f}-{:.1f} ft from the west corner".format(L / FT, Dp / FT, ROOF / FT, RETAIL_X0 / FT, RETAIL_X1 / FT)

def cam(name, loc, target, lens=24, ortho=None):
    c = bpy.data.objects.get(name)
    if not c:
        c = bpy.data.objects.new(name, bpy.data.cameras.new(name)); bpy.context.scene.collection.objects.link(c)
    c.location = loc; c.data.lens = lens; c.data.clip_end = 3000
    if ortho: c.data.type = 'ORTHO'; c.data.ortho_scale = ortho
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return c
def stage_cameras():
    sc = bpy.context.scene
    if not bpy.data.objects.get("SUN"):
        bpy.ops.object.light_add(type='SUN', location=(0, 0, 300)); s = bpy.context.active_object; s.name = "SUN"; s.data.energy = 3.0
        az, el = math.radians(165), math.radians(38)                 # 27th St front faces SSE: late-morning sun square on it
        toward = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))); s.rotation_euler = (-toward).to_track_quat('-Z', 'Y').to_euler()
    w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg: bg.inputs[0].default_value = (0.08, 0.075, 0.07, 1); bg.inputs[1].default_value = 1.0
    for name, loc, rot, ortho in (("CAM_PLAN", (0, 0, 600), (0, 0, math.radians(29)), 560), ("CAM_WIDE", (0, 0, 600), (0, 0, math.radians(29)), 900)):
        c = bpy.data.objects.get(name)
        if not c:
            cd = bpy.data.cameras.new(name); c = bpy.data.objects.new(name, cd); sc.collection.objects.link(c)
        c.location = loc; c.rotation_euler = rot; c.data.type = 'ORTHO'; c.data.ortho_scale = ortho; c.data.clip_end = 2000
    axon = bpy.data.objects.get("CAM_AXON")
    if not axon:
        cd = bpy.data.cameras.new("CAM_AXON"); axon = bpy.data.objects.new("CAM_AXON", cd); sc.collection.objects.link(axon)
    axon.location = (-260, -420, 420); axon.rotation_euler = (math.radians(50), 0, math.radians(-29)); axon.data.type = 'ORTHO'; axon.data.ortho_scale = 700; axon.data.clip_end = 3000
    # street-level 24 mm cameras in the building's own frame (x east along 27th, y north, metres)
    mid = (GLASS[0] + GLASS[1]) / 2; L = _frame()[3]
    cam("CAM_527_front", _world(mid - 1.0, -17.0, 1.65), _world(mid - 1.0, 0.0, 3.2))                 # across 27th, square on the glass (PJ's photo)
    cam("CAM_527_door", _world(GLASS[1] + 6.0, -5.5, 1.6), _world(GLASS[0] + 4.0, 0.0, 2.2))          # sidewalk east of the glass, looking west along it
    cam("CAM_527_down_27th", _world(L + 45.0, -9.5, 1.65), _world(L * 0.4, -6.0, 6.0))               # from the 10th Ave end, looking west along the block
    # High Line camera: where the deck crosses the W 27th roadway (sample the centreline, keep the samples inside the park outline)
    def inside(pt, ring):
        x, y = pt; c = False; n = len(ring)
        for i in range(n):
            (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % n]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1: c = not c
        return c
    hl_rings = [[proj(a, b) for a, b in ring] for f in load("highline_parks") for ring in rings(f["geometry"])]
    samples = []
    for f in load("centerline"):
        if (f["properties"].get("stname_label") or "").strip().upper() != "W 27 ST": continue
        g = f["geometry"]; parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for part in parts:
            pts = [proj(a, b) for a, b in part]
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]; n = max(2, int(math.dist(a, b)))
                for k in range(n + 1):
                    q = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                    if math.hypot(*q) < 250 and any(inside(q, r) for r in hl_rings): samples.append(q)
    hx = sum(q[0] for q in samples) / len(samples) if samples else 49.5; hy = sum(q[1] for q in samples) / len(samples) if samples else -20.0
    sx, sy, _ = _world(L * 0.6, 0.0, 0.0)
    cam("CAM_527_highline", (hx, hy, HL_DECK + 1.6), (sx, sy, 9.0)); print("highline cam", round(hx, 1), round(hy, 1), len(samples), "samples", flush=True)
    cam("CAM_527_axon_close", _world(mid + 60.0, -95.0, 70.0), _world(mid, 15.0, 8.0), lens=35)
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'):
        if eng in engines:
            try: sc.render.engine = eng; break
            except TypeError: continue
    sc.render.resolution_x = 1800; sc.render.resolution_y = 1200; sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 90
    vs = sc.view_settings; looks = [i.identifier for i in type(vs).bl_rna.properties['view_transform'].enum_items]
    for vt in ('AgX', 'Filmic', 'Standard'):
        if vt in looks:
            try: vs.view_transform = vt; break
            except TypeError: continue
    return "cameras: plan, wide, axon, front, door, down_27th, highline, axon_close; engine " + sc.render.engine

def street_look(on):
    """Street renders: overcast sky fill + exposure so the shaded faces read. Map renders keep the dark dossier look."""
    sc = bpy.context.scene; w = sc.world; bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg: bg.inputs[0].default_value = (0.55, 0.56, 0.58, 1) if on else (0.08, 0.075, 0.07, 1); bg.inputs[1].default_value = 2.6 if on else 1.0
    sc.view_settings.exposure = 0.7 if on else 0.0
    sun = bpy.data.objects.get("SUN")
    if sun: sun.data.energy = 4.5 if on else 3.0
def render(cam_name, filename):
    sc = bpy.context.scene; sc.camera = bpy.data.objects[cam_name]; os.makedirs(os.path.join(OUT_DIR, "frames"), exist_ok=True)
    street_look(cam_name.startswith("CAM_527_"))
    sc.render.filepath = os.path.join(OUT_DIR, "frames", filename)
    bpy.ops.render.render(write_still=True); return "rendered " + sc.render.filepath

def export_glb(filename="west_27th_527.glb"):
    for o in bpy.data.objects: o.select_set(False)
    names = ["CHELSEA_MASSING", "SITE_527", "ROADBED", "SIDEWALK", "MEDIAN", "GROUND", "TREES", "HIGH_LINE", "HIGH_LINE_DECK"] + [o.name for o in bpy.data.objects if o.name.startswith("ST_") or o.name.startswith("B527_")]
    for n in names:
        o = bpy.data.objects.get(n)
        if o: o.select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects["CHELSEA_MASSING"]
    path = os.path.join(OUT_DIR, "assets", filename); os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_apply=True, export_cameras=False, export_lights=False, export_yup=True)
    return "exported {} {:.0f} KB".format(path, os.path.getsize(path) / 1024)

def site_center():
    ob = bpy.data.objects.get("SITE_527")
    if not ob or not ob.data.vertices: return None
    xs = [v.co.x for v in ob.data.vertices]; ys = [v.co.y for v in ob.data.vertices]
    return [round(sum(xs)/len(xs), 1), 0, round(-sum(ys)/len(ys), 1)]

if __name__ == "__main__" or bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    log = []
    for fn in (stage_massing, stage_flat, stage_labels, stage_trees, stage_ground, stage_highline, stage_building, stage_cameras):
        log.append(fn()); print(log[-1], flush=True)
    pts = {"site": site_center(), "hudson_yards_7": [round(v, 1) for v in proj(-74.00219, 40.75545)], "st23_ce": [round(v, 1) for v in proj(-73.99814, 40.74575)],
           "highline_28": [round(v, 1) for v in proj(-74.00285, 40.75130)], "highline_26": [round(v, 1) for v in proj(-74.00415, 40.74985)]}
    json.dump(pts, open(os.path.join(OUT_DIR, "data", "model_points.json"), "w")); print("points", pts, flush=True)
    for c, fn in (("CAM_PLAN", "map_plan.jpg"), ("CAM_AXON", "map_axon.jpg"), ("CAM_WIDE", "map_wide.jpg"), ("CAM_527_front", "CAM_527_front.jpg"), ("CAM_527_door", "CAM_527_door.jpg"), ("CAM_527_down_27th", "CAM_527_down_27th.jpg"), ("CAM_527_highline", "CAM_527_highline.jpg"), ("CAM_527_axon_close", "CAM_527_axon_close.jpg")):
        try: print(render(c, fn), flush=True)
        except Exception as e: print("render failed", c, e, flush=True)
    try: print(export_glb(), flush=True)
    except Exception as e: print("export failed", e, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "build", "west_27th_527.blend"))
    print("BUILD DONE", flush=True)
