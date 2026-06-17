import json
import os
import re
from datetime import datetime, timezone

from app.config import DEFAULT_METADATA_PATH


ARTICLE_SUFFIX_PATTERN = re.compile(r",\s*(The|A|An)$", re.IGNORECASE)
PAREN_PATTERN = re.compile(r"\s*\([^)]*\)")

_CACHE = {"path": None, "mtime": None, "data": {"movies": {}}}


def movie_key(title, year):
    return "%s|%s" % ((title or "").strip().lower(), year or "")


def reorder_title_for_lookup(title):
    clean_title = (title or "").strip()
    match = ARTICLE_SUFFIX_PATTERN.search(clean_title)
    if not match:
        return clean_title
    article = match.group(1)
    body = ARTICLE_SUFFIX_PATTERN.sub("", clean_title).strip()
    return ("%s %s" % (article, body)).strip()


def title_lookup_variants(title):
    raw_title = (title or "").strip()
    candidates = [raw_title, reorder_title_for_lookup(raw_title)]
    stripped = PAREN_PATTERN.sub("", raw_title).strip()
    if stripped:
        candidates.extend([stripped, reorder_title_for_lookup(stripped)])

    seen = set()
    results = []
    for item in candidates:
        normalized = item.lower()
        if item and normalized not in seen:
            seen.add(normalized)
            results.append(item)
    return results


def get_metadata_path():
    return os.getenv("RECSYS_METADATA_PATH", DEFAULT_METADATA_PATH).strip()


def load_metadata_catalog():
    path = get_metadata_path()
    if not os.path.exists(path):
        _CACHE.update({"path": path, "mtime": None, "data": {"movies": {}}})
        return _CACHE["data"]

    mtime = os.path.getmtime(path)
    if _CACHE["path"] == path and _CACHE["mtime"] == mtime:
        return _CACHE["data"]

    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    data = payload if isinstance(payload, dict) else {"movies": {}}
    data.setdefault("movies", {})
    _CACHE.update({"path": path, "mtime": mtime, "data": data})
    return data


def save_metadata_catalog(movie_records):
    path = get_metadata_path()
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "movies": movie_records,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    _CACHE.update({"path": path, "mtime": os.path.getmtime(path), "data": payload})
    return path


def lookup_movie_metadata(title, year):
    records = load_metadata_catalog().get("movies", {})
    for variant in title_lookup_variants(title):
        item = records.get(movie_key(variant, year))
        if item:
            return item
    return None


def metadata_value_for_movie(title, year, field_name, fallback=""):
    record = lookup_movie_metadata(title, year) or {}
    value = record.get(field_name)
    if isinstance(value, str):
        value = value.strip()
    return value or fallback
