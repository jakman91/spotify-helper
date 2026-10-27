#!/usr/bin/env python3
"""Render the listening dashboard as one HTML file that opens in any browser.

    python3 render_dashboard.py <data_dir> <out.html> [--name Sam]

data_dir is the output of build_datasets.py. The datasets, fonts and the
charting library (d3 7.9.0, ISC license) are inlined, so the file works
offline. Genre and Mood tabs appear only when build_datasets.py
was run with --track-genres / --track-moods.
"""

import argparse
import json
import os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")
DATASETS = ["summary", "yearly", "monthly", "clock", "tracks", "artists", "albums",
            "genre_years", "genre_months", "moods"]

# Stands in for the claude.ai Dashboard runtime the page was first written for.
SHIM = """<script>
window.SPOTIFY_OWNER = %(owner)s;
window.dash = (() => {
  const D = %(data)s;
  if (!D.genre_years) {
    D.genre_years = []; D.genre_months = [];
    for (const s of ['#tab-genres', '#sp-genre', 'label[for=sp-genre]']) document.querySelector(s).hidden = true;
  }
  if (!D.moods) for (const s of ['#tab-moods', '#sp-mood', 'label[for=sp-mood]']) document.querySelector(s).hidden = true;
  let params = {};
  const subs = [];
  return {
    data: (id) => (id in D ? { status: 'ok', data: D[id] } : { status: 'missing', data: [] }),
    params: () => params,
    setParams: (p) => {
      params = { ...params };
      for (const [k, v] of Object.entries(p)) { if (v == null) delete params[k]; else params[k] = v; }
      subs.forEach((f) => f());
    },
    setLink: () => {},
    onData: (f) => { subs.push(f); setTimeout(f); },
  };
})();
</script>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("out")
    ap.add_argument("--name", help="whose dashboard, for the title (default: Your)")
    a = ap.parse_args()

    data = {}
    for d in DATASETS:
        p = os.path.join(a.data_dir, d + ".json")
        if os.path.exists(p):
            data[d] = json.load(open(p, encoding="utf-8"))
    missing = [d for d in ("summary", "yearly", "tracks", "artists") if d not in data]
    if missing:
        raise SystemExit(f"Missing {missing} in {a.data_dir}. Run build_datasets.py first.")

    owner = f"{a.name}'s" if a.name else "Your"
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    page = page.replace("<!--SHIM-->", SHIM % {"owner": json.dumps(owner), "data": blob}, 1)
    page = page.replace(">Your Spotify<", f">{owner} Spotify<", 1)
    fonts = open(os.path.join(HERE, "fonts.css"), encoding="utf-8").read()
    d3 = open(os.path.join(HERE, "d3.v7.9.0.min.js"), encoding="utf-8").read()
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{owner} Spotify</title>
<style>{fonts}
body {{ margin: 0; background: #FFFFFF; }}
</style>
<script>{d3}</script>
</head>
<body>
{page}
</body>
</html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(html)
    print(f"{a.out} ({len(html) / 1e6:.1f} MB). Tabs: genres {'on' if 'genre_years' in data else 'off'}, "
          f"moods {'on' if 'moods' in data else 'off'}")


if __name__ == "__main__":
    main()
