"""
pull_raw.py — 527 West 27th Street, the building's own record. Writes data/raw/<name>.json, skips what is already there.
Run: python3 build/pull_raw.py [names...]
"""
import json, os, sys, math, time, urllib.request, urllib.parse, subprocess, datetime
S = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(S)
D = os.path.join(R, 'data', 'raw'); os.makedirs(D, exist_ok=True)
LAT, LON = 40.751109, -74.003437
BBL, BIN, BLOCK, LOT = '1006997504', '1090205', '00699', '7504'
UA = 'Mozilla/5.0 (west-27th-527 dossier)'
LOG = open(os.path.join(R, 'data', 'pull.log'), 'a')
def log(*a):
    s = f"{datetime.datetime.now():%H:%M:%S} " + ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
def get(url, timeout=120, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
        except Exception as e:
            if 'CERTIFICATE' in str(e):
                b = subprocess.run(['curl', '-s', '--max-time', str(timeout), '-A', UA, url], capture_output=True).stdout
                if b:
                    try: return json.loads(b)
                    except Exception: pass
            body = ''
            try: body = e.read().decode()[:200]
            except Exception: pass
            log('  retry', i + 1, type(e).__name__, str(e)[:100], body, url[:150]); time.sleep(3 * (i + 1))
    return None
def soda(host, ds, **q):
    return get(f"https://{host}/resource/{ds}.json?" + urllib.parse.urlencode({('$' + k): v for k, v in q.items()}))
NYC = 'data.cityofnewyork.us'
def out(n): return os.path.join(D, n + '.json')
def have(n): return os.path.exists(out(n)) and os.path.getsize(out(n)) > 2
def save(n, obj):
    if obj is None: log('  NOTHING for', n); return
    json.dump(obj, open(out(n), 'w')); log('saved', n, len(obj))
def pull(n, host, ds, **q):
    if have(n): return
    q.setdefault('limit', 50000); save(n, soda(host, ds, **q))

def pluto():
    pull('pluto_site', NYC, '64uk-42ks', where=f"bbl='{BBL}' OR bbl={BBL}")
    pull('pluto_near', NYC, '64uk-42ks', where="borough='MN' and block between 696 and 702")
def registry():
    pull('storefront_registry', NYC, '92iy-9c3n', where=f"bbl='{BBL}'")
    pull('registry_block', NYC, '92iy-9c3n', where=f"within_circle(lat_long,{LAT},{LON},250)")
def curbs(): pull('curbs', NYC, '5xvt-8cbk', where=f"within_circle(the_geom,{LAT},{LON},260)")
def collisions(): pull('collisions', NYC, 'h9gi-nx95', where=f"within_circle(location,{LAT},{LON},150)")
def subway():
    if have('subway_complexes'): return
    r = soda('data.ny.gov', '39hk-dx4f', limit=2000)
    if not r: return
    def d(x): return math.hypot((float(x['gtfs_longitude']) - LON) * 111320 * math.cos(math.radians(LAT)), (float(x['gtfs_latitude']) - LAT) * 110540)
    near = sorted([{**x, 'dist': round(d(x))} for x in r if d(x) <= 900], key=lambda x: x['dist']); save('subway_complexes', near)
def building():
    pull('acris_legals', NYC, '8h5j-fqxa', where=f"borough='1' and block='{int(BLOCK)}' and lot='{int(LOT)}'")
    pull('ecb_violations', NYC, '6bgk-3dad', where=f"bin='{BIN}'")
    pull('dob_violations', NYC, '3h2n-5cm9', where=f"bin='{BIN}'")
    pull('dob_complaints', NYC, 'eabe-havv', where=f"bin='{BIN}'")
    pull('dob_jobs', NYC, 'ic3t-wcy2', where=f"bin__='{BIN}'")
    pull('dob_now_jobs', NYC, 'w9ak-ipjd', where=f"bin='{BIN}'")
    pull('dob_permits', NYC, 'ipu4-2q9a', where=f"bin__='{BIN}'")
    pull('hpd_violations', NYC, 'wvxf-dwi5', where=f"bin='{BIN}'")
    pull('311', NYC, 'erm2-nwe9', where="incident_address='527 WEST 27 STREET' and borough='MANHATTAN'", order='created_date DESC', limit=2000)
def tenants():
    # who has been licensed, inspected or permitted at the address
    pull('businesses', NYC, 'w7w3-xahh', where="upper(address_building)='527' and upper(address_street_name) like 'WEST 27%'")
    pull('restaurants', NYC, '43nn-pn8j', where="building='527' and upper(street) like 'WEST 27%' and boro='Manhattan'")
    pull('sidewalk_cafe', NYC, 'qcdj-rwhu', where="building='527' and upper(street) like 'WEST 27%'")
    pull('liquor_active', 'data.ny.gov', '9s3h-dpkz', where="upper(actualaddressofpremises) like '527 WEST 27%'")
    pull('businesses_bbl', NYC, 'w7w3-xahh', where=f"bbl='{BBL}' or bin='{BIN}'")
    pull('restaurants_bbl', NYC, '43nn-pn8j', where=f"bbl='{BBL}' or bin='{BIN}'")
ALL = [pluto, registry, curbs, collisions, subway, building, tenants]
if __name__ == '__main__':
    names = sys.argv[1:]
    for f in ALL:
        if names and f.__name__ not in names: continue
        log('==', f.__name__)
        try: f()
        except Exception as e: log('  FAILED', f.__name__, type(e).__name__, str(e)[:200])
    log('RAW DONE')
