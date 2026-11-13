"""Suggest classification tags from column names only, without network access."""

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata


CATALOG = Path(__file__).resolve().parents[1] / "references" / "sit-catalog.json"
NUMBER_WORDS = {"no", "num", "nbr", "nr", "numbers"}
DERIVED_WORDS = {
    "has", "is", "contains", "count", "counts", "flag", "flags", "status",
    "valid", "validated", "validation", "verified", "last", "last4", "lastfour",
    "masked", "mask", "hash", "hashed", "token", "tokenized", "encrypted", "ciphertext",
    "length", "type", "expiry", "expiration", "cvv", "cvc", "brand", "holder",
    "rotation", "date", "timestamp", "present", "provided", "available",
    "amount", "rate", "benefit", "benefits", "payment", "hint",
}


def normalize(value):
    value = unicodedata.normalize("NFKC", value).replace("#", " number ")
    value = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(char for char in value if not unicodedata.combining(char))
    words = re.findall(r"[a-z0-9]+", value)
    value = " ".join("number" if word in NUMBER_WORDS else word for word in words)
    value = re.sub(r"\bu s\b", "us", value)
    value = re.sub(r"\bu k\b", "uk", value)
    return re.sub(r"\bu a e\b", "uae", value)


def proposed_tag(entry):
    name = normalize(entry["name"])
    if "social security number" in name:
        return "Social security number"
    if name == "credit card number":
        return "Credit card number"
    if "bank account number" in name:
        return "Bank account number"
    if "passport number" in name:
        return "Passport number"
    return entry["name"]


