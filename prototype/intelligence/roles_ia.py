"""Les trois RÔLES du modèle dans le registre des capacités — derrière l'adaptateur (`Intelligence._executer`) :

    EXTRACT    texte d'un membre → attributs de SA pièce (une PROPOSITION : le membre confirme, le code valide)
    NORMALIZE  texte d'une offre → un concept du vocabulaire, avec l'extrait qui le montre
    NARRATE    faits numérotés d'une capacité → 1 à 4 phrases qui CITENT leurs faits

Le modèle ne décide jamais : il ne crée ni consentement ni identité, ne juge d'aucune validité, n'invente aucune
disponibilité, ne dit pas qu'une personne accepte, ne produit aucun résultat, ne contourne aucune règle, ne voit aucune
identité réelle (`Intelligence.proteger`), ne note personne. Chaque sortie est revalidée ici ; rejetée → UN nouvel
essai → la forme déterministe (FALLBACK_FORM : formulaire vide, règles simples ou gabarit des faits), toujours dite."""
from __future__ import annotations

import json
import re
from typing import Optional

from app.parser_llm import _json_de
from app.taxonomy import Taxonomie, norm

from .ia import Intelligence, Rejet, Reponse

NOMBRE = re.compile(r"\d+")
ETATS = ("il manque une pièce", "toutes les pièces existent", "consentements en cours", "le Club peut le faire",
         "un consentement ne vaut plus", "la fenêtre est passée", "état incertain")


def _objet(brut: str, cles: set[str]) -> dict:
    v = json.loads(_json_de(brut))
    if not isinstance(v, dict):
        raise Rejet("la sortie n'est pas un objet JSON")
    if set(v) - cles:
        raise Rejet("champs non demandés")      # ni consentement, ni statut, ni identité
    return v


