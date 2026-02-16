import waitress
import os
import json
from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
from flask_minify import Minify
import asyncio
import threading
import socket
from websockets import serve

from freetar.ug import Search, ug_tab
from freetar.utils import get_version, FreetarError
from freetar.websocket import ws_manager

cache = Cache(config={'CACHE_TYPE': 'SimpleCache',
                      "CACHE_DEFAULT_TIMEOUT": 0,
                      "CACHE_THRESHOLD": 10000})

app = Flask(__name__)
cache.init_app(app)
Minify(app=app, html=True, js=True, cssless=True)

# Global variable to track WebSocket server
_websocket_server = None
_websocket_thread = None

# Global variable to store the last shared song
last_shared_song = None

# Global variable to store recent shares (list of recent songs)
recent_shares = []
MAX_RECENT_SHARES = 100

# Global variable to store shared favorites
shared_favorites = {}

# Data file paths — stored in ./data relative to working directory
DATA_DIR = os.path.join(".", "data")
os.makedirs(DATA_DIR, exist_ok=True)
FAVORITES_FILE = os.path.join(DATA_DIR, "freetar_favorites.json")
RECENT_SHARES_FILE = os.path.join(DATA_DIR, "freetar_recent_shares.json")

def load_favorites():
    """Load favorites from JSON file"""
    global shared_favorites
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r') as f:
                shared_favorites = json.load(f)
                print(f"Loaded {len(shared_favorites)} favorites from {FAVORITES_FILE}")
        else:
            shared_favorites = {}
            print(f"No favorites file found, starting with empty favorites")
    except Exception as e:
        print(f"Error loading favorites: {e}")
        shared_favorites = {}

def save_favorites():
    """Save favorites to JSON file"""
    try:
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(shared_favorites, f, indent=2)
        print(f"Saved {len(shared_favorites)} favorites to {FAVORITES_FILE}")
    except Exception as e:
        print(f"Error saving favorites: {e}")

def load_recent_shares():
    """Load recent shares from JSON file"""
    global recent_shares
    try:
        if os.path.exists(RECENT_SHARES_FILE):
            with open(RECENT_SHARES_FILE, 'r') as f:
                recent_shares = json.load(f)
                print(f"Loaded {len(recent_shares)} recent shares from {RECENT_SHARES_FILE}")
        else:
            recent_shares = []
            print(f"No recent shares file found, starting with empty list")
    except Exception as e:
        print(f"Error loading recent shares: {e}")
        recent_shares = []

def save_recent_shares():
    """Save recent shares to JSON file"""
    try:
        with open(RECENT_SHARES_FILE, 'w') as f:
            json.dump(recent_shares, f, indent=2)
        print(f"Saved {len(recent_shares)} recent shares to {RECENT_SHARES_FILE}")
    except Exception as e:
        print(f"Error saving recent shares: {e}")

# Load favorites from disk on startup
load_favorites()

# Load recent shares from disk on startup
load_recent_shares()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@app.context_processor
def export_variables():
    return {
        'version': get_version(),
    }


@app.route("/")
def index():
    return render_template("index.html", favs=True)


@app.route("/search")
@cache.cached(query_string=True)
def search():
    search_term = request.args.get("search_term")
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        return render_template('error.html',
                               error="Invalid page requested. Not a number.")
    search_results = None
    if search_term:
        search_results = Search(search_term, page)
    return render_template("index.html",
                           search_term=search_term,
                           title=f"Freetar - Search: {search_term}",
                           search_results=search_results)


@app.route("/tab/<artist>/<song>")
@cache.cached()
def show_tab(artist: str, song: str):
    tab = ug_tab(f"{artist}/{song}")
    return render_template("tab.html",
                           tab=tab,
                           title=f"{tab.artist_name} - {tab.song_name}")


@app.route("/tab/<tabid>")
@cache.cached()
def show_tab2(tabid: int):
    tab = ug_tab(tabid)
    return render_template("tab.html",
                           tab=tab,
                           title=f"{tab.artist_name} - {tab.song_name}")


@app.route("/favs")
def show_favs():
    return render_template("index.html",
                           title="Freetar - Favorites",
                           favs=True)


@app.route("/live")
def show_live():
    """Show the live session page with recent shares"""
    global recent_shares
    
    # Check if there's been activity in the past 20 minutes
    live_session_active = False
    filtered_shares = []
    
    if recent_shares:
        from datetime import datetime, timedelta
        current_time = datetime.now()
        twenty_minutes_ago = current_time - timedelta(minutes=20)
        
        try:
            most_recent = recent_shares[0]
            most_recent_time = datetime.fromisoformat(most_recent["timestamp"])
            
            if most_recent_time >= twenty_minutes_ago:
                live_session_active = True
                
            # Filter shares to only show those from the past 20 minutes
            for share in recent_shares:
                share_time = datetime.fromisoformat(share["timestamp"])
                if share_time >= twenty_minutes_ago:
                    filtered_shares.append(share)
                    
        except Exception as e:
            print(f"Error checking live session activity: {e}")
    
    return render_template("live.html",
                           title="Freetar - Live Session",
                           live_session_active=live_session_active,
                           recent_shares=filtered_shares)


