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
    Convert Plex language tags to a clean unified string format.
    Preserves regional hyphens so they can be parsed out cleanly later.
    """
    if not raw_code:
        return "en"
    trimmed = raw_code.strip()
    if "-" in trimmed:
        parts = trimmed.split('-')
        return f"{parts[0].lower()}-{parts[1].upper()}"
    return trimmed.lower()


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
            "language": convert_language_code(plex_lang)
        })
    return libraries


def get_jellyfin_libraries():
    headers = {"X-MediaBrowser-Token": JELLYFIN_API_KEY}
    try:
        response = requests.get(f"{JELLYFIN_URL}/Library/VirtualFolders", headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        folders = response.json()
        return {
            (f.get("Name") or f.get("name", "")).strip().lower(): f
            for f in folders if f
        }
    except Exception as e:
        print(f"[-] Error fetching existing libraries from Jellyfin: {e}")
        return {}


def safe_set_key(options_dict, pascal_key, value):
    """
    Safely sets a configuration key by checking whether the server 
    prefers camelCase or PascalCase, avoiding duplicate key collisions.
    """
    camel_key = pascal_key[0].lower() + pascal_key[1:]
    if camel_key in options_dict:
        options_dict[camel_key] = value
        options_dict.pop(pascal_key, None)
    else:
        options_dict[pascal_key] = value
        options_dict.pop(camel_key, None)


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
            print(f"[*] Created missing library container: '{clean_name}'", flush=True)
        except Exception as e:
            print(f"[-] Error creating library '{clean_name}': {e}", flush=True)
            return
        
        # Re-fetch libraries so we obtain the newly generated GUID (ItemId)
        existing_jellyfin_libs = get_jellyfin_libraries()
    else:
        print(f"[*] Library '{clean_name}' already exists. Updating settings and mappings.", flush=True)

    folder_info = existing_jellyfin_libs.get(clean_name.lower(), {})
    
    # CRITICAL: We MUST use the GUID (ItemId) to target the APIs
    item_id = folder_info.get("ItemId") or folder_info.get("itemId")
    
    if not item_id:
        print(f"   [-] Could not locate internal GUID for '{clean_name}'. Skipping.", flush=True)
        return

    # === STEP 2: PARSE & SPLIT LANGUAGES ===
    raw_lang = str(lib.get("language", "en")).strip()

    if "-" in raw_lang:
        parts = raw_lang.split("-")
        base_lang = parts[0].lower()       
        country_code = parts[1].upper()    
    else:
        base_lang = raw_lang.lower()
        country_code = ""

    # Down-convert 3-letter strings to 2-letter codes for Metadata dropdown matching
    if len(base_lang) == 3:
        if _HAS_PYCOUNTRY:
            lang_obj = pycountry.languages.get(alpha_3=base_lang) or pycountry.languages.get(bibliographic=base_lang)
            if lang_obj and hasattr(lang_obj, 'alpha_2'):
                base_lang = lang_obj.alpha_2
        else:
            for a2, a3 in _FALLBACK_LANG_MAP.items():
                if a3 == base_lang:
                    base_lang = a2
                    break

    # Subtitles explicitly require 3-letter identifiers (e.g. "eng")
    if len(base_lang) == 2:
        if _HAS_PYCOUNTRY:
            lang_obj = pycountry.languages.get(alpha_2=base_lang)
            sub_lang = lang_obj.alpha_3 if lang_obj else _FALLBACK_LANG_MAP.get(base_lang, "eng")
        else:
            sub_lang = _FALLBACK_LANG_MAP.get(base_lang, "eng")
    else:
        sub_lang = base_lang

    # === STEP 3: UPDATE SCANNER CONFIGURATIONS (Dashboard -> Manage Library) ===
    existing_lib_opts = folder_info.get("LibraryOptions") or folder_info.get("libraryOptions") or {}

    safe_set_key(existing_lib_opts, "PreferredMetadataLanguage", base_lang)
    safe_set_key(existing_lib_opts, "PreferredImageLanguage", base_lang)
    safe_set_key(existing_lib_opts, "MetadataCountryCode", country_code)
    safe_set_key(existing_lib_opts, "SubtitleDownloadLanguages", [sub_lang] if sub_lang else [])

    body_options = {
        "Id": item_id,
        "LibraryOptions": existing_lib_opts
    }

    url_options = f"{JELLYFIN_URL}/Library/VirtualFolders/LibraryOptions"
    try:
        res_lang = requests.post(url_options, headers=headers, json=body_options, timeout=REQUEST_TIMEOUT)
        if res_lang.status_code in [200, 204]:
            print(f"   [+] Synced Scanner settings -> Metadata: '{base_lang}', Region: '{country_code}' (Subs: '{sub_lang}')", flush=True)
        else:
            print(f"   [-] Failed syncing Scanner settings: {res_lang.status_code} - {res_lang.text}", flush=True)
    except Exception as e:
        print(f"   [-] Error sending language options request: {e}", flush=True)


    # === STEP 4: UPDATE METADATA MANAGER ENTITY (Metadata Manager -> Media -> Library) ===
    # Jellyfin's Items API strictly requires a UserId context to retrieve a single item without throwing a 400.
    try:
        # 1. Fetch an admin user ID to provide an authorized route context
        res_users = requests.get(f"{JELLYFIN_URL}/Users", headers=headers, timeout=REQUEST_TIMEOUT)
        if res_users.status_code == 200 and res_users.json():
            # Grab the first user's ID
            user_id = res_users.json()[0].get("Id") or res_users.json()[0].get("id")
            
            # 2. Fetch the entire original item so we don't accidentally wipe its other properties
            url_item = f"{JELLYFIN_URL}/Users/{user_id}/Items/{item_id}"
            res_item = requests.get(url_item, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if res_item.status_code == 200:
                item_data = res_item.json()
                
                # Use safe_set_key to apply the matching JSON casing that Jellyfin returned
                safe_set_key(item_data, "PreferredMetadataLanguage", base_lang)
                safe_set_key(item_data, "PreferredMetadataCountryCode", country_code)
                
                # 3. Post the fully updated item entity back to the database
                url_update = f"{JELLYFIN_URL}/Items/{item_id}"
                res_item_post = requests.post(url_update, headers=headers, json=item_data, timeout=REQUEST_TIMEOUT)
                
                if res_item_post.status_code in [200, 204]:
                    print(f"   [+] Synced Metadata Manager entity to match language settings.", flush=True)
                else:
                    print(f"   [-] Failed updating Metadata Manager entity: {res_item_post.status_code} - {res_item_post.text}", flush=True)
            else:
                print(f"   [-] Failed to fetch Metadata Manager entity for '{clean_name}'. Status Code: {res_item.status_code}", flush=True)
        else:
             print(f"   [-] Could not resolve User ID for API lookup. Status: {res_users.status_code}", flush=True)
    except Exception as e:
        print(f"   [-] Error interacting with Items API: {e}", flush=True)


    # === STEP 5: UPDATE PATH MAPPINGS ===
    url_add_path = f"{JELLYFIN_URL}/Library/VirtualFolders/Paths"
    for path in lib["paths"]:
        body_path = {
            "name": clean_name,
            "path": path
        }
        try:
            res = requests.post(url_add_path, headers=headers, json=body_path, timeout=REQUEST_TIMEOUT)
            if res.status_code in [200, 204]:
                print(f"   [+] Attached/verified path: {path}", flush=True)
            else:
                print(f"   [-] Failed attaching path {path}: {res.status_code} - {res.text}", flush=True)
        except Exception as e:
            print(f"   [-] Error sending path request for {path}: {e}", flush=True)


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
