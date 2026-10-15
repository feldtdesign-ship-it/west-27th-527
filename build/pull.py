"""
pull.py — 527 West 27th Street data pulls. Same method as the East Village and Nostrand builds.
Each pull writes data/<name>.json and is skipped if the file already exists (>2 bytes), so it can be rerun.
Progress goes to data/pull.log. Run: python3 build/pull.py [names...]
"""
import json, os, sys, math, time, io, zipfile, csv, urllib.request, urllib.parse, datetime, collections
S = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(S)
D = os.path.join(R, 'data'); os.makedirs(D, exist_ok=True); os.makedirs(os.path.join(R, 'frames', 'ring'), exist_ok=True)
LAT, LON = 40.751109, -74.003437
CX = ('471', '165', '164')   # 34 St-Hudson Yards 7 543 m, 23 St C E 733 m, 34 St-Penn A C E 857 m
LOG = open(os.path.join(D, 'pull.log'), 'a')
def log(*a):
    s = f"{datetime.datetime.now():%H:%M:%S} " + ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
def dist(lat, lon): return math.hypot((lon - LON) * 111320 * math.cos(math.radians(LAT)), (lat - LAT) * 110540)
def get(url, timeout=590, binary=False, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (west-27th-527 dossier)'})
            with urllib.request.urlopen(req, timeout=timeout) as r: b = r.read()
            return b if binary else json.loads(b)
        except Exception as e:
            if 'CERTIFICATE' in str(e):   # macOS python lacks the CA bundle; curl has it
                import subprocess
                b = subprocess.run(['curl', '-s', '--max-time', str(timeout), '-A', 'Mozilla/5.0 (west-27th-527 dossier)', url], capture_output=True).stdout
                if b:
                    try: return b if binary else json.loads(b)
                    except Exception as e2: log('  curl parse fail', str(e2)[:80]); return None
            log('  retry', i + 1, type(e).__name__, str(e)[:120], url[:140]); time.sleep(5 * (i + 1))
    return None
def soda(host, ds, **q):
    return get(f"https://{host}/resource/{ds}.json?" + urllib.parse.urlencode({('$' + k): v for k, v in q.items()}))
def out(name): return os.path.join(D, name + '.json')
def have(name): p = out(name); return os.path.exists(p) and os.path.getsize(p) > 2
def save(name, obj):
    json.dump(obj, open(out(name), 'w')); log('saved', name, len(obj) if hasattr(obj, '__len__') else '')

# ---------- MTA subway: the four complexes inside 460 m ----------
def mta_hourly():   # hour x weekday, summer 2026
    for cx in CX:
        if have(f'mta_hourly_{cx}'): continue
        r = soda('data.ny.gov', '5wq4-mkjj', select='date_extract_dow(transit_timestamp) as dow,date_extract_hh(transit_timestamp) as hr,sum(ridership) as riders',
                 where=f"station_complex_id='{cx}' and transit_timestamp between '2026-06-01T00:00:00' and '2026-08-31T23:59:59'", group='dow,hr', limit=500)
        if r: save(f'mta_hourly_{cx}', r)
def mta_daily():    # daily since 2025-01-01
    for cx in CX:
        if have(f'mta_daily_{cx}'): continue
        rows = []
        for a, b in (('2025-01-01', '2025-06-30'), ('2025-07-01', '2025-12-31'), ('2026-01-01', '2026-09-30')):
            r = soda('data.ny.gov', '5wq4-mkjj', select='date_trunc_ymd(transit_timestamp) as day,sum(ridership) as riders',
                     where=f"station_complex_id='{cx}' and transit_timestamp between '{a}T00:00:00' and '{b}T23:59:59'", group='day', order='day', limit=1000)
            if r: rows += r; log('  daily', cx, a, len(r))
        if rows: save(f'mta_daily_{cx}', rows)
def mta_hist():     # monthly 2020-2024 (wujg-7c2s) + 2025 on (5wq4-mkjj)
    for cx in CX:
        if have(f'mta_hist_{cx}'): continue
        rows = []
        for y in range(2020, 2025):
            r = soda('data.ny.gov', 'wujg-7c2s', select='date_trunc_ym(transit_timestamp) as month,sum(ridership) as riders',
                     where=f"station_complex_id='{cx}' and transit_timestamp between '{y}-01-01T00:00:00' and '{y}-12-31T23:59:59'", group='month', order='month', limit=20)
            if r: rows += r; log('  hist', cx, y, len(r))
        r = soda('data.ny.gov', '5wq4-mkjj', select='date_trunc_ym(transit_timestamp) as month,sum(ridership) as riders',
                 where=f"station_complex_id='{cx}' and transit_timestamp >= '2025-01-01T00:00:00'", group='month', order='month', limit=40)
        if r: rows += r; log('  hist', cx, '2025+', len(r))
        if rows: save(f'mta_hist_{cx}', rows)
def mta_fare():
    for cx in CX:
        if have(f'fare_{cx}'): continue
        r = soda('data.ny.gov', '5wq4-mkjj', select='fare_class_category,sum(ridership) as riders',
                 where=f"station_complex_id='{cx}' and transit_timestamp between '2026-06-01T00:00:00' and '2026-08-31T23:59:59'", group='fare_class_category', limit=50)
        if r: save(f'fare_{cx}', r)

# ---------- buses: Manhattan GTFS, then stop-level counts ----------
def gtfs_stops():
    if have('bus_stops_near'): return
    b = get('https://rrgtfsfeeds.s3.amazonaws.com/gtfs_m.zip', binary=True)
    if not b: return
    z = zipfile.ZipFile(io.BytesIO(b)); log('  gtfs', z.namelist())
    stops = {}
    for r in csv.DictReader(io.TextIOWrapper(z.open('stops.txt'), 'utf-8-sig')):
        d = dist(float(r['stop_lat']), float(r['stop_lon']))
        if d <= 450: stops[r['stop_id']] = {'stop_id': r['stop_id'], 'name': r['stop_name'], 'lat': float(r['stop_lat']), 'lon': float(r['stop_lon']), 'd': round(d), 'routes': set()}
    trips = {r['trip_id']: r['route_id'] for r in csv.DictReader(io.TextIOWrapper(z.open('trips.txt'), 'utf-8-sig'))}
    for r in csv.DictReader(io.TextIOWrapper(z.open('stop_times.txt'), 'utf-8-sig')):
        if r['stop_id'] in stops: stops[r['stop_id']]['routes'].add(trips.get(r['trip_id'], '?'))
    rows = sorted([{**s, 'routes': sorted(s['routes'])} for s in stops.values()], key=lambda s: s['d'])
    save('bus_stops_near', rows)
def bus_counts():
    stops = json.load(open(out('bus_stops_near'))) if have('bus_stops_near') else []
    ids = [s['stop_id'] for s in stops if s['d'] <= 300]
    if not ids: log('  no bus stops'); return
    log('  bus stops', ids)
    inlist = ','.join(f"'{i}'" for i in ids)
    if not have('bus_raw'):
        rows = []
        for m in ('06', '07', '08'):
            r = soda('data.ny.gov', 'fvdm-uavx', select='date,hour,stop_id,route_id,boardings,alightings', where=f"stop_id in({inlist}) and date between '2026-{m}-01T00:00:00' and '2026-{m}-31T23:59:59'", limit=200000)
            if r: rows += r; log('  bus raw', m, len(r))
        if rows: save('bus_raw', rows)
    if not have('bus_monthly'):
        rows = []
        for sid in ids:
            r = soda('data.ny.gov', 'fvdm-uavx', select='stop_id,route_id,date_trunc_ym(date) as month,sum(boardings) as b,sum(alightings) as a', where=f"stop_id='{sid}' and date >= '2024-09-01T00:00:00'", group='stop_id,route_id,month', limit=5000)
            if r: rows += r; log('  bus monthly', sid, len(r))
        if rows: save('bus_monthly', rows)

# ---------- DOT cameras ----------
def cameras():
    if have('cameras'): return
    cams = get('https://webcams.nyctmc.org/api/cameras')
    if not cams: return
    near = sorted([{'id': c['id'], 'name': c['name'], 'lat': c['latitude'], 'lon': c['longitude'], 'online': c.get('isOnline'), 'dist': round(dist(c['latitude'], c['longitude']))} for c in cams], key=lambda c: c['dist'])[:10]
    stamp = datetime.datetime.now().strftime('%a %-d %b %Y, %-I:%M %p').replace('AM', 'am').replace('PM', 'pm')
    for c in near:
        b = get(f"https://webcams.nyctmc.org/api/cameras/{c['id']}/image", binary=True, timeout=60, tries=2)
        c['file'] = f"frames/ring/{c['id']}.jpg"; c['t'] = stamp
        if b: open(os.path.join(R, c['file']), 'wb').write(b); c['bytes'] = len(b)
        log('  cam', c['dist'], c['name'], len(b) if b else 0)
    save('cameras', near)

# ---------- DOT automated traffic volume counts ----------
def atr():
    if have('atr'): return
    rows = []
    for st in ('WEST 27', 'WEST 28', 'WEST 26', 'WEST 29', '10 AVENUE', '11 AVENUE', 'TENTH', 'ELEVENTH'):
        r = soda('data.cityofnewyork.us', '7ym2-wayt', where=f"(upper(street)='{st} STREET' or upper(street)='{st} ST' or upper(street)='{st}') and boro='Manhattan'", limit=500000)
        if r: rows += r; log('  atr', st, len(r))
    if rows: save('atr', rows)

# ---------- footprints, planimetric, trees ----------
def geo(name, ds, radius, fields=None):
    if have(name): return
    q = {'where': f"within_circle(the_geom,{LAT},{LON},{radius})", 'limit': 50000}
    if fields: q['select'] = fields
    r = soda('data.cityofnewyork.us', ds, **q)
    if r is not None: save(name, r)
def footprints(): geo('footprints', '5zhs-2jue', 420, 'bin,base_bbl,height_roof,construction_year,ground_elevation,the_geom')
def planimetric():
    geo('sidewalk', '52n9-sdep', 420); geo('roadbed', 'i36f-5ih7', 420); geo('median', 'ees7-4ufv', 420); geo('centerline', 'inkn-q76z', 420, 'stname_label,street_name,streetwidth,the_geom')
def trees():
    if have('trees'): return
    r = soda('data.cityofnewyork.us', 'uvpi-gqnh', select='latitude,longitude,spc_common,tree_dbh,status', where=f"within_circle(location,{LAT},{LON},420)", limit=20000)
    if r is None:
        r = soda('data.cityofnewyork.us', 'uvpi-gqnh', select='latitude,longitude,spc_common,tree_dbh,status', where=f"latitude between {LAT-0.004} and {LAT+0.004} and longitude between {LON-0.005} and {LON+0.005}", limit=20000)
    if r is not None: save('trees', r)
    if not have('trees_new'):
        r = soda('data.cityofnewyork.us', 'hn5i-inap', select='dbh,tpstructure,tpcondition,genusspecies,location', where=f"within_circle(location,{LAT},{LON},420)", limit=20000)
        if r is not None: save('trees_new', r)

# ---------- weather, citi bike, ACRIS ----------
def weather():
    if have('weather'): return
    end = datetime.date.today() - datetime.timedelta(days=2)
    r = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={LAT}&longitude={LON}&start_date=2020-01-01&end_date={end}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum&temperature_unit=fahrenheit&precipitation_unit=inch&timezone=America/New_York")
    if r: save('weather', r)
def citibike():
    if have('citibike'): return
    r = get('https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_information.json')
    if not r: return
    near = sorted([{'id': s['station_id'], 'name': s['name'], 'lat': s['lat'], 'lon': s['lon'], 'capacity': s.get('capacity'), 'dist': round(dist(s['lat'], s['lon']))} for s in r['data']['stations'] if dist(s['lat'], s['lon']) <= 320], key=lambda s: s['dist'])
    save('citibike', near)
def acris():
    if have('acris_master'): return
    legals = json.load(open(os.path.join(D, 'raw', 'acris_legals.json')))
    ids = sorted({l['document_id'] for l in legals}); inlist = ','.join(f"'{i}'" for i in ids)
    m = soda('data.cityofnewyork.us', 'bnx9-e6tj', where=f"document_id in({inlist})", limit=1000)
    p = soda('data.cityofnewyork.us', '636b-3b5g', where=f"document_id in({inlist})", limit=1000)
    if m is not None: save('acris_master', m)
    if p is not None: save('acris_parties', p)
ALL = [weather, citibike, acris, cameras, footprints, planimetric, trees, gtfs_stops, bus_counts, atr, mta_hourly, mta_fare, mta_hist, mta_daily]
if __name__ == '__main__':
    names = sys.argv[1:]
    for f in ALL:
        if names and f.__name__ not in names: continue
        log('==', f.__name__); t = time.time()
        try: f()
        except Exception as e: log('  FAILED', f.__name__, type(e).__name__, str(e)[:200])
        log('   ', f.__name__, 'done in', round(time.time() - t), 's')
    log('ALL DONE')
