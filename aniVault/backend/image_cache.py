"""
AniVault — local image cache (AniList only)

Downloads anime cover art from AniList's GraphQL API and caches it on disk
at data/images/<mal_id>.jpg, keyed by MyAnimeList ID via AniList's `idMal`
field — so the URL scheme (/static/images/<mal_id>.jpg) and everything
already cached stay compatible even though Jikan is no longer used at all.

AniList is a real maintained anime database (not a MyAnimeList scraper),
generally more stable than Jikan. Its public rate limit is roughly
90 requests/minute.

Transient failures (network errors, 5xx, timeouts) are retried with
backoff and reported separately from a genuine "no match" result, so a
temporary AniList outage never permanently marks an anime as unresolved —
it just gets retried on the next sync.
"""

import random
import time
from pathlib import Path

import requests

import paths

IMAGES_DIR = paths.get_data_dir() / "images"

ANILIST_URL      = "https://graphql.anilist.co"
REQUEST_TIMEOUT  = 10  # seconds
MAX_RETRIES      = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

ANILIST_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    idMal
    coverImage { large }
  }
}
"""

# ── Circuit breaker ────────────────────────
# If AniList is having a sustained outage, retrying full backoff on every
# single anime in the list is a bad experience — a 49-entry sync would
# take minutes of pure waiting. After a few consecutive complete failures,
# stop hitting the network for a cooldown period and fail fast instead.
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECONDS  = 60

_circuit_state = {"consecutive_failures": 0, "open_until": 0.0}


def circuit_is_open():
    return time.time() < _circuit_state["open_until"]


def _record_failure():
    _circuit_state["consecutive_failures"] += 1
    if _circuit_state["consecutive_failures"] >= CIRCUIT_FAILURE_THRESHOLD:
        _circuit_state["open_until"] = time.time() + CIRCUIT_COOLDOWN_SECONDS
        print(f"[image_cache] AniList looks down — pausing cover lookups for "
              f"{CIRCUIT_COOLDOWN_SECONDS}s instead of retrying every entry.")


def _record_success():
    _circuit_state["consecutive_failures"] = 0
    _circuit_state["open_until"] = 0.0


def ensure_images_dir():
    """Create the images directory (and parents) if it doesn't exist yet."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_images()


def _migrate_legacy_images():
    """
    Before an earlier refactor, cached covers lived at backend/static/images/.
    Move any files found there into the new data/images/ folder, once.
    """
    legacy_dir = Path(__file__).resolve().parent / "static" / "images"
    if not legacy_dir.exists() or legacy_dir == IMAGES_DIR:
        return
    moved = 0
    for f in legacy_dir.glob("*.jpg"):
        dest = IMAGES_DIR / f.name
        if not dest.exists():
            f.rename(dest)
            moved += 1
    if moved:
        print(f"[image_cache] Migrated {moved} cached image(s) from {legacy_dir} -> {IMAGES_DIR}")


def local_image_path(mal_id):
    """Filesystem path for a given MAL id's cached cover."""
    return IMAGES_DIR / f"{mal_id}.jpg"


def local_image_url(mal_id):
    """Public URL path the frontend should use to load this cover."""
    return f"/static/images/{mal_id}.jpg"


def image_exists(mal_id):
    return local_image_path(mal_id).exists()


def _request_with_retry(method, url, accept_statuses=(), **kwargs):
    """
    requests.get/post with retry-on-transient-failure.

    accept_statuses: HTTP status codes returned as-is without raising or
    retrying, even though they aren't 2xx — used for AniList's 404-with-
    GraphQL-error convention for "no match found", a valid outcome.

    Returns a Response on success/accepted-status, or None if all retries
    were exhausted (network error, timeout, or a retryable status every time).
    """
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            if resp.status_code in accept_statuses:
                return resp
            if resp.status_code in RETRYABLE_STATUS:
                last_err = f"HTTP {resp.status_code}"
            else:
                resp.raise_for_status()
                return resp
        except requests.RequestException as err:
            last_err = str(err)

        if attempt < MAX_RETRIES - 1:
            time.sleep((0.5 * (2 ** attempt)) + random.uniform(0, 0.3))

    print(f"[image_cache] Giving up after {MAX_RETRIES} attempts on {url}: {last_err}")
    return None


def download_image(mal_id, remote_url):
    """
    Download remote_url to data/images/<mal_id>.jpg.
    Returns True on success, False on failure (never raises).
    """
    if not remote_url:
        return False

    ensure_images_dir()
    dest = local_image_path(mal_id)
    tmp_path = dest.with_suffix(".tmp")

    resp = _request_with_retry("GET", remote_url, stream=True)
    if resp is None:
        return False

    try:
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        tmp_path.replace(dest)
        return True
    except OSError as err:
        print(f"[image_cache] Failed writing cover for mal_id={mal_id}: {err}")
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        return False


def search_anilist(name):
    """
    Query AniList's GraphQL API for `name`.

    Returns one of:
      ("found",     mal_id, image_url) — matched AND has a usable MAL id
      ("not_found", None,   None)      — no match, or matched with no MAL
                                          mapping (rare, but then we have
                                          no key to cache it under)
      ("error",     None,   None)      — request failed even after retries
    """
    if circuit_is_open():
        return "error", None, None

    resp = _request_with_retry(
        "POST", ANILIST_URL,
        accept_statuses={404},
        json={"query": ANILIST_QUERY, "variables": {"search": name}},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if resp is None:
        _record_failure()
        return "error", None, None

    try:
        payload = resp.json()
    except ValueError as err:
        print(f"[image_cache] AniList returned unparseable JSON for '{name}': {err}")
        _record_failure()
        return "error", None, None

    _record_success()  # a well-formed response, even a 404-not-found, means AniList is up

    media = (payload.get("data") or {}).get("Media")
    if not media:
        return "not_found", None, None

    mal_id = media.get("idMal")
    if not mal_id:
        return "not_found", None, None

    image_url = (media.get("coverImage") or {}).get("large")
    return "found", mal_id, image_url


def get_or_fetch_cover(name, existing_mal_id=None):
    """
    Main entry point used by the API layer.

    Returns (mal_id, local_url, permanent):
      - mal_id:    resolved MyAnimeList id, or None if never resolved
      - local_url: local /static/images/... path, or None if no image yet
      - permanent: True  -> safe to mark cover_fetched=1 (found + cached,
                             or AniList confirms no match exists)
                   False -> transient failure; caller should NOT set
                            cover_fetched, so it retries on the next sync

    Never raises — all network/API failures degrade gracefully.
    """
    if existing_mal_id and image_exists(existing_mal_id):
        return existing_mal_id, local_image_url(existing_mal_id), True

    status, mal_id, remote_url = search_anilist(name)

    if status == "error":
        return existing_mal_id, None, False
    if status == "not_found":
        return None, None, True

    if image_exists(mal_id):
        return mal_id, local_image_url(mal_id), True

    if download_image(mal_id, remote_url):
        return mal_id, local_image_url(mal_id), True

    return mal_id, None, False