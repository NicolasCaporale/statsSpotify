from flask import Flask, redirect, request, session, url_for, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import jwt
import time

# Chiave segreta per firmare JWT
JWT_SECRET = os.urandom(24)
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600  # token valido 1 ora

# Mappa temporanea sul server (in memoria)
user_tokens = {}  # {user_jwt: access_token_spotify}

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ===========================
# CONFIGURAZIONE
# ===========================
SCOPE = "user-top-read user-read-recently-played"
MAX_LIMIT = 30

# ===========================
# FUNZIONI SPOTIFY
# ===========================
def get_sp_oauth():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        raise Exception("Le variabili d'ambiente Spotify non sono impostate!")

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_path=".spotifycache"
    )
    def generate_jwt(access_token):
    payload = {
        "access_token": access_token,
        "exp": int(time.time()) + JWT_EXP_DELTA_SECONDS
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    user_tokens[token] = access_token
    return token


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
    sp_oauth = get_sp_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    sp_oauth = get_sp_oauth()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info['access_token']

    # genera JWT da restituire all'app
    user_token = generate_jwt(access_token)

    # ritorna JSON all'app nativa
    return jsonify({"token": user_token})


@app.route('/stats')
def stats():
    user_token = request.headers.get("Authorization")
    if not user_token:
        return jsonify({"error": "Token mancante"}), 401

    access_token = user_tokens.get(user_token)
    if not access_token:
        return jsonify({"error": "Token non valido o scaduto"}), 401

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


# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run()


