import waitress
import os
from flask import Flask, render_template, request
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
