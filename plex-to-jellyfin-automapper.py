import requests
import xml.etree.ElementTree as ET

# === CONFIGURATION ===
PLEX_URL = "http://YOUR_PLEX_IP:32400"
PLEX_TOKEN = "YOUR_PLEX_TOKEN"
JELLYFIN_URL = "http://YOUR_JELLYFIN_IP:8096"
JELLYFIN_API_KEY = "YOUR_JELLYFIN_API_KEY"
# =====================

REQUEST_TIMEOUT = 10


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

        libraries.append({
            "name": section.get('title'),
            "type": type_map[plex_type],
            "paths": paths
        })
    return libraries


def get_jellyfin_libraries():
    """Fetches existing virtual folders from Jellyfin to determine if creation is needed."""
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
            "refreshLibrary": "false"  # Wait to refresh until paths are bound
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
            return  # Stop if creation failed completely
    else:
        print(f"[*] Library '{clean_name}' already exists. Proceeding to update path mappings.")

    # === STEP 2: ALWAYS UPDATE PATH MAPPINGS ===
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
    print("[*] Extracting library map structures from Plex...")
    plex_libs = get_plex_libraries()

    if not plex_libs:
        print("[-] No valid libraries extracted. Exiting.")
        exit(1)

    print("[*] Fetching existing libraries from Jellyfin...")
    existing_jellyfin_libs = get_jellyfin_libraries()

    print(f"[*] Syncing and mapping {len(plex_libs)} libraries...")
    for lib in plex_libs:
        sync_and_map_library(lib, existing_jellyfin_libs)

    trigger_global_refresh()
