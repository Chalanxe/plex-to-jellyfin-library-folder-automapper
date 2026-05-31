Setup & Configuration
Open the script file (plex-to-jellyfin-automapper.py) and update the configuration variables at the top of the file:

Python
# === CONFIGURATION ===
PLEX_URL = "http://YOUR_PLEX_IP:32400"
PLEX_TOKEN = "YOUR_PLEX_TOKEN"
JELLYFIN_URL = "http://YOUR_JELLYFIN_IP:8096"
JELLYFIN_API_KEY = "YOUR_JELLYFIN_API_KEY"
# =====================
Finding Your Credentials
Plex Token: Follow the Official Plex Guide to find your token via any media item's XML view.

Jellyfin API Key: In your Jellyfin dashboard, go to Administration -> Dashboard -> API Keys, and create a new key named something like "PlexSync".

Docker Volume Translation (Optional)
If your Plex server uses native absolute paths (e.g., /volume1/Media/Movies) but Jellyfin runs inside a Docker container using a different volume mount (e.g., /data/movies), uncomment and adapt the translation block inside the script:

Python
# === DOCKER PATH MAPPING TRANSLATION (IF NEEDED) ===
path = path.replace("/volume1/Media/Movies", "/data/movies")
# ====================================================
Usage
Run the script from your terminal or command prompt:

Bash
python -m plex-to-jellyfin-automapper

Expected Output Log
Plaintext
[*] Extracting library map structures from Plex...
[*] Fetching existing libraries from Jellyfin...
[*] Syncing and mapping 3 libraries...
[*] Library 'Movies' already exists. Proceeding to update path mappings.
   [+] Attached/verified path: /mnt/share/Movies
[*] Created missing library container: 'Anime Shows'
   [+] Attached/verified path: /mnt/share/Anime
[+] Triggered global scan. Jellyfin is now parsing your files.

License
This project is open-source and available under the MIT License. Feel free to modify and adapt it to your homelab environment!
"""
