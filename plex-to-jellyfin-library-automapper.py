import requests
import xml.etree.ElementTree as ET

# pip install pycountry  — enables full ISO 639 coverage (~500+ languages).
# If not installed, the script falls back to the built-in map below.
try:
    import pycountry
    _HAS_PYCOUNTRY = True
except ImportError:
    _HAS_PYCOUNTRY = False

# === CONFIGURATION ===
PLEX_URL = "http://YOUR_PLEX_IP:32400"
PLEX_TOKEN = "YOUR_PLEX_TOKEN"
JELLYFIN_URL = "http://YOUR_JELLYFIN_IP:8096"
JELLYFIN_API_KEY = "YOUR_JELLYFIN_API_KEY"
# =====================

REQUEST_TIMEOUT = 10

# Used only when pycountry is not installed.
# Covers the most common languages; pycountry handles everything else.
_FALLBACK_LANG_MAP = {
    "af": "afr", "ar": "ara", "bg": "bul", "bn": "ben",
    "ca": "cat", "cs": "ces", "cy": "cym", "da": "dan",
    "de": "deu", "el": "ell", "en": "eng", "es": "spa",
    "et": "est", "eu": "eus", "fa": "fas", "fi": "fin",
    "fr": "fra", "ga": "gle", "gl": "glg", "gu": "guj",
    "he": "heb", "hi": "hin", "hr": "hrv", "hu": "hun",
    "hy": "hye", "id": "ind", "is": "isl", "it": "ita",
    "ja": "jpn", "ka": "kat", "kn": "kan", "ko": "kor",
    "lt": "lit", "lv": "lav", "mk": "mkd", "ml": "mal",
    "mr": "mar", "ms": "msa", "mt": "mlt", "nb": "nob",
    "nl": "nld", "nn": "nno", "pa": "pan", "pl": "pol",
    "pt": "por", "ro": "ron", "ru": "rus", "sk": "slk",
    "sl": "slv", "sq": "sqi", "sr": "srp", "sv": "swe",
    "sw": "swa", "ta": "tam", "te": "tel", "th": "tha",
    "tl": "tgl", "tr": "tur", "uk": "ukr", "ur": "urd",
    "vi": "vie", "zh": "zho"
}


def convert_language_code(raw_code: str) -> str:
    """
    Convert any Plex language tag to a Jellyfin-compatible ISO 639-2 three-letter code.

    Handles:
    - ISO 639-1 two-letter codes    ("en", "fr", "de")
    - BCP 47 regional subtags       ("en-US", "pt-BR", "zh-Hant")  → strips region
    - Three-letter codes already    ("eng", "fra")                  → passed through
    - Empty / None / malformed      → falls back to "eng"

    With pycountry installed this covers every language in the ISO 639 standard.
    Without it, falls back to _FALLBACK_LANG_MAP (~60 common languages).
    """
    if not raw_code:
        return "eng"

    # Normalise: trim, lowercase, drop region subtag ("pt-BR" → "pt")
    code = raw_code.strip().lower().split('-')[0]

    # Already a 3-letter code — return as-is (Jellyfin uses ISO 639-2/T)
    if len(code) == 3:
        return code

    if len(code) != 2:
        return "eng"  # Malformed input — safe default

    if _HAS_PYCOUNTRY:
        lang = pycountry.languages.get(alpha_2=code)
        if lang:
            # alpha_3 is ISO 639-2/T (terminological), which Jellyfin uses.
            # e.g. German → "deu", French → "fra", Chinese → "zho"
            return lang.alpha_3

    # pycountry unavailable — use built-in fallback map
    return _FALLBACK_LANG_MAP.get(code, "eng")