@app.route("/api/live", methods=["GET"])
def get_live():
    """Get the recent shared songs"""
    global recent_shares
    if recent_shares:
        from datetime import datetime, timedelta
        
        # Check if the most recent share is within 5 minutes
        try:
            most_recent = recent_shares[0]
            share_time = datetime.fromisoformat(most_recent["timestamp"])
            current_time = datetime.now()
            time_diff = current_time - share_time
            
            # Only show banner if most recent share is within 5 minutes
            if time_diff <= timedelta(minutes=5):
                return jsonify({"shares": recent_shares, "show_banner": True})
            else:
                return jsonify({"shares": recent_shares, "show_banner": False})
        except Exception as e:
            print(f"Error checking timestamp: {e}")
            return jsonify({"shares": recent_shares, "show_banner": False})
    else:
        return jsonify({"shares": []}), 404


@app.route("/api/live", methods=["POST"])
def set_live():
    """Add a song to recent shares"""
    global recent_shares
    data = request.get_json()
    if data and "url" in data:
        from datetime import datetime
        
        # Use provided artist and song names, with URL parsing as fallback
        url = data["url"]
        artist_name = data.get("artist_name", "Unknown Artist")
        song_name = data.get("song_name", "Unknown Song")
        
        # If names weren't provided, try to parse from URL as fallback
        if artist_name == "Unknown Artist" and song_name == "Unknown Song":
            import urllib.parse
            url_parts = url.strip('/').split('/')
            if len(url_parts) >= 3 and url_parts[0] == 'tab':
                try:
                    artist_name = urllib.parse.unquote(url_parts[1]).replace('-', ' ').replace('_', ' ')
                    song_name = urllib.parse.unquote(url_parts[2]).replace('-', ' ').replace('_', ' ')
                except Exception as e:
                    print(f"Error parsing URL {url}: {e}")
        
        # Remove if already exists to avoid duplicates
        recent_shares = [share for share in recent_shares if share["url"] != url]
        
        # Add new share at the beginning with current timestamp and names
        new_share = {
            "url": url,
            "artist_name": artist_name,
            "song_name": song_name,
            "timestamp": datetime.now().isoformat()
        }
        recent_shares.insert(0, new_share)
        
        # Keep only the most recent shares
        recent_shares = recent_shares[:MAX_RECENT_SHARES]
        
        # Save to disk
        save_recent_shares()
        
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400


@app.route("/favorites", methods=["GET"])
def get_favorites():
    """Get all shared favorites"""
    global shared_favorites
    return jsonify(shared_favorites)


@app.route("/favorites", methods=["POST"])
def add_favorite():
    """Add a song to shared favorites"""
    global shared_favorites
    data = request.get_json()
    if data and "tab_url" in data:
        fav = {
            "artist_name": data.get("artist_name", ""),
            "song": data.get("song", ""),
            "type": data.get("type", ""),
            "rating": data.get("rating", ""),
            "tab_url": data["tab_url"]
        }
        shared_favorites[data["tab_url"]] = fav
        save_favorites()  # Save to disk
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400


@app.route("/favorites", methods=["DELETE"])
def remove_favorite():
    """Remove a song from shared favorites"""
    global shared_favorites
    data = request.get_json()
    if data and "tab_url" in data and data["tab_url"] in shared_favorites:
        del shared_favorites[data["tab_url"]]
        save_favorites()  # Save to disk
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400


@app.route("/about")
def show_about():
    return render_template('about.html')


@app.errorhandler(403)
@app.errorhandler(500)
@app.errorhandler(FreetarError)
def internal_error(error):
    search_term = request.args.get("search_term")
    return render_template('error.html',
                           search_term=search_term,
                           error=error)


async def websocket_server(host: str, port: int):
    try:
        async with serve(ws_manager.register, host, port):
            print(f"WebSocket server successfully started on ws://{host}:{port}")
            await asyncio.Future()  # run forever
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"Port {port} already in use, WebSocket server not started")
        else:
            print(f"Error starting WebSocket server: {e}")

def run_websocket_server(host: str, port: int):
    # Only start if port is not in use
    if not is_port_in_use(port):
        asyncio.run(websocket_server(host, port))
    else:
        print(f"Port {port} already in use, skipping WebSocket server startup")

def start_websocket_server(host: str, port: int):
    global _websocket_thread
    if _websocket_thread is None or not _websocket_thread.is_alive():
        _websocket_thread = threading.Thread(target=run_websocket_server, args=(host, port))
        _websocket_thread.daemon = True
        _websocket_thread.start()

def main():
    host = "0.0.0.0"
    port = 22001
    ws_port = 22002
    
    if __name__ == '__main__':
        # Only start WebSocket server in main process (not in Flask reloader)
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            start_websocket_server(host, ws_port)
        
        app.run(debug=True,
                host=host,
                port=port)
    else:
        # Production mode
        start_websocket_server(host, ws_port)
        
        threads = os.environ.get("THREADS", "4")
        print(f"Running backend on {host}:{port} with {threads} threads")
        waitress.serve(app, listen=f"{host}:{port}", threads=threads)


if __name__ == '__main__':
    main()
