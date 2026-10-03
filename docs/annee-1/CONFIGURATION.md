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
| `HACKVS_HSTS` | `0` | **lot 6** — `1` : en-tête Strict-Transport-Security (production derrière HTTPS seulement) |
| `HACKVS_ANCIEN_PROTOTYPE` | `0` | `1` : sert aussi l'ancien prototype (local ou jeton) |

## Serveur

| Variable | Défaut | Rôle |
|---|---|---|
| `PORT` | `8080` (image Docker) | port d'écoute du conteneur (commande `uvicorn` de l'image) |
| `HACKVS_JOURNAL` | `INFO` | niveau des journaux structurés (JSON) ; une valeur inconnue arrête le démarrage |

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
| `HACKVS_SECRETARIAT` | `0` | **lot 4** — `1` (avec `HACKVS_COMPTES=1`) : console du secrétariat (`/secretariat`) — compte nominatif, double authentification et session élevée exigés |
| `CHROMIUM` | `/opt/pw-browsers/chromium` | **lot 4** — navigateur qui imprime le bilan en PDF, si Playwright ne trouve pas le sien |
| `HACKVS_CRITERES_PILOTE` | `docs/annee-1/pilote/criteres.json` | **lot 4** — fichier des critères du pilote (gelés par empreinte depuis la console) |
| `HACKVS_NOTIFICATIONS` | `0` | **lot 5** — `1` : notifications (relance depuis la console, désinscription `/desinscription`) |
| `HACKVS_SMS` | (vide : simulé) | **lot 5** — `faux` : faux fournisseur SMS en mémoire (tests) ; aucun vrai fournisseur branché |
| `HACKVS_ESPACE_MEMBRE` | `0` | **lot 3** — `1` : espace membre (`/espace` : pause, préférences, mes demandes, export, effacement définitif) |

## E-mail (lot 5 — sans `SMTP_HOST`, tout est simulé)

| Variable | Défaut | Rôle |
|---|---|---|
| `SMTP_HOST` | (vide : simulé) | serveur SMTP |
| `SMTP_PORT` | `587` | port |
| `SMTP_STARTTLS` | `1` | `0` : sans STARTTLS (serveur local de test seulement) |
| `SMTP_DELAI_S` | `15` | délai d'une opération SMTP (l'envoi se fait hors du verrou du monde) |
| `SMTP_UTILISATEUR` | (vide) | identifiant SMTP |
| `SMTP_MOT_DE_PASSE` | (vide) | **secret** — mot de passe SMTP |
| `SMTP_EXPEDITEUR` | `club@exemple.invalid` | adresse d'expédition |

## Intelligence artificielle (facultative : le Club marche pareil sans)

| Variable | Défaut | Rôle |
|---|---|---|
| `LLM_PROVIDER` | (vide : forme déterministe) | fournisseur choisi (`apertus`, …) |
| `APERTUS_BASE_URL` | (vide) | adresse de l'API d'Apertus (servi par le CSCS) |
| `APERTUS_MODEL` | (vide) | modèle (ex. `swiss-ai/Apertus-v1.5-70B`) |
| `APERTUS_API_KEY` | (vide) | **secret** — clé de l'API d'Apertus |
| `APERTUS_DELAI_S` | `30` | délai d'un appel (secondes) |
| `APERTUS_BUDGET_S` | `12` | budget TOTAL d'une complétion, tentatives comprises (le repli arrive avant que le téléphone abandonne) |
| `OPENAI_API_KEY` | (vide) | **secret** — fournisseur `openai` (API compatible OpenAI) |
| `OPENAI_MODEL` | (vide) | modèle du fournisseur `openai` |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | adresse du fournisseur `openai` |
| `OPENAI_TEMPERATURE` | `0` | température (`defaut` : non envoyée) |
| `OPENAI_DELAI_S` · `OPENAI_BUDGET_S` | `30` · `12` | délai d'un appel · budget total |
| `ANTHROPIC_MODEL` | (vide) | modèle du fournisseur `claude` |
| `HACKVS_ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | adresse du fournisseur `claude` |
| `ANTHROPIC_TEMPERATURE` | `0` | température (`defaut` : non envoyée) |
| `ANTHROPIC_DELAI_S` · `ANTHROPIC_BUDGET_S` | `30` · `12` | délai d'un appel · budget total |
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
