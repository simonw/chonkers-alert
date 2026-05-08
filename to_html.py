#!/usr/bin/env python3
"""Render a static index.html from iNaturalist Steller sea lion JSON.

Reads JSON from stdin (or a path argv) and writes HTML to stdout. Sightings
are sorted with the most recent first. No JavaScript dependencies — clicking
a thumbnail opens the large photo via a plain anchor.
"""
import datetime
import html
import json
import re
import sys


SIZE_RE = re.compile(r"/square\.(jpe?g|png)(\?.*)?$", re.IGNORECASE)


CSS = """
:root {
  color-scheme: light dark;
  --bg: #f7f7f5;
  --card: #fff;
  --border: #e3e3e0;
  --text: #222;
  --muted: #666;
  --link: #0a58ca;
  --shadow: 0 1px 2px rgba(0,0,0,0.04);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15171a;
    --card: #1f2226;
    --border: #2c3035;
    --text: #e8e8e6;
    --muted: #9aa0a6;
    --link: #6ea8fe;
    --shadow: 0 1px 2px rgba(0,0,0,0.3);
  }
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  margin: 0;
  padding: 1rem;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}
.wrap { max-width: 820px; margin: 0 auto; }
header { margin-bottom: 1.5rem; }
h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
.tagline { color: var(--muted); margin: 0.1rem 0; }
.meta { color: var(--muted); font-size: 0.9rem; margin-top: 0.4rem; }
a { color: var(--link); }
.sighting {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow);
}
.sighting-header { margin-bottom: 0.6rem; }
.sighting-date { font-weight: 600; font-size: 1.05rem; }
.sighting-place { color: var(--muted); font-size: 0.9rem; margin-top: 0.15rem; }
.observer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--muted);
  margin-top: 0.4rem;
}
.observer img {
  width: 24px; height: 24px; border-radius: 50%; object-fit: cover;
  background: var(--border);
}
.description {
  white-space: pre-wrap;
  font-size: 0.95rem;
  margin: 0.6rem 0;
  padding: 0.5rem 0.75rem;
  background: var(--bg);
  border-radius: 4px;
}
.gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0.6rem 0 0.4rem;
}
.gallery a {
  display: block;
  flex: 1 1 160px;
  max-width: 100%;
  height: 200px;
  overflow: hidden;
  border-radius: 4px;
  background: var(--border);
}
.gallery img {
  width: 100%; height: 100%; object-fit: cover; display: block;
}
.attribution {
  font-size: 0.75rem;
  color: var(--muted);
  margin-top: 0.2rem;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.5rem;
  font-size: 0.9rem;
}
.empty {
  text-align: center;
  padding: 2rem;
  color: var(--muted);
}
footer {
  margin: 2rem 0 1rem;
  font-size: 0.85rem;
  color: var(--muted);
  text-align: center;
}
"""


def to_large(url):
    return SIZE_RE.sub(r"/large.\1\2", url) if url else url


def to_medium(url):
    return SIZE_RE.sub(r"/medium.\1\2", url) if url else url


def format_observed(item):
    iso = item.get("time_observed_at")
    if iso:
        try:
            dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%A, %B %-d, %Y at %-I:%M %p %Z").strip()
        except ValueError:
            pass
    details = item.get("observed_on_details") or {}
    if details.get("date"):
        return details["date"]
    return "Unknown date"


def sort_key(item):
    return item.get("time_observed_at") or ""


def render_sighting(item):
    obs_id = item.get("id")
    inat_url = f"https://www.inaturalist.org/observations/{obs_id}"
    place = item.get("place_guess") or "Unknown location"
    when = format_observed(item)

    photos_html = []
    for photo_data in item.get("observation_photos") or []:
        photo = (photo_data or {}).get("photo") or {}
        url = photo.get("url")
        if not url:
            continue
        attribution = photo.get("attribution", "")
        photos_html.append(
            f'<a href="{html.escape(to_large(url))}" target="_blank" rel="noopener" '
            f'title="{html.escape(attribution)}">'
            f'<img src="{html.escape(to_medium(url))}" alt="Sighting photo" loading="lazy"/>'
            f"</a>"
        )

    user = item.get("user") or {}
    user_login = user.get("login") or ""
    user_name = user.get("name") or user_login or "Unknown observer"
    user_icon = user.get("icon_url")

    observer_html = ""
    if user_login:
        icon_html = (
            f'<img src="{html.escape(user_icon)}" alt=""/>' if user_icon else ""
        )
        observer_html = (
            '<div class="observer">'
            f"{icon_html}"
            f'<span>Observed by <a href="https://www.inaturalist.org/people/{html.escape(user_login)}">'
            f"{html.escape(user_name)}</a></span>"
            "</div>"
        )

    description = (item.get("description") or "").strip()
    description_html = (
        f'<div class="description">{html.escape(description)}</div>'
        if description
        else ""
    )

    actions = [f'<a href="{html.escape(inat_url)}">View on iNaturalist</a>']
    geojson = item.get("geojson") or {}
    coords = geojson.get("coordinates")
    if coords and len(coords) >= 2:
        lat, lon = coords[1], coords[0]
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        actions.append(
            f'<a href="{html.escape(maps_url)}" target="_blank" rel="noopener">Open in Google Maps</a>'
        )

    gallery_html = (
        f'<div class="gallery">{"".join(photos_html)}</div>' if photos_html else ""
    )

    return f"""
<article class="sighting">
  <div class="sighting-header">
    <div class="sighting-date">{html.escape(when)}</div>
    <div class="sighting-place">{html.escape(place)}</div>
    {observer_html}
  </div>
  {gallery_html}
  {description_html}
  <div class="actions">{" · ".join(actions)}</div>
</article>
"""


def render(data):
    results = sorted(data.get("results", []), key=sort_key, reverse=True)
    updated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    sightings_html = "\n".join(render_sighting(item) for item in results) or (
        '<div class="empty">No recent sightings in the bounding box yet.</div>'
    )
    count = len(results)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chonkers Alert: Steller sea lion sightings near Pier 39</title>
<link rel="alternate" type="application/atom+xml" title="Chonkers Alert Atom feed" href="atom.xml">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Chonkers Alert</h1>
  <p class="tagline">Recent Steller sea lion sightings near Pier 39, San Francisco.</p>
  <p class="meta">
    {count} sighting{'' if count == 1 else 's'} ·
    Updated {html.escape(updated)} ·
    <a href="atom.xml">Atom feed</a> ·
    <a href="https://github.com/simonw/chonkers-alert">Source</a>
  </p>
</header>
{sightings_html}
<footer>
  Data from <a href="https://www.inaturalist.org/">iNaturalist</a>.
  Bounding box: 37.795,-122.420 → 37.815,-122.388.
</footer>
</div>
</body>
</html>
"""


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    sys.stdout.write(render(data))


if __name__ == "__main__":
    main()
