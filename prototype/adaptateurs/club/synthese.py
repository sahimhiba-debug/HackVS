"""Synthèse du diagnostic pour un humain — et le CONTRÔLE qui rend une synthèse générative acceptable.

- `gabarit(d)` : texte produit par du code à partir du diagnostic structuré (fidèle par construction).
- `verifier(texte, d)` : contrôle déterministe d'un texte (généré ou non) : chaque nombre, date et identifiant de membre
  cité doit exister dans les faits fournis ; on mesure aussi la couverture des phénomènes détectés.
- `retenir(texte_ia, d)` : garde-fou produit : un texte généré n'est montré que s'il est 100 % fidèle ; sinon, le gabarit.
Le modèle génératif peut MIEUX DIRE ; il ne peut rien AJOUTER.
"""
from __future__ import annotations

import re

MOTS_PHENOMENES = {
    "ISOLEMENT": ("isol", "sans aucune relation", "sans relation"),
    "PASSAGE_UNIQUE": ("une seule personne", "un seul membre", "passage unique"),
    "PONT_FRAGILE": ("une seule relation", "pont", "fragile"),
    "FRAGMENTATION": ("groupes", "fragment", "séparés", "morcel"),
    "SUR_SOLLICITATION": ("sollicit",),
    "CONCENTRATION": ("concentr", "reposent sur", "repose sur"),
    "VIEILLISSEMENT": ("éteint", "s'éteign", "vieilli", "ne sont plus actuelles"),
    "ENTRE_SOI": ("secteur", "entre-soi"),
}
_NOMBRE = re.compile(r"(?<![\w.])(\d{4}-\d{2}-\d{2}|\d+(?:[.,]\d+)?)(?![\w])")
# Quantités écrites en lettres : invérifiables → refusées (le modèle doit écrire les nombres en chiffres).
_NOMBRES_EN_LETTRES = re.compile(r"\b(trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|"
                                 r"vingt|trente|quarante|cinquante|soixante|cent|cents|mille|dizaines?|centaines?)\b", re.I)
# Négation d'un phénomène DÉTECTÉ (contrôle de sens minimal ; ne voit pas toutes les contradictions — déclaré).
_NEGATIONS = {
    "ISOLEMENT": re.compile(r"(aucun|personne|nul)[^.]{0,40}isol|pas d[e'][^.]{0,20}isol|n'est isol|sans (aucun )?isol", re.I),
    "FRAGMENTATION": re.compile(r"(un seul|seul) groupe|(pas|aucun)[^.]{0,20}fragment|(tous|toutes)[^.]{0,30}reli[ée]s", re.I),
    "PONT_FRAGILE": re.compile(r"(aucun|pas de)[^.]{0,20}(pont|fragil)", re.I),
    "PASSAGE_UNIQUE": re.compile(r"(aucun|pas de)[^.]{0,30}(une seule personne|passage unique)", re.I),
}
_SAIN = re.compile(r"\b(parfaitement |tout à fait )?sain\b|tout va bien|aucun probl[èe]me", re.I)


def _valeurs(obj, nombres: set[str], chaines: set[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _valeurs(v, nombres, chaines)
    elif isinstance(obj, (list, tuple)):
        nombres.add(str(len(obj)))            # le NOMBRE d'éléments d'une liste est un fait vérifiable (faux positif corrigé)
        for v in obj:
            _valeurs(v, nombres, chaines)
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float)):
        nombres.add(_norm_nombre(str(obj)))
        if isinstance(obj, float):
            nombres.add(_norm_nombre(f"{obj:.0%}".rstrip("%")))   # 0.25 → « 25 »
    elif isinstance(obj, str):
        chaines.add(obj)
        for n in _NOMBRE.findall(obj):
            nombres.add(_norm_nombre(n))


def _norm_nombre(s: str) -> str:
    s = s.replace(",", ".")
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    return s


def faits_autorises(d: dict) -> tuple[set[str], set[str]]:
    nombres: set[str] = set()
    chaines: set[str] = set()
    _valeurs(d, nombres, chaines)
    return nombres, chaines


def verifier(texte: str, d: dict, identifiants: set[str]) -> dict:
    """`identifiants` : tous les identifiants de membres du Club (pour repérer ceux qui sont cités sans être dans les faits)."""
    nombres, chaines = faits_autorises(d)
    cites = [_norm_nombre(n) for n in _NOMBRE.findall(texte)]
    nombres_inventes = sorted({n for n in cites if n not in nombres})
    ids_faits = {x for x in identifiants if any(x == c or x in c for c in chaines)}
    ids_cites = {x for x in identifiants if re.search(rf"(?<!\w){re.escape(x)}(?!\w)", texte)}
    ids_inventes = sorted(ids_cites - ids_faits)
    presents = [p["phenomene"] for p in d.get("diagnostiquer", {}).get("phenomenes", [])]
    bas = texte.lower()
    couverts = [p for p in presents if any(m in bas for m in MOTS_PHENOMENES.get(p, ()))]
    en_lettres = sorted({m.group(0).lower() for m in _NOMBRES_EN_LETTRES.finditer(texte)})
    contradictions = [p for p in presents if p in _NEGATIONS and _NEGATIONS[p].search(texte)]
    if presents and _SAIN.search(texte):
        contradictions.append("RÉSEAU_DIT_SAIN")
    return {"fidele": not nombres_inventes and not ids_inventes and not en_lettres and not contradictions,
            "nombres_en_lettres": en_lettres, "contradictions": contradictions, "nombres_inventes": nombres_inventes,
            "identifiants_inventes": ids_inventes, "nombres_cites": len(cites),
            "couverture": f"{len(couverts)}/{len(presents)}", "non_couverts": [p for p in presents if p not in couverts]}


def gabarit(d: dict) -> str:
    e = d["comprendre"]["etat"]
    lignes = [f"Le réseau compte {e['membres']} membres ; {e['avec_relation_actuelle']} ont au moins une relation actuelle."]
    for p in d["diagnostiquer"].get("phenomenes", [])[:4]:
        lignes.append(f"- {p['observation']} : {p['interpretation']}. Action possible : {p['intervention_possible']}.")
    perte = d["voir_venir"]["INCLUSION"]["sans_action"]["premiere_perte"]
    if perte:
        lignes.append(f"Sans action, le réseau commence à perdre des membres le {perte}.")
    if d["agir"].get("plans_nommes"):
        lignes.append(f"{len(d['agir']['front'])} plans non dominés : aucun ne maximise tous les objectifs à la fois ; à vous de choisir.")
    else:
        lignes.append("Aucune action fondée sur une preuve n'est possible aujourd'hui : ne rien faire.")
    return "\n".join(lignes)


def retenir(texte_ia: str | None, d: dict, identifiants: set[str]) -> dict:
    """Garde-fou produit : texte généré montré seulement s'il est fidèle ; sinon le gabarit, et on dit pourquoi."""
    if texte_ia:
        v = verifier(texte_ia, d, identifiants)
        if v["fidele"]:
            return {"texte": texte_ia, "source": "IA (vérifiée : fidèle aux faits)", "controle": v}
        return {"texte": gabarit(d), "source": "gabarit (texte IA rejeté : infidèle)", "controle": v}
    return {"texte": gabarit(d), "source": "gabarit (aucun modèle configuré)", "controle": None}
