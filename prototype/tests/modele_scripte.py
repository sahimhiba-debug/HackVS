"""Un MODÈLE SCRIPTÉ pour les tests (jamais utilisé par l'application) : il répond, par rôle, ce qu'on lui a dit de
répondre — y compris des sorties fausses ou hostiles — et ENREGISTRE chaque prompt reçu (le corpus des canaris)."""
from __future__ import annotations

import json
from typing import Callable, Union

from intelligence.ia import ErreurFournisseur

Reponse = Union[str, dict, Exception, Callable[[str], Union[str, dict]]]


class ModeleScripte:
    nom, modele = "maquette", "modele-scripte-1"

    def __init__(self, **par_role: Union[Reponse, list[Reponse]]):
        self.par_role = {k: list(v) if isinstance(v, list) else [v] for k, v in par_role.items()}
        self.recus: list[tuple[str, str, str]] = []          # (rôle, prompt système, message)

    @staticmethod
    def role(systeme: str) -> str:
        return systeme.split("\n", 1)[0].removeprefix("# ").split(" ")[0]

    def completer(self, systeme_txt: str, message: str, schema) -> str:
        r = self.role(systeme_txt)
        self.recus.append((r, systeme_txt, message))
        file = self.par_role.get(r)
        if not file:
            raise ErreurFournisseur(f"aucune réponse scriptée pour {r}")
        x = file.pop(0) if len(file) > 1 else file[0]
        if callable(x):
            x = x(message)
        if isinstance(x, Exception):
            raise x
        return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)

    def appels(self, role: str) -> int:
        return sum(1 for r, *_ in self.recus if r == role)