class Matcher:
    def __init__(self, catalog):
        if not isinstance(catalog, dict) or not isinstance(catalog.get("entries"), list):
            raise ValueError("The SIT catalog must contain an entries array.")
        for field in ("source", "retrieved_at_utc", "scope"):
            if not isinstance(catalog.get(field), str) or not catalog[field]:
                raise ValueError(f"The SIT catalog is missing its {field} metadata.")
        self.catalog = catalog
        self.entries = catalog["entries"]
        if not self.entries:
            raise ValueError("The SIT catalog is empty.")
        self.aliases = {}
        self.exact_names = {}
        for index, entry in enumerate(self.entries):
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("name"), str)
                or not entry["name"].strip()
            ):
                raise ValueError("Each catalog entry must have a name.")
            if not isinstance(entry.get("url"), str) or not entry["url"].startswith(
                "https://learn.microsoft.com/en-us/purview/sit-defn-"
            ):
                raise ValueError(f"Missing public SIT definition link: {entry['name']}")
            self.exact_names.setdefault(normalize(entry["name"]).replace(" ", ""), set()).add(index)
            self.add_alias(entry["name"], [index])
            self.add_alias(re.sub(r"\([^)]*\)", "", entry["name"]), [index])
            for acronym in re.findall(r"\(([A-Z][A-Z0-9/-]{1,9})\)", entry["name"]):
                self.add_alias(acronym, [index])
                self.add_alias(normalize(entry["name"]).split()[0] + " " + acronym, [index])

        self.add_family(
            "Social security number",
            ["ssn", "ssns", "ssn number", "ssn id", "social security number", "soc sec", "ssa number"],
        )
        self.add_family(
            "Credit card number",
            ["credit card", "credit card number", "cc number", "ccn"],
        )
        self.add_family("Bank account number", ["bank account number", "bank acct number"])
        self.add_family("Passport number", ["passport number"])
        for alias, slug in {
            "full name": "sit-defn-all-full-names",
            "api key": "sit-defn-client-secret-api-key",
            "swift": "sit-defn-swift-code",
            "bic": "sit-defn-swift-code",
            "aadhaar": "sit-defn-india-unique-identification-number",
            "aadhaar number": "sit-defn-india-unique-identification-number",
            "password": "sit-defn-general-password",
            "passwd": "sit-defn-general-password",
            "pwd": "sit-defn-general-password",
        }.items():
            self.add_alias(alias, self.indices_for_slug(slug))
        self.add_alias(
            "pan",
            self.indices_for_slug("sit-defn-credit-card-number")
            + self.indices_for_slug("sit-defn-india-permanent-account-number"),
        )
        self.add_alias(
            "card number",
            self.indices_for_slug("sit-defn-credit-card-number")
            + self.indices_for_slug("sit-defn-eu-debit-card-number"),
        )

    def indices_for_slug(self, slug):
        indices = [
            index for index, entry in enumerate(self.entries)
            if entry["url"].rsplit("/", 1)[-1] == slug
        ]
        if not indices:
            raise ValueError(f"An alias references a SIT absent from the catalog: {slug}")
        return indices

    def add_alias(self, alias, indices):
        key = normalize(alias).replace(" ", "")
        if len(key) >= 3:
            self.aliases.setdefault(key, set()).update(indices)
            if key.endswith("number"):
                for suffix in ("no", "num", "nbr", "nr", "numbers"):
                    self.aliases.setdefault(key[:-6] + suffix, set()).update(indices)

    def add_family(self, tag, aliases):
        indices = [
            index for index, entry in enumerate(self.entries)
            if proposed_tag(entry) == tag
        ]
        if not indices:
            raise ValueError(f"No catalog entries found for the alias family: {tag}")
        for alias in aliases:
            self.add_alias(alias, indices)

    def suggest(self, column):
        if not isinstance(column, str) or not column.strip():
            raise ValueError("Each column name must be a nonempty string.")
        if len(column) > 1024:
            raise ValueError("A column name exceeds the 1,024-character input limit.")
        words = normalize(column).split()
        matches = []
        for start in range(len(words)):
            key = ""
            for end in range(start, len(words)):
                key += words[end]
                if key in self.aliases:
                    matches.append((len(key), start, end + 1, key))
        result = {
            "column": column,
            "status": "no_name_match",
            "suggested_tag": None,
            "matched_names": [],
            "sit_candidates": [],
            "requires_review": True,
            "reason": "No catalog name or supported alias matched. This does not establish that the column is non-sensitive.",
        }
        if not matches:
            return result
        strongest = [
            match for match in matches
            if not any(
                other[0] > match[0] and other[1] <= match[1] and other[2] >= match[2]
                for other in matches
            )
        ]
        indices = self.exact_names.get("".join(words))
        if indices is None:
            indices = set().union(*(self.aliases[match[3]] for match in strongest))
        candidates = [self.entries[index] for index in sorted(indices)]
        tags = {proposed_tag(entry) for entry in candidates}
        result["sit_candidates"] = candidates
        result["matched_names"] = list(dict.fromkeys(
            " ".join(words[start:end]) for _, start, end, _ in strongest
        ))
        outside = set()
        for _, start, end, _ in strongest:
            outside.update(words[:start] + words[end:])
        if outside & DERIVED_WORDS:
            result["status"] = "needs_review"
            result["reason"] = (
                "The name appears to describe a derived, masked, or supporting field, "
                "not necessarily the full sensitive value. No tag is recommended automatically."
            )
        elif len(tags) > 1:
            result["status"] = "needs_review"
            result["reason"] = "The name maps to different SIT categories. Confirm its meaning before choosing a tag."
        else:
            result["status"] = "suggested"
            result["suggested_tag"] = next(iter(tags))
            result["reason"] = "Name-only match; confirm the column's meaning before applying the proposed tag."
            if len(candidates) > 1:
                result["reason"] += " The name does not resolve the specific SIT or jurisdiction; candidates are listed."
        return result

    def classify(self, payload):
        if isinstance(payload, list):
            table, columns = None, payload
        elif isinstance(payload, dict):
            table, columns = payload.get("table"), payload.get("columns")
            if table is not None and (not isinstance(table, str) or not table.strip()):
                raise ValueError("The optional table name must be a nonempty string.")
        else:
            raise ValueError("Input must be a column-name array or an object with a columns array.")
        if not isinstance(columns, list) or not columns:
            raise ValueError("Provide at least one column in the columns array.")
        return {
            "table": table,
            "basis": "column_names_only",
            "contents_inspected": False,
            "changes_applied": False,
            "catalog_source": self.catalog["source"],
            "catalog_retrieved_at_utc": self.catalog["retrieved_at_utc"],
            "catalog_scope": self.catalog["scope"],
            "alias_scope": "Normalized catalog names, catalog acronyms, and authored aliases; not an exhaustive synonym dictionary.",
            "results": [self.suggest(column) for column in columns],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="JSON file; omit to read JSON from standard input.")
    args = parser.parse_args()
    try:
        text = args.input.read_text(encoding="utf-8-sig") if args.input else sys.stdin.read()
        payload = json.loads(text)
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        result = Matcher(catalog).classify(payload)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
