"""Le lanceur du jour J (« 1 - Lancer Club Pulse.command ») appelle ce script — à la main, rien à taper.

    python3 prototype/scripts/jour_j.py film        # trouve la vidéo du Bureau, la copie dans le deck, un voyant
    python3 prototype/scripts/jour_j.py jeton       # le jeton de console (~/.clubpulse/jeton, créé s'il manque)
    python3 prototype/scripts/jour_j.py attendre URL [secondes]   # attend qu'une adresse réponde (code 0 / 1)
    python3 prototype/scripts/jour_j.py preflight   # la check-list à voyants ; code 0 seulement si « FEU VERT v2 »
    python3 prototype/scripts/jour_j.py purger      # réinitialise la salle et vérifie qu'elle est vide (code 0 / 1)

Variables (tests) : CLUBPULSE_BUREAU, CLUBPULSE_DOSSIER, CLUBPULSE_FILM_DECK, CLUBPULSE_PORT, CLUBPULSE_PORT_DECK,
PUBLIC_BASE_URL. Bibliothèque standard seulement."""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import jour_j as jj  # noqa: E402


def _ports() -> tuple[str, str]:
    return os.environ.get("CLUBPULSE_PORT", "8000"), os.environ.get("CLUBPULSE_PORT_DECK", "8765")


def _salle(base: str, jeton: str) -> dict:
    try:
        req = urllib.request.Request(base + "/api/pulse/console/salle", headers={"X-Pulse-Console": jeton})
        with urllib.request.urlopen(req, timeout=4) as r:
            return json.load(r)
    except (OSError, ValueError):
        return {"injoignable": True}


def purger() -> int:
    """« Réinitialiser : tout effacer », puis vérification : plus aucun participant. Le jeton ne passe jamais en argument."""
    base = f"http://127.0.0.1:{_ports()[0]}"
    entetes = {"X-Pulse-Console": jj.jeton(jj.dossier())}
    try:
        urllib.request.urlopen(urllib.request.Request(base + "/api/pulse/console/salle/purger", data=b"", method="POST",
                                                      headers=entetes), timeout=5).close()
    except OSError as e:
        print(f"ÉCHEC : la salle n'a pas pu être réinitialisée ({e})")
        return 1
    etat = _salle(base, entetes["X-Pulse-Console"])
    if etat.get("participants") != 0 or etat.get("demande") or etat.get("invitee"):
        print(f"ÉCHEC : la salle n'est pas vide après la purge ({etat})")
        return 1
    print("salle réinitialisée : aucun participant, aucune réponse, aucun reçu")
    return 0


def preflight(couleurs: bool) -> int:
    port, port_deck = _ports()
    base = f"http://127.0.0.1:{port}"
    vs = jj.controles(bureau=jj.bureau(), cible=jj.cible_film(), dossier=jj.dossier(), base_locale=base,
                      base_publique=os.environ.get("PUBLIC_BASE_URL") or None,
                      deck_url=f"http://127.0.0.1:{port_deck}/v2.html", salle=_salle(base, jj.jeton(jj.dossier())),
                      sonde=jj.sonde_http, pmset=jj.pmset)
    print(jj.en_texte(vs, couleurs=couleurs).replace("http://127.0.0.1:8000/preflight", base + "/preflight"))
    return 0 if jj.verdict(vs)[0] == "FEU VERT v2" else 1


def main(argv: list[str]) -> int:
    couleurs = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    commande = argv[1] if len(argv) > 1 else "preflight"
    if commande == "film":
        v = jj.preparer_film(jj.bureau(), jj.cible_film(), jj.racine(), jj.dossier())
        print(jj.en_texte([v], couleurs=couleurs).split("\n")[3])     # la seule ligne du voyant
        return 0 if v.couleur != "rouge" else 1
    if commande == "jeton":
        print(jj.jeton(jj.dossier()))
        return 0
    if commande == "attendre":
        url, limite = argv[2], time.monotonic() + float(argv[3] if len(argv) > 3 else 30)
        while time.monotonic() < limite:
            if jj.sonde_http(url, delai=2.0):
                return 0
            time.sleep(0.5)
        return 1
    if commande == "preflight":
        return preflight(couleurs)
    if commande == "purger":
        return purger()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
