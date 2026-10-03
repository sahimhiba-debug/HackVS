"""COACH « SMART » d'une demande (P3 n°3) — ce qui manque pour qu'on puisse dire oui : quand ? combien ? où ?

Une demande précise reçoit plus de oui (Reciprocity Ring : des demandes SMART ; PREUVES, « Contexte »). Ces questions
viennent de RÈGLES sur les mots du membre (français, allemand), jamais d'un modèle : IA allumée ou éteinte, les mêmes
questions (parité par construction). Rien n'est écrit ; le membre précise ou non."""
from __future__ import annotations

import re

JOURS = r"lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag"
MOIS = (r"janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre"
        r"|januar|februar|märz|april|juni|juli|august|oktober|dezember")
QUAND = re.compile(rf"\b({JOURS}|{MOIS}|demain|aujourd'hui|ce soir|cette semaine|semaine prochaine|morgen|heute|nächste woche"
                   r"|matin|après-midi|apres-midi|soir|vormittag|nachmittag|abend)\b|\b\d{1,2}\s?(h|uhr)\b|\b\d{1,2}[./]\d{1,2}\b",
                   re.IGNORECASE)
NOMBRES = r"un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|douze|vingt|ein|eine|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|zwölf|zwanzig"
COMBIEN = re.compile(rf"\b\d+\b|\b({NOMBRES})\s+\w*(personnes?|places?|acheteurs?|heures?|jours?|invités?|personen|plätze|einkäufer|stunden|gäste)\b",
                     re.IGNORECASE)
# un lieu nommé : préposition + nom propre (sensible à la casse : « à Martigny », pas « à 14h ») ; ou un mot de lieu
OU = re.compile(r"\b(à|au|aux|chez|en|in|im|bei|nach)\s+(la\s+|le\s+|l')?[A-ZÉÈÂ][\w\-']+")
OU_MOTS = re.compile(r"\b(salle|stand|bureau|local|atelier|foire|saal|büro|messe)\b", re.IGNORECASE)

QUESTIONS = [
    ("quand", QUAND, "Quand ?", "un jour et une heure : « jeudi 8 octobre, 14 h – 16 h »"),
    ("combien", COMBIEN, "Combien ?", "de personnes, de places, d'heures : « 8 acheteurs, un minibus de 12 places »"),
    ("ou", None, "Où ?", "un lieu : « à Martigny », « au stand de la Foire »"),
]


def _ou(texte: str) -> bool:
    return bool(OU.search(texte) or OU_MOTS.search(texte))


def questions(texte: str) -> list[dict]:
    """Les questions SMART qui manquent, dans l'ordre quand / combien / où (vide : la demande est précise)."""
    res = []
    for qid, motif, question, exemple in QUESTIONS:
        present = _ou(texte) if motif is None else bool(motif.search(texte))
        if not present:
            res.append({"id": qid, "question": question, "exemple": exemple})
    return res
