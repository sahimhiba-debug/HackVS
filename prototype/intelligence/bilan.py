"""BILAN DE PÉRIODE (Foire 2026 · G) — `make bilan` écrit `docs/bilans/bilan-<période>.md` depuis le journal.

Mêmes chiffres que l'écran Suivi (calculés par `suivi.calculer`, donc mêmes règles : agrégats, k = 3), plus les métiers
manquants et les nouveaux invités. Un paragraphe NARRATIF peut être demandé à Apertus (interrupteur `HACKVS_BILAN_IA=1`,
fournisseur configuré) : il ne reçoit que les agrégats, et le CODE le vérifie — tout nombre du récit absent des
statistiques calculées fait REJETER le récit (on garde alors le récit déterministe, et on le dit)."""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Optional

from . import suivi

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

NOMBRE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w])")
SYSTEME = ("Tu rédiges UN paragraphe de bilan (4 phrases au plus, en français) pour le comité d'un club d'entrepreneurs. "
           "Tu n'utilises QUE les nombres présents dans les statistiques fournies, écrits en chiffres, sans en calculer "
           "de nouveaux (ni total, ni pourcentage, ni différence). Aucun nom, aucune personne. Si une valeur vaut « < 3 », "
           "écris « moins de trois ».")


def _nombres(x: Any) -> set[str]:
    """Tous les nombres d'une structure de statistiques, normalisés (« 12 », « 12.5 », « 3 » de « < 3 »)."""
    if isinstance(x, dict):
        return set().union(*[_nombres(v) for v in x.values()]) if x else set()
    if isinstance(x, (list, tuple)):
        return set().union(*[_nombres(v) for v in x]) if x else set()
    if isinstance(x, bool) or x is None:
        return set()
    if isinstance(x, (int, float)):
        return {_norme(str(x))}
    return {_norme(m) for m in NOMBRE.findall(str(x))}


def _norme(n: str) -> str:
    n = n.replace(",", ".")
    return n[:-2] if n.endswith(".0") else n


HORS_CHIFFRES = ("du", "au", "regles", "periode", "periode_libelle", "delai_note", "monde")   # dates et textes : pas des chiffres


def verifier_recit(recit: str, stats: dict) -> list[str]:
    """Les nombres du récit ABSENTS des statistiques (vide : le récit est accepté). Les dates et les textes de règle ne
    comptent pas comme des chiffres permis : un « 10 » tiré du « 2026-10-06 » serait un chiffre inventé."""
    permis = _nombres({k: v for k, v in stats.items() if k not in HORS_CHIFFRES})
    return sorted({_norme(m) for m in NOMBRE.findall(recit)} - permis)


def recit_deterministe(s: dict) -> str:
    r = s["reponses"]
    phrases = [f"Sur la période ({s['periode_libelle']}), le Club a adressé {s['demandes']['adressees']} demande(s) ; "
               f"{s['demandes']['sans_reponse']} restent sans réponse.",
               f"Réponses oui : {r['oui']} ; non : {r['non']} ; pas cette fois : {r['pas_cette_fois']}."]
    if s["metiers_manquants"]:
        phrases.append("Métiers qui manquent : " + ", ".join(f"{m['metier']} ({m['demandes']})" for m in s["metiers_manquants"]) + ".")
    phrases.append(f"Invités ayant contribué : {s['invites']['ont_contribue']}.")
    return " ".join(phrases)


def recit_ia(c: "ClubPulse", s: dict) -> tuple[Optional[str], str]:
    """(récit accepté ou None, explication). N'appelle le modèle que si l'interrupteur et le fournisseur le permettent."""
    f = getattr(c.ia, "f", None)
    if f is None or not c.ia.actif:
        return None, "récit IA non demandé ou aucun modèle configuré : forme déterministe"
    try:
        brut = f.completer(SYSTEME, json.dumps(s, ensure_ascii=False), None).strip()
    except Exception as e:                                          # un fournisseur en panne ne bloque jamais le bilan
        return None, f"modèle indisponible ({type(e).__name__}) : forme déterministe"
    intrus = verifier_recit(brut, s)
    if intrus:
        return None, "récit du modèle REJETÉ par le code : nombres absents des statistiques " + ", ".join(intrus)
    return brut, f"récit proposé par le modèle « {getattr(f, 'modele', '?')} », vérifié par le code (chaque nombre est dans les statistiques)"


def _ligne(cle: str, v: Any) -> str:
    return f"| {cle} | {v} |"


def rediger(c: "ClubPulse", periode: str, ia: bool = False, origine: str = "") -> str:
    s = suivi.calculer(c, periode)
    r = s["reponses"]
    recit, note = recit_ia(c, s) if ia else (None, "forme déterministe (HACKVS_BILAN_IA non allumé)")
    hv = s["hors_valais"] if isinstance(s["hors_valais"], str) else s["hors_valais"]["membres"]
    L = [f"# Bilan — {s['periode_libelle']}", "",
         f"> **{s['monde']}** — chiffres d'un monde fictif, pas du Club réel. Période : du {s['du']} au {s['au']} "
         "(dates du monde, simulées en démonstration). Généré par `make bilan` depuis le journal" + (f" ({origine})" if origine else "")
         + f". Mêmes règles que l'écran Suivi : agrégats seulement, tout décompte de personnes sous {s['k']} s'affiche « < {s['k']} ».",
         "", "## Récit", "", recit or recit_deterministe(s), "", f"*{note}.*", "",
         "## Chiffres (identiques à Suivi)", "", "| Mesure | Valeur |", "|---|---|",
         _ligne("Demandes envoyées", s["demandes"]["adressees"]), _ligne("Demandes sans réponse", s["demandes"]["sans_reponse"]),
         _ligne("Réponses oui", r["oui"]), _ligne("Réponses non", r["non"]), _ligne("Réponses « pas cette fois »", r["pas_cette_fois"]),
         _ligne("Délai médian avant le premier oui (jours)", s["delai_premier_oui_jours"] if s["delai_premier_oui_jours"] is not None else s["delai_note"]),
         _ligne("Membres actifs", s["membres_actifs"]), _ligne("Membres hors Valais", hv),
         *[_ligne(f"Partenariats — {k}", v) for k, v in s["partenariats_par_etape"].items()],
         *[_ligne(f"Résultat déclaré — {k}", v) for k, v in s["resultats"].items()],
         "", "## Métiers manquants", "",
         *([f"- {m['metier']} : {m['demandes']} demande(s) sans réponse" for m in s["metiers_manquants"]] or ["- aucun"]),
         "", "## Nouveaux invités (passe découverte)", "",
         f"- passes émis dans la période : {s['invites'].get('emis', 0)}",
         f"- invités actifs : {s['invites']['actifs']}", f"- invités ayant contribué : {s['invites']['ont_contribue']}",
         f"- intentions d'adhésion : {s['invites']['intentions_adhesion']} (jamais appelées « conversions » ; la suite est simulée en démonstration)",
         "", "## Règles", "", s["regles"], ""]
    return "\n".join(L)
