"""Génère un Club SYNTHÉTIQUE de N membres (défaut 150), déterministe (graine fixe).

But : tester le passage à l'échelle (planificateur, recherche, Bourse) sur une taille réaliste. Les noms sont
volontairement non réalistes (« Nadia R. », « Menuiserie · synthétique n°042 ») pour ne ressembler à aucune
personne ni entreprise réelle. Aucune donnée collectée.

Usage : python scripts/generer_club.py [--n 150] → data/profils_synthetiques.json
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

OFFRES = {
    "transport_frigorifique": ["Transport frigorifique de produits frais", "Livraisons réfrigérées régulières", "Transport sous température dirigée"],
    "logistique": ["Entreposage et préparation de commandes", "Distribution de marchandises en Suisse romande"],
    "installation_froid": ["Installation et dépannage de chambres froides", "Climatisation de locaux professionnels"],
    "fiduciaire": ["Comptabilité et bouclements pour PME", "Fiscalité et TVA des indépendants", "Gestion des salaires et fiduciaire"],
    "droit_affaires": ["Conseil juridique en droit des sociétés", "Rédaction et relecture de contrats commerciaux"],
    "droit_travail": ["Droit du travail pour employeurs"],
    "recrutement": ["Placement de personnel temporaire", "Recrutement de saisonniers"],
    "cybersecurite": ["Tests d'intrusion et sécurité informatique", "Sensibilisation au phishing pour PME"],
    "securite_evenement": ["Agents de sécurité pour événements", "Contrôle d'accès et gardiennage"],
    "sante_securite_travail": ["Concepts MSST et prévention des accidents"],
    "informatique": ["Infogérance et support informatique", "Réseau informatique et sauvegardes"],
    "developpement_web": ["Création de sites web et boutiques en ligne", "Développement d'applications web"],
    "marketing": ["Communication et réseaux sociaux", "Image de marque et campagnes publicitaires"],
    "photo_video": ["Photographie de produits", "Film d'entreprise et vidéo"],
    "traduction": ["Traduction français–allemand", "Traduction et relecture de documents"],
    "menuiserie": ["Menuiserie et agencement sur mesure", "Charpente bois"],
    "construction_metallique": ["Construction métallique et serrurerie"],
    "energie_solaire": ["Installations photovoltaïques", "Panneaux solaires pour entreprises"],
    "efficacite_energetique": ["Audit énergétique et CECB", "Rénovation énergétique de bâtiments"],
    "financement": ["Financement et crédit pour PME", "Leasing d'équipements"],
    "assurance": ["Courtage en assurances entreprises", "Assurance responsabilité civile"],
    "location_machines": ["Location de nacelles et de machines", "Location de chariots élévateurs"],
    "emballage": ["Emballages et étiquettes alimentaires", "Conditionnement et packaging"],
    "vins": ["Vins du Valais et encavage", "Domaine viticole"],
    "boissons": ["Jus de fruits artisanaux", "Cidre et boissons régionales"],
    "mentorat": ["Mentorat de jeunes dirigeants"],
    "transmission_entreprise": ["Accompagnement à la transmission d'entreprise"],
    "ia_donnees": ["Analyse de données et tableaux de bord", "Automatisation et intelligence artificielle pour PME"],
    "tourisme": ["Hôtellerie et hébergement de groupes"],
    "evenementiel": ["Organisation d'événements d'entreprise"],
    "traiteur": ["Service traiteur pour entreprises"],
}
# Ce que chaque secteur cherche typiquement (complémentarités plausibles, hypothèses de génération)
BESOINS_TYPE = {
    "vins": ["transport_frigorifique", "marketing", "emballage", "developpement_web", "export_suisse_alemanique"],
    "boissons": ["transport_frigorifique", "emballage", "marketing", "export_suisse_alemanique"],
    "tourisme": ["marketing", "developpement_web", "recrutement", "traiteur", "photo_video"],
    "menuiserie": ["energie_solaire", "recrutement", "fiduciaire", "location_machines"],
    "construction_metallique": ["location_machines", "sante_securite_travail", "recrutement"],
    "transport_frigorifique": ["recrutement", "ia_donnees", "assurance", "installation_froid"],
    "logistique": ["recrutement", "ia_donnees", "assurance"],
    "informatique": ["recrutement", "marketing", "cybersecurite"],
    "developpement_web": ["marketing", "traduction", "photo_video"],
    "evenementiel": ["securite_evenement", "traiteur", "photo_video"],
}
COMMUNES = [("Martigny", "bas"), ("Sion", "centre"), ("Sierre", "centre"), ("Monthey", "bas"), ("Fully", "bas"), ("Saxon", "bas"),
            ("Conthey", "centre"), ("Nendaz", "centre"), ("Brigue", "haut"), ("Viège", "haut"), ("Naters", "haut"), ("Orsières", "bas"),
            ("Chamoson", "centre"), ("Riddes", "bas"), ("Bagnes", "bas"), ("Vex", "centre")]
PRENOMS = ["Nadia", "Luc", "Sarah", "Marc", "Julie", "Thomas", "Laura", "David", "Emma", "Nicolas", "Léa", "Pierre", "Anna", "Yves",
           "Chloé", "Simon", "Eva", "Hugo", "Inès", "Paul", "Mia", "Loïc", "Zoé", "Jan", "Nina", "Reto", "Sonja", "Urs"]
LIBELLES = {k: k.replace("_", " ").capitalize() for k in OFFRES}


def generer(n: int, graine: int = 2026) -> dict:
    rng = random.Random(graine)
    secteurs = list(OFFRES)
    poids = [3 if s in ("vins", "fiduciaire", "tourisme", "menuiserie", "informatique", "marketing") else 1 for s in secteurs]
    profils = []
    for k in range(1, n + 1):
        s = rng.choices(secteurs, poids)[0]
        commune, region = rng.choice(COMMUNES)
        offres = [{"concept": s, "texte": rng.choice(OFFRES[s])}]
        if rng.random() < 0.3:
            s2 = rng.choice(secteurs)
            if s2 != s:
                offres.append({"concept": s2, "texte": rng.choice(OFFRES[s2])})
        besoins = BESOINS_TYPE.get(s, [])
        tires = rng.sample(besoins, k=min(len(besoins), rng.choice([0, 1, 1, 2])))
        recherche = [{"concept": c, "texte": f"Nous cherchons : {LIBELLES.get(c, c).lower()}"} for c in tires]
        langues = ["de"] + (["fr"] if rng.random() < 0.5 else []) if region == "haut" else ["fr"] + (["de"] if rng.random() < 0.4 else [])
        if rng.random() < 0.2:
            langues.append("en")
        zones = (["Valais"] + (["Suisse romande"] if rng.random() < 0.5 else [])
                 + (["Suisse alémanique"] if rng.random() < (0.7 if region == "haut" else 0.3) else []))
        profils.append({
            "id": f"s{k:03d}", "nom": f"{rng.choice(PRENOMS)} {chr(65 + rng.randrange(26))}.", "fonction": "Dirigeant·e",
            "entreprise": f"{LIBELLES[s]} · synthétique n°{k:03d}", "commune": commune, "type": "membre_club",
            "secteurs": [s], "offre": offres, "recherche": recherche, "langues": langues, "zones_service": zones,
            "accepte_introductions": rng.random() < 0.9, "disponible": rng.random() < 0.95,
            "presentation": "", "maj": "2026-09",
        })
    return {"_avertissement": f"CLUB SYNTHÉTIQUE de {n} membres généré par scripts/generer_club.py (graine {graine}). "
                              "Noms volontairement non réalistes ; aucune personne ni entreprise réelle.",
            "utilisateur_demo": "s001", "profils": profils}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    a = ap.parse_args()
    d = generer(a.n)
    (DATA / "profils_synthetiques.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(d['profils'])} profils synthétiques → data/profils_synthetiques.json")
