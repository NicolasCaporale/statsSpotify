from flask import Flask, redirect, request, session, jsonify, send_from_directory
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # per sessioni sicure

# Credenziali Spotify (meglio mettere come ENV VARIABLES su Render)
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")


SCOPE = "user-top-read user-read-recently-played"

# ===========================
# ROUTE FRONT-END
# ===========================
@app.route("/")
def index():
    # Se utente già loggato, reindirizza a dashboard
    if "token_info" in session:
        return redirect("/dashboard.html")
    return send_from_directory("static", "login.html")  # login.html nella cartella static

@app.route("/dashboard.html")
def dashboard():
    # Serve la pagina dashboard front-end
    return send_from_directory("static", "dashboard.html")

# ===========================
# ROUTE OAUTH
# ===========================
@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/env")
def show_env():
    return {
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET[:4] + "***",  # nasconde il resto
        "REDIRECT_URI": REDIRECT_URI
    }


@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    
    # Salva token nella sessione
    session["token_info"] = token_info
    return redirect("/dashboard.html")  # dopo login va al front-end

# ===========================
# ROUTE PER API FRONT-END
# ===========================
def get_spotify_client():
    token_info = session.get("token_info", None)
    if not token_info:
        return None
    return Spotify(auth=token_info['access_token'])

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
            "id": track['id']
        })
    return jsonify(result)

@app.route("/api/top/<category>/<time_range>")
def top_items(category, time_range):
    sp = get_spotify_client()
    if not sp:
        return jsonify({"error": "non autenticato"}), 401

    limit = 30  # massimo ricavabile
    items = []

    if category == "track":
        items = sp.current_user_top_tracks(limit=limit, time_range=time_range)['items']
        result = [{"name": t['name'], "artists": [a['name'] for a in t['artists']], "id": t['id']} for t in items]
    elif category == "artist":
        items = sp.current_user_top_artists(limit=limit, time_range=time_range)['items']
        result = [{"name": a['name'], "id": a['id']} for a in items]
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
        result = [{"name": a['name'], "artists": [ar['name'] for ar in a['artists']], "id": a['id']} for a in albums[:limit]]
    else:
        return jsonify({"error": "categoria non valida"}), 400

    return jsonify(result)

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888)



