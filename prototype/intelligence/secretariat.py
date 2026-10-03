"""ANNÉE 1 · LOT 4 — La console du secrétariat : ce que le lot ajoute à ce qui existait déjà (annonces sous chiffre,
escalade vers les piliers, tableau de bord, bilan, « Le Club cherche ») :

- MÉTIERS À CONFIRMER : les libellés de la colonne « métier » de la liste d'entreprises que le Club ne sait pas
  rattacher ; le secrétariat les rattache à un métier (fait METIER_CONFIRME). Jamais un nom d'entreprise lu ni montré ;
  le nombre de lignes d'un libellé s'affiche « < k » sous le seuil.
- CRITÈRES DU PILOTE FIXÉS D'AVANCE : un fichier de critères (seuils) GELÉ par son empreinte (fait CRITERES_GELES) ;
  le tableau du pilote compare chaque mesure à son seuil et dit en clair si le fichier a été retouché après le gel.
- BILAN TRIMESTRIEL exportable : Markdown, CSV, HTML imprimable (le PDF en est l'impression, côté serveur).
- CAMPAGNE D'INVITATION : « Le Club cherche » → N passes découverte liés aux plus anciennes demandes d'un métier, avec
  leur suivi agrégé (émis, activés, ont contribué, intentions d'adhésion — « < k » sous le seuil)."""
from __future__ import annotations

import hashlib
import html
import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from plateforme.affirmations import Statut

from . import bilan, club_cherche, metiers, suivi
from .erreurs import Invalide

if TYPE_CHECKING:
    from .club_pulse import ClubPulse

CRITERES_DEFAUT = Path(__file__).resolve().parents[2] / "docs" / "annee-1" / "pilote" / "criteres.json"
Nombre = Union[int, str, None]


def _k(c: "ClubPulse", n: int) -> Nombre:
    k = c.reglages.k_anonymat
    return f"< {k}" if 0 < n < k else n


# ------------------------------------------------------------------ métiers à confirmer
def confirmations(c: "ClubPulse") -> dict[str, str]:
    return {e.donnees["valeur"]: e.donnees["metier"] for e in c.journal.evenements("METIER_CONFIRME")}


def metiers_a_verifier(c: "ClubPulse") -> dict:
    libelles = club_cherche.libelles_metier()
    if libelles is None:
        return {"source": "absente", "a_verifier": [], "note": "liste d'entreprises non fournie"}
    conf = confirmations(c)
    compte: dict[str, int] = {}
    for v in libelles:
        if v and v not in conf and club_cherche._metier_csv(v) is None:
            compte[v] = compte.get(v, 0) + 1
    return {"source": "liste d'entreprises (colonne métier seulement)", "lignes": len(libelles),
            "a_verifier": [{"valeur": v, "lignes": _k(c, n)} for v, n in sorted(compte.items())],
            "metiers": [{"id": m["id"], "fr": metiers.libelle(m["id"]), "de": metiers.libelle(m["id"], "de")}
                        for m in metiers.metiers()]}


def confirmer_metier(c: "ClubPulse", valeur: str, metier: str, par: str = "") -> dict:
    v = club_cherche.normaliser(valeur)
    if not v or len(v) > 80:
        raise Invalide("libellé vide ou trop long")
    if metier not in metiers.ids():
        raise Invalide("métier inconnu")
    c.banc._ecrire("METIER_CONFIRME", [], Statut.DECLARE, valeur=v, metier=metier, par=par[:60])
    return {"valeur": v, "metier": metier}


