# Configuration — toutes les variables d'environnement

> **Construit — branche `annee-1`, pas dans la démo.** Liste tenue à jour par un test :
> `prototype/tests/test_annee1_exploitation.py` échoue si le serveur lit une variable qui n'est pas ici.

Règles :

- **Aucun secret dans un fichier du dépôt.** Les variables marquées *secret* se passent par l'environnement du
  processus (`docker run -e`, fichier `.env` hors dépôt, gestionnaire de secrets de l'hébergeur).
- Interrupteur = `1` pour allumer, toute autre valeur pour éteindre, sauf mention contraire.
- Les valeurs par défaut sont celles du code ; « démo » signale ce que le lanceur du jour J règle lui-même.

## Stockage et données

| Variable | Défaut | Rôle |
|---|---|---|
| `HACKVS_ESSAIS_DB` | `:memory:` | **Journal du Club** (tout l'état métier). Chemin → SQLite ; `postgresql://…` → PostgreSQL (lot 1). Mot de passe : jamais dans l'adresse écrite dans un fichier — `PGPASSWORD` ou `~/.pgpass` |
| `HACKVS_DB` | `var/fil_<mode>.db` | base de l'ancien prototype « Le Fil du Club » |
| `HACKVS_CYCLE_DB` | `var/reseau_<mode>.db` | mémoire du réseau de l'ancien prototype |
| `HACKVS_DECISIONS_DB` | `var/decisions_demo.db` | plateforme de décision de l'ancien prototype |
| `HACKVS_PROFILS` | (vide) | fichier de profils de l'ancien prototype |
| `HACKVS_ENTREPRISES_CSV` | CSV du dépôt | liste des entreprises du Club (colonne métier seulement) |

## Sécurité et accès

| Variable | Défaut | Rôle |
|---|---|---|
| `HACKVS_SECRET` | aléatoire à chaque démarrage | **secret** — signe les sessions, passes, empreintes de rejeu ; ≥ 32 caractères, STABLE en production |
| `HACKVS_CONSOLE_JETON` | (aucun : console limitée à cette machine) | **secret** — jeton de la console du Club ; exigé derrière un tunnel ou sur un serveur joignable |
| `HACKVS_DECK_ORIGINES` | `http://127.0.0.1:8765 http://localhost:8765` | origines du deck local autorisées à intégrer l'écran de la salle (boucle locale seulement) |
| `HACKVS_K_ANONYMAT` | `3` | seuil « < k » du mode salle (compté en entreprises distinctes ailleurs) |
| `HACKVS_ANCIEN_PROTOTYPE` | `0` | `1` : sert aussi l'ancien prototype (local ou jeton) |

## Adresses publiques

| Variable | Défaut | Rôle |
|---|---|---|
| `PUBLIC_BASE_URL` | (adresse de la requête) | adresse publique (tunnel, déploiement) : liens et QR en partent |
| `HACKVS_URL_PUBLIQUE` | (vide) | compatibilité : adresse du point d'accès du portable en salle (v1) |
| `PUBLIC_VISITE_URL` | (vide) | adresse publique du monde « visite » |
| `HACKVS_API_URL` | `http://localhost:8000` | adresse de l'API pour le serveur MCP |
| `HACKVS_MCP_URL_PUBLIQUE` | `http://<hôte>:<port>` | adresse publique du serveur MCP |

## Fonctionnalités (interrupteurs)

| Variable | Défaut | Rôle |
|---|---|---|
| `HACKVS_MODE` | `demo` | mode du serveur (monde de démonstration fictif) |
| `HACKVS_FOIRE` | `1` | nouveautés Foire 2026 (Suivi, passe découverte, Le Club cherche…) ; `0` : la démo d'avant |
| `HACKVS_SALLE` | `1` | mode salle (QR, constellation, régie) |
| `HACKVS_SALLE_MIN` | `5` | participants minimum avant la bascule scriptée |
| `HACKVS_SALLE_PLAFOND` | `80` | places dans la salle |
| `HACKVS_VISITE` | `0` | `1` : monde « visite » (bac à sable public, conteneur à part) |
| `HACKVS_RECU_27560` | `1` | reçus alignés ISO/IEC TS 27560 (aligné, pas certifié) |
| `HACKVS_COACH_SMART` | `1` | questions du coach de demande SMART |
| `HACKVS_DECOUVERTE_JOURS` | `90` | durée du passe découverte |
| `HACKVS_ASKS_MONTREES` | `1` | demandes montrées à la fois à un membre |
| `HACKVS_PLAFOND_JOURS` | `7` | fenêtre du plafond de sollicitations |
| `HACKVS_BUDGET_NOEUDS` | `20000` | budget de nœuds du compositeur |
| `HACKVS_BUDGET_RELANCE` | `1000000` | budget de la relance |
| `HACKVS_SOIREE_DEBUT` | `2026-10-03T18:30` | début de la soirée (ancien prototype) |
| `HACKVS_METRIQUES` | `0` | **lot 1** — `1` : sert `/metriques` (cette machine ou jeton de console seulement) |
| `HACKVS_COMPTES` | `0` | **lot 2** — `1` : comptes, rôles, double authentification (`/compte`, `/api/pulse/comptes/…`) |
| `HACKVS_ESPACE_MEMBRE` | `0` | **lot 3** — `1` : espace membre (`/espace` : pause, préférences, mes demandes, export, effacement définitif) |

## Intelligence artificielle (facultative : le Club marche pareil sans)

| Variable | Défaut | Rôle |
|---|---|---|
| `LLM_PROVIDER` | (vide : forme déterministe) | fournisseur choisi (`apertus`, …) |
| `APERTUS_BASE_URL` | (vide) | adresse de l'API d'Apertus (servi par le CSCS) |
| `APERTUS_MODEL` | (vide) | modèle (ex. `swiss-ai/Apertus-v1.5-70B`) |
| `APERTUS_API_KEY` | (vide) | **secret** — clé de l'API d'Apertus |
| `APERTUS_APPEL_OUTILS` | `0` | appel d'outils natif (mesuré : aucun gain sur les 26 cas) |
| `APERTUS_NOTES_PRIVEES` | `0` | `1` : les notes privées peuvent partir vers l'IA (consentement) |
| `HACKVS_LLM` | (vide) | ancien prototype : fournisseur (`claude`…) |
| `HACKVS_CLAUDE_MODEL` | (défaut du code) | ancien prototype : modèle |
| `ANTHROPIC_API_KEY` | (vide) | **secret** — ancien prototype |
| `ANTHROPIC_AUTH_TOKEN` | (vide) | **secret** — ancien prototype |
| `HACKVS_SEMANTIQUE` | `1` | suggestions sémantiques locales (si le modèle est présent) |
| `HACKVS_SEMANTIQUE_AUTO` | `0` | analyse sémantique automatique |
| `HACKVS_MODELE_SEMANTIQUE` | `var/modeles/…` | dossier du modèle ONNX local |

## Serveur MCP (assistants)

| Variable | Défaut | Rôle |
|---|---|---|
| `HACKVS_MCP_JETONS` | `var/mcp_jetons.json` | **secret** (fichier) — jetons des assistants |
| `HACKVS_MCP_MEMBRE` | `p00` | membre par défaut (démo) |
| `HACKVS_MCP_CONFIRMATION` | `exigee` | `client` : confirmation déléguée au client MCP |

## Jour J (lanceur du Mac, `prototype/app/jour_j.py`)

| Variable | Défaut | Rôle |
|---|---|---|
| `CLUBPULSE_BUREAU` | `~/Desktop` | où chercher le film |
| `CLUBPULSE_DOSSIER` | `~/.clubpulse` | jeton, journaux, PID (hors dépôt) |
| `CLUBPULSE_FILM_DECK` | `docs/presentation/deck/assets/film.mp4` | copie du film dans le deck |
| `CLUBPULSE_DECK_URL` | `http://127.0.0.1:8765/v2.html` | deck sondé par la check-list |
