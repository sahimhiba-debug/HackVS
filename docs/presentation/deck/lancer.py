"""Lance le deck hors ligne : petit serveur local (127.0.0.1) + navigateur.

    python3 docs/presentation/deck/lancer.py          # puis F11 / plein écran

Pourquoi un serveur : ouvert en double-clic (file://), Chrome refuse de lire data/gel.json. Ici rien ne sort de la
machine : le serveur n'écoute que 127.0.0.1 et ne sert que ce dossier. Bibliothèque standard Python uniquement.
"""
import functools
import http.server
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> None:
    gestion = functools.partial(Muet, directory=str(DOSSIER))
    with socketserver.TCPServer(("127.0.0.1", PORT), gestion) as srv:
        url = f"http://127.0.0.1:{PORT}/index.html"
        print(f"Deck : {url}   (Ctrl+C pour arrêter)")
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        srv.serve_forever()


if __name__ == "__main__":
    main()
