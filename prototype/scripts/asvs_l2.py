"""ANNÉE 1 · LOT 6 — La checklist OWASP ASVS 4.0.3, niveau 2, avec le statut de CHAQUE exigence.

    python scripts/asvs_l2.py      # → docs/annee-1/conformite/ASVS_L2.md

Source : le fichier officiel de l'OWASP (docs/annee-1/conformite/asvs-4.0.3-en.csv, licence CC BY-SA 3.0, téléchargé
depuis github.com/OWASP/ASVS, étiquette v4.0.3). Le statut d'une exigence n'est JAMAIS « conforme » sans une preuve
(un test ou un fichier) ; sans examen, elle reste « non évaluée ». Périmètre : la branche annee-1, pas un audit externe."""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
CSV = RACINE / "docs" / "annee-1" / "conformite" / "asvs-4.0.3-en.csv"
SORTIE = RACINE / "docs" / "annee-1" / "conformite" / "ASVS_L2.md"
STATUTS = ("conforme", "partiel", "non conforme", "sans objet", "non évaluée")

SANS_MOT_DE_PASSE = ("sans objet", "aucun mot de passe : invitation à usage unique + second facteur TOTP (lot 2)")
# (statut, preuve) — preuve obligatoire pour conforme / partiel / non conforme / sans objet
EVAL: dict[str, tuple[str, str]] = {
    **{f"V2.1.{i}": SANS_MOT_DE_PASSE for i in range(1, 13)},
    **{f"V2.4.{i}": SANS_MOT_DE_PASSE for i in range(1, 6)},
    "V2.5.2": ("conforme", "aucune question secrète ni indice (comptes.py)"),
    "V2.5.3": SANS_MOT_DE_PASSE,
    "V2.5.4": ("conforme", "comptes nominatifs ; l'amorçage crée UN compte d'administration étiqueté (test_tout_survit_a_un_redemarrage)"),
    "V2.5.5": ("partiel", "remplacement du second facteur journalisé (ADMIN_ACTION « remplacer_totp ») ; pas encore d'avis envoyé au membre"),
    "V2.2.1": ("partiel", "limite d'écritures par session (test_limite_par_session) ; pas de blocage après des codes TOTP faux (AUDIT_LOT23 M2)"),
    "V2.3.1": ("conforme", "invitation : jeton aléatoire signé, usage unique, expiration (test_invitation_a_usage_unique_et_qui_expire)"),
    "V2.5.1": ("conforme", "le jeton d'invitation n'est jamais écrit dans le journal (test_aucun_secret_en_clair_dans_le_journal)"),
    "V2.7.1": ("conforme", "aucun SMS ni appel n'authentifie (les SMS du lot 5 sont des notifications)"),
    "V2.8.1": ("conforme", "TOTP RFC 6238, pas de 30 s, ±1 pas toléré (test_le_code_totp_tolere_un_pas_de_decalage_pas_plus)"),
    "V2.8.3": ("conforme", "HMAC-SHA1 RFC 6238, vecteur de la RFC vérifié (test_le_vecteur_de_la_rfc_6238_est_respecte)"),
    "V2.8.4": ("conforme", "un code ne sert qu'une fois (test_la_console_exige_un_compte_nominatif_et_le_code_totp)"),
    "V2.8.5": ("partiel", "rejeu refusé ; pas encore consigné comme événement de sécurité"),
    "V2.8.2": ("partiel", "secret TOTP dérivé du secret du serveur + nonce journalisé, jamais stocké en clair ; pas de module matériel"),
    "V2.10.4": ("conforme", "secrets par l'environnement seulement (CONFIGURATION.md, verifier_secrets, test_le_depot_est_propre)"),
    "V3.1.1": ("conforme", "session en en-tête (X-Pulse-Compte / X-Pulse-Session), jamais dans l'adresse ; /espace la retire (AUDIT_LOT23 M5)"),
    "V3.2.1": ("conforme", "nouvelle session à chaque acceptation (comptes.accepter)"),
    "V3.2.2": ("conforme", "identifiant de session secrets.token_urlsafe(12) = 96 bits, signé HMAC-SHA256"),
    "V3.2.3": ("partiel", "sessionStorage (onglet seulement), pas de cookie ; un script injecté pourrait la lire (pas de cookie HttpOnly)"),
    "V3.2.4": ("conforme", "HMAC-SHA256 (comptes._mac)"),
    "V3.3.1": ("conforme", "déconnexion et expiration invalident la session (test_sessions_appareils_et_deconnexion)"),
    "V3.3.2": ("conforme", "session de 30 jours ; la console exige une élévation par code valable 12 h"),
    "V3.3.4": ("conforme", "liste des appareils et déconnexion de chacun (test_sessions_appareils_et_deconnexion)"),
    **{f"V3.4.{i}": ("sans objet", "aucun cookie de session (en-tête)") for i in range(1, 6)},
    "V3.5.2": ("conforme", "sessions par personne ; le jeton « console » de la DÉMO reste un secret partagé (hors lots année 1)"),
    "V3.5.3": ("conforme", "jeton de session signé HMAC, expiration couverte par la signature"),
    "V3.7.1": ("conforme", "actions d'administration : session élevée par un code exigée (AUDIT_LOT23 I1)"),
    "V4.1.1": ("conforme", "contrôles côté serveur ; balayage automatique de chaque route (test_autorisation_balayage.py)"),
    "V4.1.3": ("conforme", "rôles membre / invité / secrétariat / administration ; le secrétariat ne voit que membres et invités"),
    "V4.1.5": ("conforme", "toute erreur métier → 401/403/404/409 ; balayage : aucune route ne s'ouvre sur une session fausse"),
    "V4.2.1": ("conforme", "« moi » = la session, jamais un identifiant passé par le client (test_on_ne_deconnecte_pas_l_appareil_d_un_autre)"),
    "V4.2.2": ("conforme", "session en en-tête personnalisé + refus des Origin étrangères (test_une_origine_etrangere_est_refusee)"),
    "V4.3.1": ("conforme", "console du secrétariat : compte nominatif + TOTP + élévation (test_seul_un_compte_nominatif_eleve_ouvre_la_console)"),
    "V4.3.2": ("conforme", "aucune liste de répertoire (FastAPI, fichiers statiques nommés)"),
    "V8.1.1": ("conforme", "Cache-Control: no-store sur /api/pulse/ (protections.py)"),
    "V8.2.1": ("conforme", "Cache-Control: no-store sur les données personnelles et les pages des lots"),
    "V8.2.2": ("partiel", "seule la session est en sessionStorage ; aucune donnée personnelle stockée côté navigateur"),
    "V8.3.1": ("conforme", "données sensibles en corps ou en-tête ; invitation et désinscription dans le fragment (#), jamais envoyé au serveur"),
    "V8.3.2": ("conforme", "export et suppression définitive (lot 3, test_annee1_espace_membre*.py, test_annee1_audit_lot23.py)"),
    "V8.3.3": ("partiel", "politique de confidentialité FR/DE rédigée — à valider par un juriste (conformite/)"),
    "V8.3.4": ("partiel", "registre des traitements (conformite/REGISTRE_TRAITEMENTS.md) — à valider par un juriste"),
    "V8.3.5": ("conforme", "journal des accès à la console, sans les données (test_chaque_consultation_de_la_console_est_journalisee)"),
    "V8.3.8": ("non conforme", "durées de conservation proposées dans le registre, pas encore appliquées automatiquement"),
    "V14.2.5": ("non conforme", "pas encore de SBOM (constraints.txt donne les versions exactes, ce n'est pas une SBOM)"),
    "V14.3.2": ("conforme", "aucun mode debug ; erreurs 500 sans détail (observabilite, gestionnaire 500)"),
    "V14.3.3": ("partiel", "pas de version de l'application dans les en-têtes ; l'en-tête server d'uvicorn n'est pas retiré"),
    "V14.4.1": ("partiel", "Content-Type toujours posé ; les réponses JSON disent « application/json » sans charset explicite (vérifié)"),
    "V14.4.3": ("conforme", "CSP stricte par empreintes de scripts sur chaque page (protections.py, test de la CSP)"),
    "V14.4.4": ("conforme", "X-Content-Type-Options: nosniff sur toutes les réponses (protections.BASE)"),
    "V14.4.5": ("partiel", "HSTS posé si HACKVS_HSTS=1 (production derrière HTTPS) ; éteint en démo (test_hsts_seulement_quand_on_le_demande)"),
    "V14.4.6": ("conforme", "Referrer-Policy: no-referrer"),
    "V14.4.7": ("conforme", "X-Frame-Options SAMEORIGIN + frame-ancestors ; seul le deck LOCAL peut intégrer l'écran de salle"),
    "V14.5.2": ("conforme", "l'Origin sert seulement à REFUSER (CSRF), jamais à autoriser"),
    "V14.5.3": ("conforme", "aucun en-tête CORS : pas d'origine tierce autorisée"),
    "V14.2.1": ("partiel", "versions exactes figées (constraints.txt) ; pas de vérificateur de dépendances automatique (CI bloquée)"),
    "V14.1.1": ("partiel", "Dockerfile et docker-compose.annee1.yml reproductibles ; image non construite dans cette session"),
}


