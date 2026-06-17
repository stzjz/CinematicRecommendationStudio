import argparse
import csv
import html
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from io import TextIOWrapper
from urllib.parse import urlencode
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
import zipfile

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_DIR = os.path.dirname(BACKEND_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import DEFAULT_DB_PATH
from app.metadata_catalog import movie_key, reorder_title_for_lookup, save_metadata_catalog, title_lookup_variants
from app.movie_metadata import summary_for_movie
from app.poster_catalog import poster_url_for_movie


SEARCH_API = "https://en.wikipedia.org/w/api.php"
TMDB_API = "https://api.themoviedb.org/3"
TMDB_WEB = "https://www.themoviedb.org/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
USER_AGENT = "CinematicRecommendationStudio/1.0 (movie metadata enrichment)"


def load_local_env():
    for filename in (".env.local", ".env"):
        path = os.path.join(PROJECT_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_json_with_curl(url, timeout, request_headers, force_ipv4=False):
    command = ["curl", "-fsSL", "--max-time", str(int(timeout)), "-A", USER_AGENT]
    if force_ipv4:
        command.insert(1, "-4")
    for key, value in request_headers.items():
        if key.lower() == "user-agent":
            continue
        command.extend(["-H", "%s: %s" % (key, value)])
    command.append(url)
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip().splitlines()
        detail = stderr[-1] if stderr else "request failed"
        raise RuntimeError("curl exit %s for %s: %s" % (exc.returncode, safe_url(url), detail)) from exc
    return json.loads(result.stdout)


def fetch_text_with_curl(url, timeout, request_headers):
    command = ["curl", "-fsSL", "--max-time", str(int(timeout)), "-A", USER_AGENT]
    for key, value in request_headers.items():
        if key.lower() == "user-agent":
            continue
        command.extend(["-H", "%s: %s" % (key, value)])
    command.append(url)
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip().splitlines()
        detail = stderr[-1] if stderr else "request failed"
        raise RuntimeError("curl exit %s for %s: %s" % (exc.returncode, safe_url(url), detail)) from exc
    return result.stdout


def safe_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def fetch_json(url, timeout, headers=None):
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    last_error = None
    attempts = max(int(os.getenv("METADATA_HTTP_RETRIES", "2")), 1)
    curl_ipv4_mode = os.getenv("TMDB_CURL_IPV4", "auto").strip().lower()
    for attempt in range(attempts):
        try:
            if os.getenv("TMDB_TRANSPORT", "curl").strip().lower() == "curl":
                try:
                    return fetch_json_with_curl(url, timeout, request_headers, force_ipv4=curl_ipv4_mode in ("1", "true", "yes"))
                except Exception as exc:
                    if curl_ipv4_mode == "auto" and "SSL: no alternative certificate subject name matches target host name" in str(exc):
                        return fetch_json_with_curl(url, timeout, request_headers, force_ipv4=True)
                    raise

            request = Request(url, headers=request_headers)
            try:
                with urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception:
                return fetch_json_with_curl(url, timeout, request_headers, force_ipv4=curl_ipv4_mode in ("1", "true", "yes"))
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.0 + attempt)
    raise RuntimeError(str(last_error))


def safe_error(exc):
    message = str(exc)
    api_key = get_tmdb_api_key()
    bearer_token = os.getenv("TMDB_BEARER_TOKEN", "").strip()
    if api_key:
        message = message.replace(api_key, "[redacted-api-key]")
    if bearer_token:
        message = message.replace(bearer_token, "[redacted-token]")
    if "SSL: no alternative certificate subject name matches target host name" in message:
        message += " (try IPv4 routing; this usually means the current network path returned the wrong TLS certificate)"
    return message


def should_try_tmdb(source, tmdb_enabled):
    return tmdb_enabled and source in ("auto", "tmdb", "tmdb+wiki")


def should_try_tmdb_web(source):
    return source in ("tmdb_web", "tmdb+wiki")


def should_try_wikipedia(source, tmdb_enabled):
    if source == "wiki":
        return True
    if source == "tmdb+wiki":
        return True
    return source == "auto" and not tmdb_enabled


def source_label(source, tmdb_enabled):
    if source == "auto":
        return "tmdb" if tmdb_enabled else "wiki"
    return source


def apply_http_retry_env(retries):
    os.environ["METADATA_HTTP_RETRIES"] = str(max(retries, 1))


def apply_curl_ipv4_env(mode):
    os.environ["TMDB_CURL_IPV4"] = mode


def maybe_print_fetching(args, scanned, total, movie):
    if args.progress_every <= 0:
        return
    if scanned == 1 or scanned % args.progress_every == 0:
        print("fetching=%s/%s current=%s" % (scanned, total, movie["title"]), flush=True)


def clean_error_from_record(record):
    if "error" in record:
        record = dict(record)
        record.pop("error", None)
    return record


def record_error(record, exc):
    record["error"] = safe_error(exc)
    return record


def merge_error_record(current_record, exc, source):
    record = {"source": current_record.get("source") or source}
    return record_error(record, exc)


def request_context_error(remote_record):
    return remote_record and remote_record.get("error")


def error_source(tmdb_enabled):
    return "tmdb" if tmdb_enabled else "wikipedia"


def should_update_from_remote(remote_record):
    return remote_record and not remote_record.get("error")


def existing_error(current_record):
    return current_record.get("error")


def sanitize_existing_error(current_record):
    error = current_record.get("error")
    if not error:
        return ""
    message = safe_error(Exception(error))
    if "Authorization" in message or "api_key=" in message or "[redacted-" in message:
        return "previous metadata request failed; rerun enrichment to retry"
    return message


def is_missing_remote_record(remote_record):
    return not remote_record


def apply_remote_identifiers(remote_record, link_info):
    if link_info.get("tmdb_id") and not remote_record.get("tmdb_id"):
        remote_record["tmdb_id"] = link_info["tmdb_id"]
    if link_info.get("imdb_id") and not remote_record.get("imdb_id"):
        remote_record["imdb_id"] = link_info["imdb_id"]
    return remote_record


def record_fetch_error(local_record, current_record, remote_record):
    if existing_error(current_record):
        local_record["error"] = sanitize_existing_error(current_record)
    elif request_context_error(remote_record):
        local_record["error"] = safe_error(Exception(remote_record["error"]))
    return local_record



def get_tmdb_headers():
    bearer_token = os.getenv("TMDB_BEARER_TOKEN", "").strip()
    if bearer_token:
        return {"Authorization": "Bearer %s" % bearer_token}
    return {}


def get_tmdb_api_key():
    return os.getenv("TMDB_API_KEY", "").strip()


def build_tmdb_url(path, params=None):
    clean_path = path if path.startswith("/") else "/%s" % path
    query = dict(params or {})
    api_key = get_tmdb_api_key()
    if api_key:
        query["api_key"] = api_key
    encoded = urlencode(query)
    return "%s%s%s" % (TMDB_API, clean_path, ("?%s" % encoded) if encoded else "")


def extract_year(text):
    if not text:
        return None
    for token in text.split():
        if len(token) == 4 and token.isdigit():
            return int(token)
    return None


def normalize_text(text):
    return "".join(ch.lower() for ch in (text or "") if ch.isalnum())


def build_search_queries(title, year):
    base_variants = title_lookup_variants(title)
    queries = []
    for variant in base_variants[:4]:
        queries.append("%s %s film" % (variant, year))
        queries.append("%s film" % variant)
        queries.append("%s %s" % (variant, year))

    seen = set()
    results = []
    for item in queries:
        cleaned = " ".join(item.split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            results.append(cleaned)
    return results


def search_candidate_titles(query, timeout):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 5,
        "format": "json",
        "formatversion": 2,
    }
    payload = fetch_json("%s?%s" % (SEARCH_API, urlencode(params)), timeout)
    return [item.get("title") for item in payload.get("query", {}).get("search", []) if item.get("title")]


def fetch_title_details(titles, timeout):
    if not titles:
        return []
    params = {
        "action": "query",
        "prop": "pageimages|extracts|categories",
        "titles": "|".join(titles),
        "piprop": "original",
        "exintro": 1,
        "explaintext": 1,
        "cllimit": "max",
        "format": "json",
        "formatversion": 2,
    }
    payload = fetch_json("%s?%s" % (SEARCH_API, urlencode(params)), timeout)
    return payload.get("query", {}).get("pages", [])


def page_score(page, requested_title, requested_year):
    score = 0
    page_title = page.get("title") or ""
    extract = page.get("extract") or ""
    categories = [item.get("title", "").lower() for item in page.get("categories", [])]
    title_norm = normalize_text(requested_title)
    page_norm = normalize_text(page_title)

    if page_norm == title_norm:
        score += 60
    elif title_norm and title_norm in page_norm:
        score += 42

    alt_title = normalize_text(reorder_title_for_lookup(requested_title))
    if alt_title and alt_title == page_norm:
        score += 20

    page_year = extract_year(page_title) or extract_year(extract)
    if requested_year and page_year == requested_year:
        score += 25
    elif requested_year and abs((page_year or 0) - requested_year) <= 1:
        score += 10

    if any("film" in item for item in categories):
        score += 18
    if any("disambiguation" in item for item in categories):
        score -= 80
    if any("album" in item or "soundtrack" in item or "tv series" in item or "television" in item for item in categories):
        score -= 40
    if page.get("original", {}).get("source"):
        score += 10
    if extract:
        score += 8
    return score


def fetch_wikipedia_movie_metadata(title, year, timeout):
    candidate_titles = []
    for query in build_search_queries(title, year):
        for page_title in search_candidate_titles(query, timeout):
            if page_title not in candidate_titles:
                candidate_titles.append(page_title)
        if len(candidate_titles) >= 8:
            break

    details = fetch_title_details(candidate_titles[:8], timeout)
    ranked = sorted(details, key=lambda page: page_score(page, title, year), reverse=True)
    if not ranked or page_score(ranked[0], title, year) < 45:
        return None

    best = ranked[0]
    poster_url = ((best.get("original") or {}).get("source") or "").strip()
    summary = (best.get("extract") or "").strip()
    if not poster_url and not summary:
        return None

    return {
        "poster_url": poster_url,
        "summary": summary,
        "source": "wikipedia",
        "page_title": best.get("title") or "",
        "fetched_at": utc_timestamp(),
    }


def fetch_tmdb_movie_metadata(tmdb_id, timeout):
    headers = get_tmdb_headers()
    languages = ["zh-CN", "en-US"]
    best_payload = None

    for language in languages:
        payload = fetch_json(
            build_tmdb_url("/movie/%s" % tmdb_id, {"language": language}),
            timeout,
            headers=headers,
        )
        if not best_payload:
            best_payload = payload
        if payload.get("overview"):
            best_payload = payload
            break

    if not best_payload:
        return None

    poster_path = (best_payload.get("poster_path") or "").strip()
    overview = (best_payload.get("overview") or "").strip()
    release_date = (best_payload.get("release_date") or "").strip()
    title = (best_payload.get("title") or "").strip()
    original_title = (best_payload.get("original_title") or "").strip()
    if not poster_path and not overview:
        return None

    return {
        "poster_url": ("%s%s" % (TMDB_IMAGE_BASE, poster_path)) if poster_path else "",
        "summary": overview,
        "source": "tmdb",
        "page_title": title or original_title,
        "release_date": release_date,
        "tmdb_id": str(tmdb_id),
        "fetched_at": utc_timestamp(),
    }


def extract_meta_content(page, property_name):
    for tag in re.findall(r"<meta\b[^>]*>", page):
        property_match = re.search(r"\bproperty=[\"']([^\"']+)[\"']", tag)
        if not property_match or property_match.group(1) != property_name:
            continue
        content_match = re.search(r"\bcontent=[\"']([^\"']*)[\"']", tag)
        if content_match:
            return html.unescape(content_match.group(1)).strip()
    return ""


def fetch_tmdb_web_movie_metadata(tmdb_id, timeout):
    headers = {"Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.7,en;q=0.6"}
    best_record = None
    for language in ("zh-CN", "en-US"):
        url = "%s/%s?language=%s" % (TMDB_WEB, tmdb_id, language)
        page = fetch_text_with_curl(url, timeout, headers)
        title = extract_meta_content(page, "og:title")
        summary = extract_meta_content(page, "og:description")
        poster_url = extract_meta_content(page, "og:image")
        if poster_url.startswith("https://media.themoviedb.org/t/p/"):
            poster_url = poster_url.replace("/w500/", "/original/")
        record = {
            "poster_url": poster_url,
            "summary": summary,
            "source": "tmdb_web",
            "page_title": title,
            "tmdb_id": str(tmdb_id),
            "fetched_at": utc_timestamp(),
        }
        if not best_record:
            best_record = record
        if summary and poster_url:
            return record
    if best_record and (best_record.get("summary") or best_record.get("poster_url")):
        return best_record
    return None


def fetch_tmdb_by_imdb_id(imdb_id, timeout):
    headers = get_tmdb_headers()
    payload = fetch_json(
        build_tmdb_url("/find/tt%s" % str(imdb_id).zfill(7), {"external_source": "imdb_id", "language": "zh-CN"}),
        timeout,
        headers=headers,
    )
    movie_results = payload.get("movie_results") or []
    if not movie_results:
        return None
    tmdb_id = movie_results[0].get("id")
    if not tmdb_id:
        return None
    return fetch_tmdb_movie_metadata(tmdb_id, timeout)


def parse_movie_ids(raw_value):
    if not raw_value:
        return []
    movie_ids = []
    for item in raw_value.replace(";", ",").split(","):
        cleaned = item.strip()
        if cleaned:
            movie_ids.append(int(cleaned))
    return movie_ids


def load_movies(connection, limit=None, movie_ids=None):
    sql = "SELECT movie_id, title, year, poster_url, summary FROM movies ORDER BY movie_id"
    params = ()
    if movie_ids:
        placeholders = ",".join("?" for _ in movie_ids)
        sql = "SELECT movie_id, title, year, poster_url, summary FROM movies WHERE movie_id IN (%s) ORDER BY movie_id" % placeholders
        params = tuple(movie_ids)
    if limit is not None:
        sql += " LIMIT ?"
        params = tuple(params) + (limit,)
    return [dict(row) for row in connection.execute(sql, params).fetchall()]


def discover_links_archive():
    candidates = [
        os.path.join(BACKEND_DIR, "data", "raw", "ml-25m.zip"),
        os.path.join(BACKEND_DIR, "data", "raw", "ml-latest.zip"),
        os.path.join(BACKEND_DIR, "data", "raw", "ml-latest-small.zip"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def load_movielens_links(archive_path):
    if not archive_path or not os.path.exists(archive_path):
        return {}

    with zipfile.ZipFile(archive_path) as archive:
        member_name = ""
        for name in archive.namelist():
            if name.lower().endswith("links.csv"):
                member_name = name
                break
        if not member_name:
            return {}

        with archive.open(member_name) as handle:
            reader = csv.DictReader(TextIOWrapper(handle, encoding="utf-8"))
            links = {}
            for row in reader:
                movie_id = int(row["movieId"])
                links[movie_id] = {
                    "imdb_id": (row.get("imdbId") or "").strip(),
                    "tmdb_id": (row.get("tmdbId") or "").strip(),
                }
            return links


def load_existing_records():
    try:
        from app.metadata_catalog import load_metadata_catalog

        return dict(load_metadata_catalog().get("movies", {}))
    except Exception:
        return {}


def should_fetch(movie, force):
    if force:
        return True
    poster = (movie.get("poster_url") or "").strip()
    summary = (movie.get("summary") or "").strip()
    poster_missing = (not poster) or poster.startswith("/api/posters/")
    summary_missing = not summary or len(summary) < 20
    return poster_missing or summary_missing


def merge_record(movie, record):
    return {
        "poster_url": (record.get("poster_url") or "").strip() or poster_url_for_movie(movie["title"], movie["year"], movie.get("poster_url")),
        "summary": (record.get("summary") or "").strip() or summary_for_movie(movie["title"], movie["year"], movie.get("summary")),
        "source": record.get("source") or "local",
        "page_title": record.get("page_title") or "",
        "tmdb_id": (record.get("tmdb_id") or "").strip(),
        "imdb_id": (record.get("imdb_id") or "").strip(),
        "fetched_at": record.get("fetched_at") or utc_timestamp(),
    }


def update_database(connection, movie_id, record):
    connection.execute(
        """
        UPDATE movies
        SET poster_url = ?, summary = ?
        WHERE movie_id = ?
        """,
        (record.get("poster_url") or None, record.get("summary") or None, movie_id),
    )


def main():
    load_local_env()
    parser = argparse.ArgumentParser(description="Enrich movie posters and summaries via TMDb or Wikipedia and cache the results locally.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)
    parser.add_argument("--links-archive", default=discover_links_archive())
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--movie-ids", default="", help="Comma-separated MovieLens movie IDs to enrich.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--source", choices=("auto", "tmdb", "tmdb_web", "wiki", "tmdb+wiki"), default="auto")
    parser.add_argument("--ipv4", action="store_true", help="Force curl to use IPv4 for metadata requests.")
    parser.add_argument("--no-ipv4", action="store_true", help="Disable automatic IPv4 retry for metadata requests.")
    args = parser.parse_args()
    apply_http_retry_env(args.retries)
    curl_ipv4_mode = "1" if args.ipv4 else ("0" if args.no_ipv4 else "auto")
    apply_curl_ipv4_env(curl_ipv4_mode)

    connection = sqlite3.connect(args.db_path, timeout=60)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 60000")
    try:
        movies = load_movies(connection, args.limit, parse_movie_ids(args.movie_ids))
        links_map = load_movielens_links(args.links_archive)
        records = load_existing_records()
        for record in records.values():
            if record.get("error"):
                record["error"] = sanitize_existing_error(record)
        scanned = 0
        fetched = 0
        failed = 0
        updated = 0
        last_error = ""
        last_report_failed = 0
        tmdb_enabled = bool(get_tmdb_api_key() or get_tmdb_headers())
        print(
            "start movies=%s missing_only=%s source=%s delay=%s timeout=%s retries=%s curl_ipv4=%s"
            % (len(movies), not args.force, source_label(args.source, tmdb_enabled), args.delay, args.timeout, args.retries, curl_ipv4_mode),
            flush=True,
        )

        for movie in movies:
            scanned += 1
            key = movie_key(movie["title"], movie["year"])
            current_record = records.get(key, {})
            local_record = merge_record(movie, current_record)
            link_info = links_map.get(movie["movie_id"], {})
            if link_info.get("tmdb_id") and not local_record.get("tmdb_id"):
                local_record["tmdb_id"] = link_info["tmdb_id"]
            if link_info.get("imdb_id") and not local_record.get("imdb_id"):
                local_record["imdb_id"] = link_info["imdb_id"]

            if should_fetch(movie, args.force):
                maybe_print_fetching(args, scanned, len(movies), movie)
                remote_error = None
                try:
                    remote_record = None
                    if should_try_tmdb(args.source, tmdb_enabled) and link_info.get("tmdb_id"):
                        try:
                            remote_record = fetch_tmdb_movie_metadata(link_info["tmdb_id"], args.timeout)
                        except Exception as exc:
                            remote_error = exc
                    if should_try_tmdb(args.source, tmdb_enabled) and not remote_record and link_info.get("imdb_id"):
                        try:
                            remote_record = fetch_tmdb_by_imdb_id(link_info["imdb_id"], args.timeout)
                        except Exception as exc:
                            remote_error = exc
                    if should_try_tmdb_web(args.source) and not remote_record and link_info.get("tmdb_id"):
                        try:
                            remote_record = fetch_tmdb_web_movie_metadata(link_info["tmdb_id"], args.timeout)
                        except Exception as exc:
                            remote_error = exc
                    if should_try_wikipedia(args.source, tmdb_enabled) and is_missing_remote_record(remote_record):
                        remote_record = fetch_wikipedia_movie_metadata(movie["title"], movie["year"], args.timeout)
                    if is_missing_remote_record(remote_record) and remote_error:
                        raise remote_error
                except Exception as exc:
                    remote_record = merge_error_record(current_record, exc, error_source(tmdb_enabled))

                if should_update_from_remote(remote_record):
                    fetched += 1
                    local_record = merge_record(movie, apply_remote_identifiers(remote_record, link_info))
                    local_record = clean_error_from_record(local_record)
                else:
                    if request_context_error(remote_record):
                        failed += 1
                        last_error = safe_error(Exception(remote_record["error"]))
                    local_record = record_fetch_error(local_record, current_record, remote_record)

                time.sleep(max(args.delay, 0.0))

            records[key] = local_record
            update_database(connection, movie["movie_id"], local_record)
            updated += 1

            if args.progress_every > 0 and scanned % args.progress_every == 0:
                connection.commit()
                save_metadata_catalog(records)
                error_suffix = (" last_error=%s" % last_error) if failed > last_report_failed and last_error else ""
                print(
                    "processed=%s/%s fetched=%s failed=%s updated=%s current=%s%s"
                    % (
                        scanned,
                        len(movies),
                        fetched,
                        failed,
                        updated,
                        movie["title"],
                        error_suffix,
                    ),
                    flush=True,
                )
                last_report_failed = failed

        connection.commit()
        path = save_metadata_catalog(records)
        print(
            "done processed=%s fetched=%s failed=%s updated=%s source=%s cache=%s%s"
            % (
                scanned,
                fetched,
                failed,
                updated,
                source_label(args.source, tmdb_enabled),
                path,
                (" last_error=%s" % last_error) if last_error else "",
            ),
            flush=True,
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
