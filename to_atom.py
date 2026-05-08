#!/usr/bin/env python3
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import datetime
import re
import sys
from urllib.parse import quote


SIZE_RE = re.compile(r"/square\.(jpe?g|png)(\?.*)?$", re.IGNORECASE)


def to_large(url):
    return SIZE_RE.sub(r"/large.\1\2", url) if url else url


def format_xml(element):
    """Format XML with proper indentation"""
    rough_string = ET.tostring(element, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ").replace(
        '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>'
    )


def json_to_atom(
    json_data,
    feed_title="Nature Observations Feed",
    feed_id="https://example.com/feed",
    author_name="Feed Generator",
    feed_updated=None,
):
    """
    Convert JSON data to Atom feed
    """

    atom = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")

    ET.SubElement(atom, "title").text = feed_title
    ET.SubElement(atom, "id").text = feed_id

    if feed_updated is None:
        feed_updated = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    ET.SubElement(atom, "updated").text = feed_updated

    author = ET.SubElement(atom, "author")
    ET.SubElement(author, "name").text = author_name

    for item in json_data.get("results", []):
        entry = ET.SubElement(atom, "entry")

        obs_id = item.get("id")
        inaturalist_url = f"https://www.inaturalist.org/observations/{obs_id}"
        ET.SubElement(entry, "id").text = inaturalist_url

        observation_time = item.get("time_observed_at")
        place = item.get("place_guess", "Unknown location")
        title_text = f"Steller Sea Lion at {place}"
        ET.SubElement(entry, "title").text = title_text
        ET.SubElement(entry, "updated").text = observation_time

        content = ET.SubElement(entry, "content")
        content.set("type", "html")

        html_content = f"<div><p>Location: {item.get('place_guess', 'Unknown')}</p>"

        if item.get("geojson") and item.get("geojson").get("coordinates"):
            coords = item.get("geojson").get("coordinates")
            lat, lon = coords[1], coords[0]
            google_maps_url = f"https://www.google.com/maps?q={lat},{lon}"
            html_content += f'<p>Coordinates: <a href="{google_maps_url}" target="_blank">{lat}, {lon}</a></p>'

        if item.get("observation_photos"):
            html_content += "<p>Photos:</p>"
            for photo_data in item.get("observation_photos"):
                if photo_data.get("photo") and photo_data.get("photo").get("url"):
                    photo_url = to_large(photo_data.get("photo").get("url"))
                    photo_attribution = photo_data.get("photo").get("attribution", "")
                    html_content += (
                        f'<div><img src="{photo_url}" alt="Observation photo"/>'
                    )
                    html_content += f"<br/>{photo_attribution}</div>"

        html_content += "</div>"
        content.text = html_content

        if item.get("observation_photos"):
            for photo_data in item.get("observation_photos"):
                if photo_data.get("photo") and photo_data.get("photo").get("url"):
                    photo_url = to_large(photo_data.get("photo").get("url"))
                    link = ET.SubElement(entry, "link")
                    link.set("rel", "enclosure")
                    link.set("href", photo_url)
                    link.set("type", "image/jpeg")

        link = ET.SubElement(entry, "link")
        link.set("rel", "alternate")
        link.set("href", inaturalist_url)

        if item.get("place_guess"):
            category = ET.SubElement(entry, "category")
            category.set("term", quote(item.get("place_guess")))
            category.set("label", item.get("place_guess"))

    return format_xml(atom)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    print(
        json_to_atom(
            data,
            feed_title="Chonkers: Steller Sea Lion sightings near Pier 39",
            feed_id="https://simonw.github.io/chonkers-alert/atom.xml",
            author_name="Chonkers Alert",
            feed_updated=now,
        )
    )


if __name__ == "__main__":
    main()
