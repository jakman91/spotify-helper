#!/usr/bin/env python3
"""Aggregate a Spotify Extended Streaming History export into dashboard datasets.

Usage: python3 build_datasets.py <export_dir> <out_dir> [--tz America/Chicago]
(--tz defaults to this computer's time zone)

A "play" is a music stream of 30s or more (Spotify's own stream threshold).
A "skip" is any start that ended under 30s or that Spotify flagged as skipped.
"""
import argparse, collections, csv, glob, json, os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def local_tz():
    """IANA name of this computer's zone (macOS and Linux keep it in /etc/localtime)."""
    if os.environ.get('TZ'):
        return os.environ['TZ']
    path = os.path.realpath('/etc/localtime')
    return path.split('zoneinfo/', 1)[1] if 'zoneinfo/' in path else 'UTC'


ap = argparse.ArgumentParser()
ap.add_argument('export_dir'); ap.add_argument('out_dir')
ap.add_argument('--tz', default=local_tz(), help='local time zone for the listening clock')
ap.add_argument('--min-track-plays', type=int, default=3)
ap.add_argument('--min-plays', type=int, default=5, help='floor for artists and albums')
ap.add_argument('--track-moods', help='optional JSON {tracks: {track_uri: {src, val, ene, tem, aco, ins, dan, moods[]}}}')
ap.add_argument('--track-genres', help='optional JSON {track_uri: {"genre": name}} keyed by the deduped track id')
a = ap.parse_args()
tz = ZoneInfo(a.tz)
os.makedirs(a.out_dir, exist_ok=True)

rows = []
for f in sorted(glob.glob(os.path.join(a.export_dir, '**', 'Streaming_History_Audio_*.json'), recursive=True)):
    with open(f, encoding='utf-8') as fh:
        rows += json.load(fh)
music = [r for r in rows if r.get('spotify_track_uri') and r.get('master_metadata_track_name')]
music.sort(key=lambda r: r['ts'])
years = sorted({int(r['ts'][:4]) for r in music})

uri_key = {}
def key(r):
    # one song per URI (Spotify sometimes retitles a URI), then merge different URIs by title + artist
    return uri_key.setdefault(r['spotify_track_uri'], _name_key(r))

def _name_key(r):
    return (r['master_metadata_track_name'].strip().lower(), r['master_metadata_album_artist_name'].strip().lower())

def new_agg():
    return {'plays': 0, 'ms': 0, 'starts': 0, 'skips': 0, 'done': 0, 'first': None, 'last': None,
            'yp': collections.Counter(), 'ym': collections.Counter(), 'uris': collections.Counter()}

T, AR, AL = collections.defaultdict(new_agg), collections.defaultdict(new_agg), collections.defaultdict(new_agg)
T_meta, AL_meta = {}, {}
yearly = collections.defaultdict(lambda: {'ms': 0, 'plays': 0, 'starts': 0, 'skips': 0, 'shuffle': 0,
                                          'tracks': set(), 'artists': set(), 'ac': collections.Counter()})
monthly = collections.defaultdict(lambda: {'ms': 0, 'plays': 0})
clock = collections.Counter()
artist_first_year = {}

