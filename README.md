# Plex to Jellyfin Automapper

A lightweight Python utility to automatically reuse your Plex library structure and folder paths at Jellyfin. 

* If a library configuration exists in Plex but is **missing** in Jellyfin, it automatically creates the same.
* If the library **already exists** in Jellyfin, it bypasses creation but still updates and maps all corresponding media paths.

> ℹ️ **Compatibility Note:** Tested only on Windows installations for both Plex and Jellyfin.

---

## ✨ Features

* **Automated Library Extraction:** Reads library names, collection types (`movies`, `tvshows`, `music`, `photos`), and underlying directory paths straight from your Plex server.
* **Smart Existence Checking:** Prevents duplicate library creation errors while ensuring paths are always up to date.
* **Path Mapping Expansion:** Appends new directory structures directly to existing Jellyfin Virtual Folders.
* **Automatic Library Scan:** Triggers a global Jellyfin refresh immediately after mapping is complete so your content populates right away.
* **Docker Ready:** Includes a commented translation section to adapt host-level paths to Docker container volumes if needed.

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
python -m plex-to-jellyfin-library-automapper.py
```

### 📄 Expected Output Log

```text
[*] Extracting library map structures from Plex...
[*] Fetching existing libraries from Jellyfin...
[*] Syncing and mapping 3 libraries...
[*] Library 'Movies' already exists. Proceeding to update path mappings.
   [+] Attached/verified path: /$DriveA/$Media/Movies
   [+] Attached/verified path: /$DriveB/$Media/Movies
[*] Created missing library container: 'TV Shows'
   [+] Attached/verified path: /$Drive/$Media/TV Shows
[+] Triggered global scan. Jellyfin is now parsing your files.
```