def get_plex_libraries():
    headers = {"X-Plex-Token": PLEX_TOKEN}
    try:
        response = requests.get(f"{PLEX_URL}/library/sections", headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        print(f"[-] Error connecting to Plex: {e}")
        return []

    root = ET.fromstring(response.content)
    libraries = []
    type_map = {"movie": "movies", "show": "tvshows", "artist": "music", "photo": "photos"}

    for section in root.findall('Directory'):
        plex_type = section.get('type')
        if plex_type not in type_map:
            continue

        paths = [loc.get('path') for loc in section.findall('Location')]
        if not paths:
            continue

        plex_lang = section.get('language', 'en')

        libraries.append({
            "name": section.get('title'),
            "type": type_map[plex_type],
            "paths": paths,
            "language": convert_language_code(plex_lang)  # now handles any language
        })
    return libraries


def get_jellyfin_libraries():
    """Fetches existing virtual folders from Jellyfin."""
    headers = {"X-MediaBrowser-Token": JELLYFIN_API_KEY}
    try:
        response = requests.get(f"{JELLYFIN_URL}/Library/VirtualFolders", headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        folders = response.json()
        return {
            (folder.get("Name") or folder.get("name", "")).strip().lower()
            for folder in folders if folder
        }
    except Exception as e:
        print(f"[-] Error fetching existing libraries from Jellyfin: {e}")
        return set()


def sync_and_map_library(lib, existing_jellyfin_libs):
    headers = {
        "X-MediaBrowser-Token": JELLYFIN_API_KEY,
        "Content-Type": "application/json"
    }
    clean_name = lib["name"].strip()

    # === STEP 1: CREATE IF MISSING ===
    if clean_name.lower() not in existing_jellyfin_libs:
        url_create = f"{JELLYFIN_URL}/Library/VirtualFolders"
        params = {
            "name": clean_name,
            "collectionType": lib["type"],
            "refreshLibrary": "false"
        }
        body_create = {
            "name": clean_name,
            "collectionType": lib["type"]
        }
        try:
            requests.post(url_create, headers=headers, params=params, json=body_create, timeout=REQUEST_TIMEOUT)
            print(f"[*] Created missing library container: '{clean_name}'")
        except Exception as e:
            print(f"[-] Error creating library '{clean_name}': {e}")
            return
    else:
        print(f"[*] Library '{clean_name}' already exists. Updating settings and mappings.")

    # === STEP 2: UPDATE METADATA LANGUAGE ===
    url_options = f"{JELLYFIN_URL}/Library/VirtualFolders/LibraryOptions"
    body_options = {
        "Id": clean_name,
        "LibraryOptions": {
            "PreferredMetadataLanguage": lib["language"]
        }
    }
    try:
        res_lang = requests.post(url_options, headers=headers, json=body_options, timeout=REQUEST_TIMEOUT)
        if res_lang.status_code in [200, 204]:
            print(f"   [+] Synced metadata language to: {lib['language']}")
        else:
            print(f"   [-] Failed syncing language settings: {res_lang.status_code}")
    except Exception as e:
        print(f"   [-] Error sending language options request: {e}")

    # === STEP 3: UPDATE PATH MAPPINGS ===
    url_add_path = f"{JELLYFIN_URL}/Library/VirtualFolders/Paths"
    for path in lib["paths"]:

        # === DOCKER PATH MAPPING TRANSLATION (IF NEEDED) ===
        # path = path.replace("/volume1/Media/Movies", "/data/movies")
        # ====================================================

        body_path = {
            "Name": clean_name,
            "Path": path
        }
        try:
            res = requests.post(url_add_path, headers=headers, json=body_path, timeout=REQUEST_TIMEOUT)
            if res.status_code in [200, 204]:
                print(f"   [+] Attached/verified path: {path}")
            else:
                print(f"   [-] Failed attaching path {path}: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"   [-] Error sending path request for {path}: {e}")


def trigger_global_refresh():
    headers = {"X-MediaBrowser-Token": JELLYFIN_API_KEY}
    try:
        requests.post(f"{JELLYFIN_URL}/Library/Refresh", headers=headers, timeout=REQUEST_TIMEOUT)
        print("[+] Triggered global scan. Jellyfin is now parsing your files.")
    except Exception as e:
        print(f"[-] Failed to auto-trigger scan: {e}")


if __name__ == "__main__":
    if not _HAS_PYCOUNTRY:
        print("[!] pycountry not installed — using built-in fallback map (~60 languages).")
        print("[!] For full ISO 639 coverage, run: pip install pycountry\n")

    print("[*] Extracting library map structures and metadata rules from Plex...")
    plex_libs = get_plex_libraries()

    if not plex_libs:
        print("[-] No valid libraries extracted. Exiting.")
        exit(1)

    print("[*] Fetching existing libraries from Jellyfin...")
    existing_jellyfin_libs = get_jellyfin_libraries()

    print(f"[*] Syncing, updating options, and mapping {len(plex_libs)} libraries...")
    for lib in plex_libs:
        sync_and_map_library(lib, existing_jellyfin_libs)

    trigger_global_refresh()