for r in music:
    y = int(r['ts'][:4]); ms = r['ms_played'] or 0
    full = ms >= 30000
    skip = (not full) or bool(r.get('skipped'))
    k = key(r); art = r['master_metadata_album_artist_name']; alb = r['master_metadata_album_album_name'] or ''
    T_meta.setdefault(k, (r['master_metadata_track_name'], art))
    AL_meta.setdefault((alb.lower(), art.lower()), (alb, art))
    for agg, kk in ((T, k), (AR, art), (AL, (alb.lower(), art.lower()))):
        g = agg[kk]
        g['starts'] += 1; g['ms'] += ms; g['ym'][y] += ms
        if skip: g['skips'] += 1
        if r.get('reason_end') == 'trackdone': g['done'] += 1
        if full:
            g['plays'] += 1; g['yp'][y] += 1
            g['first'] = g['first'] or r['ts'][:10]; g['last'] = r['ts'][:10]
    if full:
        T[k]['uris'][r['spotify_track_uri']] += 1
        T[k].setdefault('albums', collections.Counter())[alb] += 1
    Y = yearly[y]; Y['ms'] += ms; Y['starts'] += 1
    if skip: Y['skips'] += 1
    if r.get('shuffle'): Y['shuffle'] += 1
    if full:
        Y['plays'] += 1; Y['tracks'].add(k); Y['artists'].add(art); Y['ac'][art] += 1
        artist_first_year.setdefault(art, y)
    T[k].setdefault('mm', collections.Counter())[r['ts'][:7]] += ms
    if full: T[k].setdefault('mp', collections.Counter())[r['ts'][:7]] += 1
    m = monthly[r['ts'][:7]]; m['ms'] += ms
    if full: m['plays'] += 1
    lt = datetime.strptime(r['ts'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz)
    clock[(lt.strftime('%a'), lt.hour)] += ms

def mins(ms): return round(ms / 60000, 1)
def peak(g): return g['yp'].most_common(1)[0][0] if g['yp'] else None
def ycols(g, prefix='y'): return {f'{prefix}{y}': g['yp'].get(y, 0) for y in years}

tracks = []
for k, g in T.items():
    if g['plays'] < 1: continue
    name, art = T_meta[k]
    tracks.append({'id': g['uris'].most_common(1)[0][0], 'track': name, 'artist': art,
                   'album': g['albums'].most_common(1)[0][0], 'plays': g['plays'], 'minutes': mins(g['ms']),
                   'starts': g['starts'], 'skip_rate': round(g['skips'] / g['starts'], 3),
                   'completion_rate': round(g['done'] / g['starts'], 3),
                   'first': g['first'], 'last': g['last'], 'peak_year': peak(g), 'years_active': len(g['yp']),
                   'other_uris': '|'.join(u for u, _ in g['uris'].most_common()[1:]), **ycols(g)})
tracks.sort(key=lambda t: -t['plays'])

genre_years, genre_months = [], []
if a.track_genres:
    with open(a.track_genres, encoding='utf-8') as fh:
        tg = {u: (v.get('genre') if isinstance(v, dict) else v) or 'Unsorted' for u, v in json.load(fh).items()}
    gy, gm = collections.defaultdict(lambda: [0, 0]), collections.defaultdict(lambda: [0, 0])
    art_g = collections.defaultdict(collections.Counter)
    by_id = {g['uris'].most_common(1)[0][0]: g for g in T.values() if g['plays'] >= 1}
    for t in tracks:
        gname = tg.get(t['id'], 'Unsorted'); t['genre'] = gname
        g = by_id[t['id']]
        art_g[t['artist']][gname] += t['plays']
        for y in years:
            if g['ym'].get(y) or g['yp'].get(y):
                gy[(gname, y)][0] += g['yp'].get(y, 0); gy[(gname, y)][1] += g['ym'].get(y, 0)
        for mo, v in g.get('mm', {}).items():
            gm[(gname, mo)][1] += v; gm[(gname, mo)][0] += g.get('mp', {}).get(mo, 0)
    genre_years = [{'genre': gn, 'year': y, 'plays': v[0], 'hours': round(v[1] / 3.6e6, 2)} for (gn, y), v in sorted(gy.items())]
    genre_months = [{'genre': gn, 'month': mo, 'plays': v[0], 'hours': round(v[1] / 3.6e6, 2)} for (gn, mo), v in sorted(gm.items())]

artists = []
for art, g in AR.items():
    if g['plays'] < 1: continue
    artists.append({'artist': art, 'plays': g['plays'], 'minutes': mins(g['ms']),
                    'tracks': sum(1 for t in tracks if t['artist'] == art) if False else None,
                    'skip_rate': round(g['skips'] / g['starts'], 3), 'first': g['first'], 'last': g['last'],
                    'peak_year': peak(g), 'years_active': len(g['yp']), **ycols(g),
                    **{f'm{y}': mins(g['ym'].get(y, 0)) for y in years}})
tc = collections.Counter(t['artist'] for t in tracks)
for x in artists:
    x['tracks'] = tc[x['artist']]
    if a.track_genres: x['genre'] = art_g[x['artist']].most_common(1)[0][0] if art_g[x['artist']] else 'Unsorted'
artists.sort(key=lambda x: -x['plays'])

albums = []
for kk, g in AL.items():
    if g['plays'] < a.min_plays: continue
    alb, art = AL_meta[kk]
    albums.append({'id': f'{art} — {alb}', 'album': alb, 'artist': art, 'plays': g['plays'], 'minutes': mins(g['ms']),
                   'first': g['first'], 'last': g['last'], 'peak_year': peak(g), **ycols(g)})
albums.sort(key=lambda x: -x['plays'])
if a.track_genres:
    alb_g = collections.defaultdict(collections.Counter)
    for t in tracks: alb_g[(t['album'], t['artist'])][t['genre']] += t['plays']
    for x in albums:
        c = alb_g.get((x['album'], x['artist'])) or art_g[x['artist']]
        x['genre'] = c.most_common(1)[0][0] if c else 'Unsorted'

yearly_rows = []
seen = set()
for y in years:
    Y = yearly[y]
    new = sum(1 for art in Y['artists'] if artist_first_year.get(art) == y)
    yearly_rows.append({'year': y, 'hours': round(Y['ms'] / 3.6e6, 1), 'plays': Y['plays'],
                        'unique_tracks': len(Y['tracks']), 'unique_artists': len(Y['artists']), 'new_artists': new,
                        'skip_rate': round(Y['skips'] / Y['starts'], 3), 'shuffle_share': round(Y['shuffle'] / Y['starts'], 3),
                        'top_artist': Y['ac'].most_common(1)[0][0] if Y['ac'] else ''})
monthly_rows = [{'month': m, 'hours': round(v['ms'] / 3.6e6, 2), 'plays': v['plays']} for m, v in sorted(monthly.items())]
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
clock_rows = [{'day': d, 'hour': h, 'hours': round(clock[(d, h)] / 3.6e6, 1)} for d in days for h in range(24)]
total_ms = sum(r['ms_played'] or 0 for r in music)
summary = [{'first_played': music[0]['ts'][:10], 'last_played': music[-1]['ts'][:10],
            'hours': round(total_ms / 3.6e6), 'plays': sum(t['plays'] for t in tracks),
            'starts': len(music), 'unique_tracks': len(tracks), 'unique_artists': len(artists),
            'skip_rate': round(sum(1 for r in music if (r['ms_played'] or 0) < 30000 or r.get('skipped')) / len(music), 3),
            'podcast_streams': sum(1 for r in rows if r.get('spotify_episode_uri')),
            'timezone': a.tz}]

def dump(name, data):
    with open(os.path.join(a.out_dir, name + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))

dump('summary', summary); dump('yearly', yearly_rows); dump('monthly', monthly_rows); dump('clock', clock_rows)
dump('tracks', [t for t in tracks if t['plays'] >= a.min_track_plays])
dump('artists', [x for x in artists if x['plays'] >= a.min_plays])
dump('albums', albums)
if a.track_genres: dump('genre_years', genre_years); dump('genre_months', genre_months)
if a.track_moods:
    with open(a.track_moods, encoding='utf-8') as fh:
        tm = json.load(fh)['tracks']
    dump('moods', [{'id': u, 'valence': v['val'], 'energy': v['ene'], 'tempo': v['tem'], 'acousticness': v['aco'],
                    'instrumentalness': v['ins'], 'danceability': v['dan'], 'source': v['src'],
                    'moods': '|'.join(v.get('moods') or [])} for u, v in tm.items()])
# Full tables for the library and playlist steps
dump('tracks_all', tracks); dump('artists_all', artists)
with open(os.path.join(a.out_dir, 'tracks_all.csv'), 'w', newline='', encoding='utf-8') as fh:
    cols = [c for c in tracks[0] if not c.startswith('y')] if tracks else []
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(tracks)
print(json.dumps(summary[0]), len(tracks), len(artists), len(albums))
