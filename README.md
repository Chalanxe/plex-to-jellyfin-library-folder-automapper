# Plex to Jellyfin Automapper

A lightweight Python utility to automatically reuse your Plex library structure and folder paths at Jellyfin. 

* If a library configuration exists in Plex but is **missing** in Jellyfin, it automatically creates the same.
* If the library **already exists** in Jellyfin, it bypasses creation but still updates and maps all corresponding media paths.
* Automatically syncs preferred metadata and country languages.*
  
> ℹ️ **Compatibility Note:** Tested only on Windows installations for both Plex and Jellyfin.

---

## ✨ Features

* **Automated Library Extraction:** Reads library names, collection types (`movies`, `tvshows`, `music`, `photos`), and underlying directory paths straight from your Plex server.
* **Smart Existence Checking:** Prevents duplicate library creation errors while ensuring paths are always up to date.
* **Path Mapping Expansion:** Appends new directory structures directly to existing Jellyfin Virtual Folders.
* **Full Language Support:** Automatically converts Plex language tags (ISO 639-1, BCP 47 regional tags like `en-US`) to Jellyfin-compatible ISO 639-2 codes for all ~500 languages in the ISO 639 standard. Requires `pycountry` — see [Dependencies](#-dependencies).
* **Metadata Language Sync:** Writes the resolved language code directly to each library's Jellyfin options so metadata providers fetch results in the correct language.
* **Automatic Library Scan:** Triggers a global Jellyfin refresh immediately after mapping is complete so your content populates right away.
* **Docker Ready:** Includes a commented translation section to adapt host-level paths to Docker container volumes if needed.

---

## 📦 Dependencies

The script requires only the Python standard library plus `requests`. Install with:

```bash
pip install requests
```

For full language support across all ~500 ISO 639 languages, also install `pycountry`:

```bash
pip install pycountry
```

> **Without `pycountry`:** The script falls back to a built-in map of ~60 common languages and prints a warning at startup. Everything still works — you will only hit the fallback limit if your library language is not in that set.

---

## ⚙️ Setup & Configuration

### 1. Open the script file
Open the script file (`plex-to-jellyfin-automapper.py`).

### 2. Update the configuration variables
Update the configuration variables at the very top of the script:

```python
# === CONFIGURATION ===
PLEX_URL = "http://YOUR_PLEX_IP:32400"
PLEX_TOKEN = "YOUR_PLEX_TOKEN"
JELLYFIN_URL = "http://YOUR_JELLYFIN_IP:8096"
JELLYFIN_API_KEY = "YOUR_JELLYFIN_API_KEY"
# =====================
```

### 🔑 Finding Your Credentials

* **Plex Token:** Follow the [Official Plex Guide](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) to locate your token using any media item's XML view.
* **Jellyfin API Key:** In your Jellyfin dashboard, navigate to **Administration** ➡️ **Dashboard** ➡️ **API Keys**, and create a new key (e.g., named `PlexSync`).

---

### 🐳 Docker Volume Translation (Optional)

If your Plex server utilizes native absolute paths (e.g., `/volume1/Media/Movies`) but Jellyfin runs inside a Docker container with a different volume mount (e.g., `/data/movies`), uncomment and modify the translation block inside the script:

```python
# === DOCKER PATH MAPPING TRANSLATION (IF NEEDED) ===
path = path.replace("/volume1/Media/Movies", "/data/movies")
# ====================================================
```

---

## 🚀 Usage

Execute the script directly from your terminal or command prompt:

```bash
python plex-to-jellyfin-automapper.py
```

### 📄 Expected Output Log

**With `pycountry` installed:**

```text
[*] Extracting library map structures and metadata rules from Plex...
[*] Fetching existing libraries from Jellyfin...
[*] Syncing, updating options, and mapping 3 libraries...
[*] Library 'Movies' already exists. Updating settings and mappings.
   [+] Synced metadata language to: eng
   [+] Attached/verified path: /$DriveA/$Media/Movies
   [+] Attached/verified path: /$DriveB/$Media/Movies
[*] Created missing library container: 'TV Shows'
   [+] Synced metadata language to: eng
   [+] Attached/verified path: /$Drive/$Media/TV Shows
[+] Triggered global scan. Jellyfin is now parsing your files.
```

**Without `pycountry` (fallback mode):**

```text
[!] pycountry not installed — using built-in fallback map (~60 languages).
[!] For full ISO 639 coverage, run: pip install pycountry

[*] Extracting library map structures and metadata rules from Plex...
...
```
