import spotipy
from spotipy.oauth2 import SpotifyOAuth

# ===========================
# CREDENZIALI
# ===========================
CLIENT_ID = "9358ec7ac43144f9b4a46cfea80dc4b1"
CLIENT_SECRET = "5fa2b039c36b47ada3e055b475034a59"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-top-read user-read-recently-played"

# ===========================
# AUTENTICAZIONE
# ===========================
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

# ===========================
# FUNZIONI UTILI
# ===========================
def print_top_items(items, category):
    for i, item in enumerate(items):
        if category == "track":
            name = item['name']
            artist = ', '.join([a['name'] for a in item['artists']])
            print(f"{i+1}. {name} - {artist}")
        elif category == "artist":
            print(f"{i+1}. {item['name']}")
        elif category == "album":
            name = item['name']
            artist = ', '.join([a['name'] for a in item['artists']])
            print(f"{i+1}. {name} - {artist}")
    print("\n")

def get_top(category, time_range, max_limit=30):
    items = []
    limit = 50  # massimo consentito dall'API
    offset = 0

    if category in ["track", "artist"]:
        while True:
            if category == "track":
                response = sp.current_user_top_tracks(limit=limit, offset=offset, time_range=time_range)
            else:
                response = sp.current_user_top_artists(limit=limit, offset=offset, time_range=time_range)

            batch = response['items']
            if not batch:
                break
            items.extend(batch)
            offset += limit
            if offset >= max_limit:  # fermati a max_limit
                break
        return items[:max_limit]

    elif category == "album":
        # Prendiamo top tracks fino a max_limit * 2 per coprire più album
        top_tracks = []
        offset_tracks = 0
        while True:
            batch = sp.current_user_top_tracks(limit=limit, offset=offset_tracks, time_range=time_range)['items']
            if not batch:
                break
            top_tracks.extend(batch)
            offset_tracks += limit
            if offset_tracks >= max_limit*2:  # sicurezza
                break

        albums = []
        seen = set()
        for track in top_tracks:
            album = track['album']
            album_id = album['id']
            if album_id not in seen and album['total_tracks'] > 1 and album['album_type'] == 'album':
                albums.append(album)
                seen.add(album_id)
        return albums[:max_limit]

def get_recently_played(limit=30):
    recent = sp.current_user_recently_played(limit=limit)['items']
    result = []
    for item in recent:
        track = item['track']
        name = track['name']
        artist = ', '.join([a['name'] for a in track['artists']])
        result.append(f"{name} - {artist}")
    return result

# ===========================
# MAIN
# ===========================
time_ranges = {
    "Ultime 4 settimane": "short_term",
    "Ultimi 6 mesi": "medium_term",
    "Lifetime": "long_term"
}

categories = ["track", "artist", "album"]

# Top brani, artisti e album
for label, tr in time_ranges.items():
    print(f"====== {label} ======")
    for cat in categories:
        print(f"--- Top {cat}s ---")
        items = get_top(cat, tr, max_limit=30)
        print_top_items(items, cat)

# Brani ascoltati di recente
print("====== Brani ascoltati di recente ======")
recent_tracks = get_recently_played(limit=30)
for i, track in enumerate(recent_tracks):
    print(f"{i+1}. {track}")