class RolesIA:
    def __init__(self, ia: Intelligence, tax: Taxonomie):
        self.ia, self.tax = ia, tax

    # ------------------------------------------------------------------ EXTRACT
    def extraire(self, texte: str, minimums: dict[str, int]) -> Reponse:
        protege = self.ia.proteger(texte)
        nombres = set(NOMBRE.findall(protege))

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            v = _objet(brut, {"attributs", "incertitudes"})
            att = v.get("attributs") or {}
            if not isinstance(att, dict) or set(att) - set(minimums):
                raise Rejet("attribut non demandé")
            for x in att.values():
                if not isinstance(x, int) or isinstance(x, bool) or not 0 <= x <= 1000:
                    raise Rejet("valeur hors bornes")
                if str(x) not in nombres:
                    raise Rejet("valeur absente du texte du membre (inventée)")
            inc = v.get("incertitudes") or []
            if not isinstance(inc, list) or len(inc) > 3 or any(not isinstance(i, str) or len(i) > 120 for i in inc):
                raise Rejet("incertitudes mal formées")
            return {"attributs": att, "incertitudes": inc}, {"nombres_du_texte": sorted(nombres)}
        schema = {"type": "object", "additionalProperties": False, "required": ["attributs"],
                  "properties": {"attributs": {"type": "object", "properties": {k: {"type": "integer"} for k in minimums},
                                               "additionalProperties": False},
                                 "incertitudes": {"type": "array", "items": {"type": "string"}, "maxItems": 3}}}
        message = json.dumps({"texte": texte, "attributs_attendus": minimums}, ensure_ascii=False)
        return self.ia._executer("extraire_piece", "extraire_piece", message, schema, valide,
                                 lambda: {"attributs": {}, "incertitudes": []}, rejouable=True)   # le formulaire, vide

    # ------------------------------------------------------------------ NORMALIZE
    def normaliser(self, texte: str) -> Reponse:
        protege = norm(self.ia.proteger(texte))

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            v = _objet(brut, {"concept", "extrait"})
            c, x = v.get("concept"), v.get("extrait")
            if c is None:
                return {"concept": None, "extrait": None}, None
            if c not in self.tax.concepts:
                raise Rejet("concept hors vocabulaire")
            if not isinstance(x, str) or len(x.strip()) < 3 or norm(x) not in protege:
                raise Rejet("extrait absent du texte du membre")
            return {"concept": c, "extrait": x.strip()}, None

        def regles() -> dict:
            trouves = sorted(self.tax.concepts_dans(protege))
            return {"concept": trouves[0] if len(trouves) == 1 else None, "extrait": None}
        vocabulaire = {cid: self.tax.libelle(cid) for cid in sorted(self.tax.concepts)}
        schema = {"type": "object", "additionalProperties": False, "required": ["concept", "extrait"],
                  "properties": {"concept": {"type": ["string", "null"], "enum": [*vocabulaire, None]},
                                 "extrait": {"type": ["string", "null"]}}}
        message = json.dumps({"texte": texte, "vocabulaire": vocabulaire}, ensure_ascii=False)
        return self.ia._executer("normaliser_offre", "normaliser_offre", message, schema, valide, regles, rejouable=True)

    # ------------------------------------------------------------------ NARRATE
    @staticmethod
    def faits(carte: dict) -> list[dict]:
        """Les faits d'une carte de l'Établi (vue en RÔLES, sans nom), numérotés : ce que le récit peut citer."""
        f = [f"état : {carte['statut_libelle']}", f"fenêtre : {carte['fenetre']}"]
        for p in carte["pieces"]:
            f.append(f"{p['role']} : " + (f"présente, consentement {p['consentement']}" if p["presente"] else "manquante"))
        f += [f"pièce critique : {r}" for r in carte["critiques"]] + list(carte["perdus"])
        return [{"id": f"F{i}", "texte": t} for i, t in enumerate(f, 1)]

    def raconter(self, faits: list[dict]) -> Reponse:
        par_id = {x["id"]: x["texte"] for x in faits}

        def valide(brut: str) -> tuple[dict, Optional[dict]]:
            v = _objet(brut, {"phrases"})
            ph = v.get("phrases")
            if not isinstance(ph, list) or not 1 <= len(ph) <= 4:
                raise Rejet("1 à 4 phrases attendues")
            propres = []
            for p in ph:
                if not isinstance(p, dict) or set(p) - {"texte", "faits"}:
                    raise Rejet("phrase mal formée")
                t, cites = p.get("texte"), p.get("faits")
                if not isinstance(t, str) or not 3 <= len(t) <= 240:
                    raise Rejet("phrase vide ou trop longue")
                if not isinstance(cites, list) or not cites or any(c not in par_id for c in cites):
                    raise Rejet("phrase sans citation, ou citation d'un fait inexistant")
                source = " ".join(par_id[c] for c in cites)
                if set(NOMBRE.findall(t)) - set(NOMBRE.findall(source)):
                    raise Rejet("nombre absent des faits cités")
                if any(e in norm(t) and e not in norm(source) for e in map(norm, ETATS)):
                    raise Rejet("état affirmé sans fait cité qui le porte")
                if "MEMBRE-" in t or self.ia.proteger(t) != t:
                    raise Rejet("la phrase désigne une personne")
                propres.append({"texte": t.strip(), "faits": list(dict.fromkeys(cites))})
            return {"phrases": propres}, None

        def gabarit() -> dict:
            return {"phrases": [{"texte": x["texte"][0].upper() + x["texte"][1:] + ".", "faits": [x["id"]]} for x in faits[:4]]}
        schema = {"type": "object", "additionalProperties": False, "required": ["phrases"],
                  "properties": {"phrases": {"type": "array", "minItems": 1, "maxItems": 4, "items": {
                      "type": "object", "additionalProperties": False, "required": ["texte", "faits"],
                      "properties": {"texte": {"type": "string"}, "faits": {"type": "array", "items": {"type": "string"}}}}}}}
        return self.ia._executer("raconter_capacite", "raconter_capacite", json.dumps({"faits": faits}, ensure_ascii=False),
                                 schema, valide, gabarit, rejouable=True)
