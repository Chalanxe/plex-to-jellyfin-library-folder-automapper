Tested only on windows installation for both plex and jellyfin.

## ⚙️ Setup & Configuration

#1. Open the script file (`plex-to-jellyfin-automapper.py`).

#2. Update the configuration variables at the very top of the script:

```python
# === CONFIGURATION ===
PLEX_URL = "http://YOUR_PLEX_IP:32400"
PLEX_TOKEN = "YOUR_PLEX_TOKEN"
JELLYFIN_URL = "http://YOUR_JELLYFIN_IP:8096"
JELLYFIN_API_KEY = "YOUR_JELLYFIN_API_KEY"
# =====================
```
##🔑 Finding Your Credentials

**Plex Token**: Follow the Official Plex Guide to locate your token using any media item's XML view.

**Jellyfin API Key**: In your Jellyfin dashboard, navigate to Administration ➡️ Dashboard ➡️ API Keys, and create a new key (e.g., named PlexSync).


🐳 Docker Volume Translation (Optional)
If your Plex server utilizes native absolute paths (e.g., /volume1/Media/Movies) but Jellyfin runs inside a Docker container with a different volume mount (e.g., /data/movies), uncomment and modify the translation block inside the script:

 DOCKER PATH MAPPING TRANSLATION (IF NEEDED)
path = path.replace("/volume1/Media/Movies", "/data/movies")

#3. 🚀 Usage
Execute the script directly from your terminal or command prompt:

```python
python plex-to-jellyfin-automapper.py
```

📄 Expected Output Log

```python
[*] Extracting library map structures from Plex...
[*] Fetching existing libraries from Jellyfin...
[*] Syncing and mapping 3 libraries...
[*] Library 'Movies' already exists. Proceeding to update path mappings.
   [+] Attached/verified path: /mnt/share/Movies
[*] Created missing library container: 'Anime Shows'
   [+] Attached/verified path: /mnt/share/Anime
[+] Triggered global scan. Jellyfin is now parsing your files.
```

📄 License
This project is open-source and available under the MIT License. Feel free to modify, distribute, and adapt it to your personal homelab environment!
