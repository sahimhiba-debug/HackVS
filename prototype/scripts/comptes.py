"""ANNÉE 1 · LOT 2 — Amorcer le premier compte d'administration (une seule fois dans la vie du journal).

    HACKVS_ESSAIS_DB=<journal> HACKVS_SECRET=<secret du serveur> python scripts/comptes.py amorcer "Administration du Club"

Affiche UNE fois la session de l'administration (à coller dans l'en-tête X-Pulse-Compte). Elle n'est écrite nulle part.
Avant toute action d'administration (inviter, rôles, révoquer), cette session doit activer la double authentification
(POST /api/pulse/comptes/moi/totp/preparer puis /confirmer) et s'élever par un code (/moi/elever). Même journal et même
secret que le serveur : sinon la session ne vaudra rien."""
import hashlib
import hmac
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intelligence.comptes import Comptes  # noqa: E402
from intelligence.erreurs import ErreurMetier  # noqa: E402
from plateforme.memoire import Memoire  # noqa: E402


def main(a: list[str]) -> int:
    if len(a) < 2 or a[0] != "amorcer":
        print(__doc__)
        return 2
    secret, journal = os.environ.get("HACKVS_SECRET", ""), os.environ.get("HACKVS_ESSAIS_DB", "")
    if len(secret) < 32 or not journal:
        print("REFUSÉ : HACKVS_SECRET (32 caractères ou plus) et HACKVS_ESSAIS_DB (le journal du serveur) sont requis")
        return 1
    cle = hmac.new(secret.encode(), b"comptes|annee-1", hashlib.sha256).digest()
    try:
        session = Comptes(Memoire(journal), cle).amorcer_administration(a[1])
    except ErreurMetier as e:
        print(f"REFUSÉ : {e}")
        return 1
    print(f"Administration amorcée. Session (affichée une seule fois) :\n{session}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
