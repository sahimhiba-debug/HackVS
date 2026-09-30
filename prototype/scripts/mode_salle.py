"""MODE SALLE : exécute une commande (les E2E) comme dans la salle de la Foire, réseau LOCAL seul et IA OFF.

    sudo unshare --net python scripts/mode_salle.py -- python -m pytest -q tests/test_e2e_*.py

`unshare --net` donne au processus un espace réseau VIDE ; ce script y lève la boucle locale (127.0.0.1), PROUVE que
l'extérieur est injoignable (connexion IP directe et résolution de nom), retire toute configuration du fournisseur de
langage, puis lance la commande avec HACKVS_MODE_SALLE=1 (la fixture E2E vérifie alors que le serveur dit « IA non
configurée »). Si l'isolement n'est pas réel, le script ÉCHOUE au lieu de prétendre."""
from __future__ import annotations

import fcntl
import os
import socket
import struct
import sys

SIOCGIFFLAGS, SIOCSIFFLAGS, IFF_UP = 0x8913, 0x8914, 0x1


def lever_boucle_locale() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        drapeaux = struct.unpack("16sH", fcntl.ioctl(s, SIOCGIFFLAGS, struct.pack("16sH", b"lo", 0)))[1]
        fcntl.ioctl(s, SIOCSIFFLAGS, struct.pack("16sH", b"lo", drapeaux | IFF_UP))


def exterieur_joignable() -> list[str]:
    joignables = []
    for hote in ("1.1.1.1", "8.8.8.8"):
        try:
            socket.create_connection((hote, 443), timeout=2).close()
            joignables.append(hote)
        except OSError:
            pass
    try:
        socket.getaddrinfo("example.org", 443)
        joignables.append("résolution DNS")
    except OSError:
        pass
    return joignables


def main(argv: list[str]) -> int:
    commande = argv[argv.index("--") + 1:] if "--" in argv else argv
    if not commande:
        print(__doc__)
        return 2
    lever_boucle_locale()
    fuites = exterieur_joignable()
    if fuites:
        print(f"MODE SALLE REFUSÉ : l'extérieur est joignable ({', '.join(fuites)}). Lancer sous `unshare --net`.", file=sys.stderr)
        return 3
    env = {k: v for k, v in os.environ.items() if not k.startswith("APERTUS_") and k not in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy")}
    env |= {"HACKVS_MODE_SALLE": "1", "HACKVS_SEMANTIQUE": "0"}
    print("mode salle : réseau local seul (extérieur injoignable, vérifié), IA OFF (aucune configuration APERTUS_*)", flush=True)
    os.execvpe(commande[0], commande, env)
    return 0  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