def main() -> int:
    lignes = [x for x in csv.DictReader(CSV.open(encoding="utf-8")) if x["level2"].strip()]
    inconnues = sorted(set(EVAL) - {x["req_id"] for x in lignes})
    if inconnues:
        print("exigences inconnues dans EVAL :", inconnues)
        return 1
    compte = Counter(EVAL.get(x["req_id"], ("non évaluée", ""))[0] for x in lignes)
    out = ["# OWASP ASVS 4.0.3 — niveau 2 : statut de chaque exigence", "",
           "> **Construit — branche `annee-1`, pas dans la démo.** Auto-évaluation de l'équipe, PAS un audit externe ni une",
           "> certification. Généré par `python prototype/scripts/asvs_l2.py` depuis le fichier officiel de l'OWASP",
           "> (`asvs-4.0.3-en.csv`, CC BY-SA 3.0). Une exigence n'est « conforme » qu'avec une preuve (test ou fichier) ;",
           "> sans examen, elle reste « non évaluée ».", "",
           f"**{len(lignes)} exigences de niveau 2** : " + " · ".join(f"{s} : {compte.get(s, 0)}" for s in STATUTS), "",
           "| Exigence | Intitulé (OWASP, anglais) | Statut | Preuve |", "|---|---|---|---|"]
    for x in lignes:
        statut, preuve = EVAL.get(x["req_id"], ("non évaluée", ""))
        texte = " ".join(x["req_description"].split("([C")[0].split()).replace("|", "\\|")
        out.append(f"| {x['req_id']} | {texte[:160]}{'…' if len(texte) > 160 else ''} | {statut} | {preuve.replace('|', '/')} |")
    SORTIE.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(lignes)} exigences → {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
