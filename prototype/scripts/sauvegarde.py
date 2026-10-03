"""ANNÉE 1 · LOT 1 — Sauvegarder, vérifier, restaurer, migrer le journal (SQLite ou PostgreSQL).

    python scripts/sauvegarde.py sauvegarder <adresse du journal> <fichier.jsonl>
    python scripts/sauvegarde.py verifier <fichier.jsonl>
    python scripts/sauvegarde.py restaurer <adresse d'un journal VIDE> <fichier.jsonl>
    python scripts/sauvegarde.py migrer <adresse> [niveau] [--confirmer-destruction]

Adresse : un chemin SQLite (ex. var/club_pulse.db) ou postgresql://… — jamais un mot de passe dans un fichier du dépôt :
passez-le par l'environnement (PGPASSWORD) ou un fichier ~/.pgpass."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plateforme import migrations, sauvegarde  # noqa: E402
from plateforme.memoire import Memoire  # noqa: E402
from plateforme.stockage import ouvrir  # noqa: E402


def _journal_existant(adresse: str) -> Memoire:
    """Audit M3 : une faute de frappe dans l'adresse créait une base VIDE et une sauvegarde « valide » de 0 fait. On
    exige un journal qui existe, et on le lit sans le migrer."""
    if "://" not in adresse and not Path(adresse).is_file():
        raise ValueError(f"aucun journal à cette adresse : {adresse}")
    if not ouvrir(adresse).table_existe("evenements"):
        raise ValueError(f"cette base n'a pas de journal (table « evenements » absente) : {adresse}")
    return Memoire(adresse, migrer_schema=False)


def main(a: list[str]) -> int:
    if len(a) >= 3 and a[0] == "sauvegarder":
        e = sauvegarde.sauvegarder(_journal_existant(a[1]), a[2])
        print(f"sauvegardé : {e['nombre']} faits · empreinte {e['empreinte'][:16]}… → {a[2]}")
        return 0
    if len(a) >= 2 and a[0] == "verifier":
        e, _ = sauvegarde.lire(a[1])
        print(f"valide : {e['nombre']} faits · empreinte {e['empreinte'][:16]}…")
        return 0
    if len(a) >= 3 and a[0] == "restaurer":
        e = sauvegarde.restaurer(Memoire(a[1]), a[2])
        print(f"restauré : {e['nombre']} faits · empreinte vérifiée")
        return 0
    if len(a) >= 2 and a[0] == "migrer":
        niveaux = [x for x in a[2:] if not x.startswith("--")]
        if niveaux and not niveaux[0].isdigit():
            raise ValueError(f"niveau illisible : {niveaux[0]!r} (un nombre de 0 à {migrations.DERNIERE})")
        cible = int(niveaux[0]) if niveaux else None
        n = migrations.migrer(ouvrir(a[1]), cible, confirmer_destruction="--confirmer-destruction" in a)
        print(f"schéma au niveau {n} (dernier : {migrations.DERNIERE})")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (sauvegarde.SauvegardeInvalide, migrations.Destructeur, ValueError) as err:
        print(f"REFUSÉ : {err}")
        sys.exit(1)
