"""Lance le deck hors ligne : petit serveur local (127.0.0.1) + navigateur.

    python3 docs/presentation/deck/lancer.py          # puis F11 / plein écran
    python3 docs/presentation/deck/lancer.py 8765 --sans-navigateur   # (lanceur du jour J)

Pourquoi un serveur : ouvert en double-clic (file://), Chrome refuse de lire data/gel.json. Ici rien ne sort de la
machine : le serveur n'écoute que 127.0.0.1 et ne sert que ce dossier. Bibliothèque standard Python uniquement.

Le serveur gère les requêtes par plages (« Range ») : Safari en a besoin pour lire une vidéo du tout, et Chrome pour
sauter à un moment du film (et relancer le film sans recharger la page).
"""
import functools
import http.server
import os
import re
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT = int(ARGS[0]) if ARGS else 8765
SANS_NAVIGATEUR = "--sans-navigateur" in sys.argv     # le lanceur du jour J ouvre lui-même Chrome
PLAGE = re.compile(r"bytes=(\d*)-(\d*)$")


class Deck(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        plage = PLAGE.match(self.headers.get("Range", "").strip())
        chemin = self.translate_path(self.path)
        if not plage or not os.path.isfile(chemin):
            return super().send_head()
        taille = os.path.getsize(chemin)
        debut_txt, fin_txt = plage.groups()
        if debut_txt:
            debut, fin = int(debut_txt), int(fin_txt) if fin_txt else taille - 1
        elif fin_txt:                                   # « bytes=-N » : les N derniers octets
            debut, fin = max(0, taille - int(fin_txt)), taille - 1
        else:
            return super().send_head()
        fin = min(fin, taille - 1)
        if debut > fin or debut >= taille:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{taille}")
            self.end_headers()
            return None
        f = open(chemin, "rb")
        f.seek(debut)
        self._reste = fin - debut + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(chemin))
        self.send_header("Content-Range", f"bytes {debut}-{fin}/{taille}")
        self.send_header("Content-Length", str(self._reste))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        reste = getattr(self, "_reste", None)
        if reste is None:
            return super().copyfile(source, outputfile)
        try:
            while reste > 0:
                bloc = source.read(min(64 * 1024, reste))
                if not bloc:
                    break
                outputfile.write(bloc)
                reste -= len(bloc)
        except (BrokenPipeError, ConnectionResetError):  # le navigateur abandonne une plage : normal pendant un saut
            pass
        finally:
            self._reste = None


class Serveur(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    gestion = functools.partial(Deck, directory=str(DOSSIER))
    with Serveur(("127.0.0.1", PORT), gestion) as srv:
        url = f"http://127.0.0.1:{PORT}/index.html"
        print(f"Deck : {url}   (Ctrl+C pour arrêter)")
        if not SANS_NAVIGATEUR:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        srv.serve_forever()


if __name__ == "__main__":
    main()
