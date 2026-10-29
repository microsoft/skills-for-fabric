"""Snapshot public SIT names and definition links; never send schema or data."""

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen
from urllib.parse import urljoin


SOURCE = "https://learn.microsoft.com/en-us/purview/sit-sensitive-information-type-entity-definitions"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "references" / "sit-catalog.json"


class CatalogParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.entries = {}
        self.target = None
        self.label = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if re.fullmatch(r"(?:\./)?sit-defn-[a-z0-9-]+(?:#[a-z0-9-]+)?", href):
                self.target = urljoin(SOURCE, href).split("#")[0]
                self.label = []

    def handle_data(self, data):
        if self.target:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.target:
            name = " ".join("".join(self.label).split())
            if name:
                self.entries[(name, self.target)] = {"name": name, "url": self.target}
            self.target = None
            self.label = []


def parse_catalog(html):
    parser = CatalogParser()
    parser.feed(html)
    entries = sorted(parser.entries.values(), key=lambda entry: entry["name"].casefold())
    names = {entry["name"].casefold() for entry in entries}
    if not {"credit card number", "u.s. social security number (ssn)"} <= names:
        raise ValueError("The page did not contain the expected SIT index; no catalog was written.")
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true", help="Replace the chosen catalog snapshot.")
    args = parser.parse_args()
    request = Request(SOURCE, headers={"User-Agent": "Fabric-SIT-catalog-maintenance"})
    with urlopen(request, timeout=30) as response:
        if not response.geturl().startswith("https://learn.microsoft.com/"):
            raise ValueError("Unexpected catalog redirect; no catalog was written.")
        content = response.read(5_000_001)
    if len(content) > 5_000_000:
        raise ValueError("The SIT index exceeded the download limit; no catalog was written.")
    entries = parse_catalog(content.decode("utf-8"))
    snapshot = {
        "source": SOURCE,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "scope": "Public Purview SIT index, not a Fabric-supported-types list.",
        "entries": entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w" if args.replace else "x", encoding="utf-8") as output:
        output.write(json.dumps(snapshot, ensure_ascii=True, indent=2) + "\n")
    print(f"Saved {len(entries)} SIT names and links to {args.output}")


if __name__ == "__main__":
    main()