# ------------------------------------------------------------------ critères du pilote
def criteres_par_defaut() -> list[dict]:
    """PROPOSITION de critères (à fixer par le comité AVANT le pilote, puis geler). `mesure` : chemin dans Suivi."""
    return [
        {"id": "taux_oui", "libelle": "Part des demandes qui reçoivent un oui (%)", "mesure": "reponses.pourcentages.oui",
         "sens": ">=", "seuil": 30},
        {"id": "sans_reponse", "libelle": "Part des demandes restées sans réponse (%)",
         "mesure": "reponses.pourcentages.sans_reponse", "sens": "<=", "seuil": 40},
        {"id": "delai_oui", "libelle": "Délai médian avant le premier oui (jours)", "mesure": "delai_premier_oui_jours",
         "sens": "<=", "seuil": 7},
        {"id": "membres_actifs", "libelle": "Membres actifs sur le trimestre", "mesure": "membres_actifs", "sens": ">=",
         "seuil": 20},
        {"id": "intentions", "libelle": "Invités qui souhaitent adhérer", "mesure": "invites.intentions_adhesion",
         "sens": ">=", "seuil": 3},
    ]


def _empreinte(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def _lire_criteres(f: Path) -> list[dict]:
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Invalide(f"critères illisibles : {e}") from None
    if not isinstance(d, list) or not all(isinstance(x, dict) and {"id", "libelle", "mesure", "sens", "seuil"} <= set(x)
                                          and x["sens"] in (">=", "<=") for x in d):
        raise Invalide("critères mal formés : une liste de {id, libelle, mesure, sens (>= ou <=), seuil}")
    return d


def geler_criteres(c: "ClubPulse", f: Path = CRITERES_DEFAUT, par: str = "") -> dict:
    _lire_criteres(f)
    if c.journal.evenements("CRITERES_GELES"):
        raise Invalide("les critères sont déjà gelés : le premier gel fait foi (un changement se décide en comité, et se "
                       "dit dans le bilan)")
    e = _empreinte(f)
    c.banc._ecrire("CRITERES_GELES", [], Statut.DECLARE, empreinte=e, par=par[:60])
    return {"empreinte": e, "le": c.jour.isoformat()}


def _valeur(s: dict, chemin: str) -> Any:
    x: Any = s
    for morceau in chemin.split("."):
        x = x.get(morceau) if isinstance(x, dict) else None
    return x


def tableau_pilote(c: "ClubPulse", f: Path = CRITERES_DEFAUT, periode: str = "trimestre") -> dict:
    criteres = _lire_criteres(f)
    gel = c.journal.evenements("CRITERES_GELES")
    s = suivi.calculer(c, periode)
    lignes = []
    for x in criteres:
        v = _valeur(s, x["mesure"])
        mesurable = isinstance(v, (int, float)) and not isinstance(v, bool)
        atteint = None if not mesurable else (v >= x["seuil"] if x["sens"] == ">=" else v <= x["seuil"])
        lignes.append({"id": x["id"], "libelle": x["libelle"], "sens": x["sens"], "seuil": x["seuil"], "valeur": v,
                       "atteint": atteint})
    if not gel:
        alerte = "critères PAS ENCORE gelés : tant qu'ils ne le sont pas, ils peuvent être ajustés aux résultats"
    elif gel[0].donnees["empreinte"] != _empreinte(f):
        alerte = f"critères modifiés après le gel du {gel[0].le.isoformat()} : les seuils affichés ne sont plus ceux fixés d'avance"
    else:
        alerte = ""
    return {"periode": s["periode_libelle"], "du": s["du"], "au": s["au"], "monde": s["monde"], "fictif": True,
            "gel": {"le": gel[0].le.isoformat(), "empreinte": gel[0].donnees["empreinte"][:16]} if gel else None,
            "alerte": alerte, "criteres": lignes,
            "regle": "Atteint : oui / non ; vide : non mesurable (moins de k entreprises, ou pas de donnée)."}


# ------------------------------------------------------------------ bilan trimestriel
def _html(md: str) -> str:
    """Le Markdown du bilan (titres, citation, tableau, listes, paragraphes) en HTML imprimable, tout échappé."""
    def inl(t: str) -> str:
        t = html.escape(t)
        while t.count("**") >= 2:
            t = t.replace("**", "<b>", 1).replace("**", "</b>", 1)
        return t
    out, table = [], False
    for ligne in md.split("\n"):
        if ligne.startswith("|"):
            cellules = [x.strip() for x in ligne.strip("|").split("|")]
            if set("".join(cellules)) <= {"-", ":"}:
                continue
            if not table:
                out.append("<table>")
                table = True
            out.append("<tr>" + "".join(f"<td>{inl(x)}</td>" for x in cellules) + "</tr>")
            continue
        if table:
            out.append("</table>")
            table = False
        if ligne.startswith("## "):
            out.append(f"<h2>{inl(ligne[3:])}</h2>")
        elif ligne.startswith("# "):
            out.append(f"<h1>{inl(ligne[2:])}</h1>")
        elif ligne.startswith("> "):
            out.append(f"<blockquote>{inl(ligne[2:])}</blockquote>")
        elif ligne.startswith("- "):
            out.append(f"<p class=\"li\">• {inl(ligne[2:])}</p>")
        elif ligne.strip():
            out.append(f"<p>{inl(ligne)}</p>")
    if table:
        out.append("</table>")
    style = ("body{font:12pt/1.45 system-ui,sans-serif;margin:24mm;color:#111}h1{font-size:20pt}h2{font-size:14pt;"
             "margin-top:18pt}table{border-collapse:collapse}td{border:1px solid #bbb;padding:4px 8px}"
             "blockquote{border-left:3px solid #999;margin:0;padding-left:10px;color:#444}.li{margin:2px 0}")
    return ("<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><title>Bilan trimestriel</title>"
            f"<style>{style}</style></head><body>" + "\n".join(out) + "</body></html>")


def bilan_trimestriel(c: "ClubPulse", fmt: str) -> str:
    if fmt == "md":
        return bilan.rediger(c, "trimestre", origine="console du secrétariat")
    if fmt == "csv":
        return bilan.csv_texte(c, "trimestre")
    if fmt == "html":
        return _html(bilan.rediger(c, "trimestre", origine="console du secrétariat"))
    raise Invalide("format : md, csv ou html (le PDF est l'impression du HTML)")


# ------------------------------------------------------------------ campagne d'invitation
def lancer_campagne(c: "ClubPulse", metier: str, nombre: int, base: str) -> dict:
    if not 1 <= nombre <= 50:
        raise Invalide("de 1 à 50 invitations par campagne")
    groupe = next((g for g in club_cherche.calculer(c)["metiers"] if g["metier"] == metier), None)
    if groupe is None:
        raise Invalide("aucune demande sans réponse pour ce métier")
    demandes = sorted(groupe["demandes"], key=lambda d: -d["age_jours"])
    cid = "camp-" + secrets.token_hex(4)
    invitations = []
    for i in range(nombre):
        d = demandes[i % len(demandes)]
        p = c.decouverte.emettre("demande", d["id"])
        url = base.rstrip("/") + p["chemin"]
        invitations.append({"jeton": p["jeton"], "nonce": p["nonce"], "url": url, "jusqu_au": p["jusqu_au"],
                            "texte": club_cherche.invitation(d["piece"], metier, url, p["jours"])})
    c.banc._ecrire("CAMPAGNE", [], Statut.DECLARE, id=cid, metier=metier, passes=[x["nonce"] for x in invitations])
    return {"id": cid, "metier": metier, "libelle": metiers.libelle(metier), "invitations": invitations}


def campagnes(c: "ClubPulse") -> list[dict]:
    passes = c.decouverte.passes()
    k = c.reglages.k_anonymat
    res = []
    for e in c.journal.evenements("CAMPAGNE"):
        ps = [passes[n] for n in e.donnees["passes"] if n in passes]

        def kk(groupe: list[dict]) -> Nombre:
            ent = {(p["declaration"] or {}).get("cle_entreprise") or f"passe:{p['nonce']}" for p in groupe}
            return f"< {k}" if groupe and len(ent) < k else len(groupe)
        res.append({"id": e.donnees["id"], "le": e.le.isoformat(), "metier": e.donnees["metier"],
                    "libelle": metiers.libelle(e.donnees["metier"]), "emis": len(ps),
                    "actives": kk([p for p in ps if p["active_le"] is not None]),
                    "ont_contribue": kk([p for p in ps if any(r["aide"] for r in p["reponses"])]),
                    "intentions_adhesion": kk([p for p in ps if p["intention"]])})
    return res
