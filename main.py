from flask import Flask, redirect, request, session, jsonify, send_from_directory
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # per sessioni sicure

SCOPE = "user-top-read user-read-recently-played"

# ===========================
# FUNZIONE PER LEGGERE CREDENZIALI
# ===========================
# ===========================
# CREDENZIALI SPOTIFY HARD-CODATE
# ===========================
CLIENT_ID = "9358ec7ac43144f9b4a46cfea80dc4b1"
CLIENT_SECRET = "5fa2b039c36b47ada3e055b475034a59"
REDIRECT_URI = "https://statsspotify.onrender.com/callback"

# ===========================
# ROUTE FRONT-END
# ===========================
@app.route("/")
def index():
    if "token_info" in session:
        return redirect("/dashboard.html")
    return send_from_directory("static", "login.html")  # login.html nella cartella static

@app.route("/dashboard.html")
def dashboard():
    return send_from_directory("static", "dashboard.html")

# ===========================
# ROUTE OAUTH
# ===========================
@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE
    )
    code = request.args.get('code')
    if not code:
        return "Errore: nessun codice ricevuto da Spotify", 400

    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect("/dashboard.html")

# ===========================
# HELPER CLIENT SPOTIFY
# ===========================
def get_spotify_client():
    token_info = session.get("token_info", None)
    if not token_info:
        return None
    return Spotify(auth=token_info['access_token'])

# ===========================
# ROUTE API
# ===========================
@app.route("/api/recent")
def recent_tracks():
    sp = get_spotify_client()
    if not sp:
        return jsonify({"error": "non autenticato"}), 401

    recent = sp.current_user_recently_played(limit=30)['items']
    result = []
    for item in recent:
        track = item['track']
        result.append({
            "name": track['name'],
            "artists": [a['name'] for a in track['artists']],
            "album": track['album']['name'],
            "id": track['id'],
            "image": track['album']['images'][0]['url'] if track['album']['images'] else None
        })
    return jsonify(result)

@app.route("/api/top/<category>/<time_range>")
def top_items(category, time_range):
    sp = get_spotify_client()
    if not sp:
        return jsonify({"error": "non autenticato"}), 401

    limit = 30
    items = []

    if category == "track":
        items = sp.current_user_top_tracks(limit=limit, time_range=time_range)['items']
        result = [{
            "name": t['name'],
            "artists": [a['name'] for a in t['artists']],
            "id": t['id'],
            "image": t['album']['images'][0]['url'] if t['album']['images'] else None
        } for t in items]

    elif category == "artist":
        items = sp.current_user_top_artists(limit=limit, time_range=time_range)['items']
        result = [{
            "name": a['name'],
            "id": a['id'],
            "image": a['images'][0]['url'] if a['images'] else None
        } for a in items]

    elif category == "album":
        top_tracks = sp.current_user_top_tracks(limit=50, time_range=time_range)['items']
        albums = []
        seen = set()
        for t in top_tracks:
            album = t['album']
            album_id = album['id']
            if album_id not in seen and album['total_tracks'] > 1 and album['album_type'] == 'album':
                albums.append(album)
                seen.add(album_id)
        result = [{
            "name": a['name'],
            "artists": [ar['name'] for ar in a['artists']],
            "id": a['id'],
            "image": a['images'][0]['url'] if a['images'] else None
        } for a in albums[:limit]]
    else:
        return jsonify({"error": "categoria non valida"}), 400

    return jsonify(result)

# ===========================
# ROUTA DI DEBUG ENV (opzionale)
# ===========================
@app.route("/env")
def show_env():
    try:
        return jsonify({
            "CLIENT_ID": client_id[:4] + "***",
            "CLIENT_SECRET": client_secret[:4] + "***",
            "REDIRECT_URI": redirect_uri
        })
    except Exception as e:
        return str(e), 500

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888)

