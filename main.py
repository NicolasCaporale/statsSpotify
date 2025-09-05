from flask import Flask, redirect, request, session, url_for, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # sessione sicura per ogni utente

# ===========================
# CONFIGURAZIONE SPOTIFY
# ===========================
CLIENT_ID = os.getenv("9358ec7ac43144f9b4a46cfea80dc4b1")
CLIENT_SECRET = os.getenv("5fa2b039c36b47ada3e055b475034a59")
REDIRECT_URI = os.getenv("https://statsspotify.onrender.com/callback")  # es. https://tuo-dominio.render.com/callback

SCOPE = "user-top-read user-read-recently-played"
MAX_LIMIT = 30

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotifycache"
)

# ===========================
# FUNZIONI UTILI
# ===========================
def get_top(sp, category, time_range, max_limit=MAX_LIMIT):
    items = []
    limit = 50
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
            if offset >= max_limit:
                break
        return items[:max_limit]

    elif category == "album":
        # ricaviamo album dai top tracks
        top_tracks = []
        offset_tracks = 0
        while True:
            batch = sp.current_user_top_tracks(limit=limit, offset=offset_tracks, time_range=time_range)['items']
            if not batch:
                break
            top_tracks.extend(batch)
            offset_tracks += limit
            if offset_tracks >= max_limit*2:
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

def get_recently_played(sp, max_limit=MAX_LIMIT):
    recent = sp.current_user_recently_played(limit=max_limit)['items']
    result = []
    for item in recent:
        track = item['track']
        name = track['name']
        artist = ', '.join([a['name'] for a in track['artists']])
        result.append({"name": name, "artist": artist})
    return result

def format_top_items(items, category):
    formatted = []
    for item in items:
        if category == "track":
            formatted.append({
                "name": item['name'],
                "artists": [a['name'] for a in item['artists']]
            })
        elif category == "artist":
            formatted.append({
                "name": item['name']
            })
        elif category == "album":
            formatted.append({
                "name": item['name'],
                "artists": [a['name'] for a in item['artists']],
                "total_tracks": item['total_tracks']
            })
    return formatted

# ===========================
# ROUTE
# ===========================
@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info['access_token']
    sp = spotipy.Spotify(auth=access_token)
    session['access_token'] = access_token
    return redirect(url_for('stats'))

@app.route('/stats')
def stats():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth=access_token)

    time_ranges = {
        "short_term": "Ultime 4 settimane",
        "medium_term": "Ultimi 6 mesi",
        "long_term": "Lifetime"
    }

    categories = ["track", "artist", "album"]

    data = {}
    for tr_key, tr_label in time_ranges.items():
        data[tr_label] = {}
        for cat in categories:
            top_items = get_top(sp, cat, tr_key)
            data[tr_label][cat] = format_top_items(top_items, cat)

    data["recently_played"] = get_recently_played(sp)

    return jsonify(data)

if __name__ == "__main__":
    app.run()


