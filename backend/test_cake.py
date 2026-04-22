import json
import urllib.request

from bs4 import BeautifulSoup

url = "https://www.cake.me/jobs?q=Python"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read()
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag and tag.string:
        data = json.loads(tag.string)
        props = (
            data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("jobSearch", {})
        )

        entities = props.get("entityByPathId", {})
        for _path, entity in list(entities.items())[:2]:
            print(f"Locations: {entity.get('locations')}")
            print(f"LocationsWithLocale: {entity.get('locationsWithLocale')}")
except Exception as e:
    print(e)
