# Déploiement de la démonstration sur un VPS Infomaniak (Ubuntu) — pas à pas

Écrit pour la **session Claude Code locale sur l'iMac d'Hiba**, qui déploiera en SSH. Rien n'a été déployé depuis la
session cloud (aucun accès SSH, aucun démon Docker : l'image n'y a pas été construite — la première construction se
fera sur le VPS ; `docker compose config` a validé le fichier). L'ancien guide Cloud Run reste dans
[DEPLOIEMENT_CLOUD_RUN.md](DEPLOIEMENT_CLOUD_RUN.md).

## Ce qu'Hiba doit fournir (liste exacte)

| # | Quoi | Où ça va | Remarque |
|---|---|---|---|
| 1 | **Adresse IP** du VPS et **utilisateur SSH** (avec `sudo`) | session locale : `ssh <utilisateur>@<ip>` | clé SSH déjà installée sur le VPS |
| 2 | **Nom de domaine** (ex. `pulse.<domaine>.ch`) avec un enregistrement **A** (et AAAA si IPv6) vers l'IP du VPS | `.env` : `DOMAINE`, `PUBLIC_BASE_URL=https://<domaine>` | propagé AVANT le premier `deploy.sh` (Caddy obtient le certificat au démarrage) |
| 2b | Un **second sous-domaine** pour le monde « visite » (ex. `visite.pulse.<domaine>.ch`), même IP | `.env` : `DOMAINE_VISITE`, `PUBLIC_VISITE_URL` | bac à sable fictif, console ouverte : le jury explore après le pitch depuis `/feuille-de-route` |
| 3 | **Ports 80 et 443 ouverts** (pare-feu Infomaniak et `ufw`) | — | HTTPS automatique par Caddy |
| 4 | Un **secret** de 48 caractères (généré sur place) | `.env` : `HACKVS_SECRET` | `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` — ne jamais le mettre dans le dépôt |
| 5 | Un **jeton de console** (généré sur place) | `.env` : `HACKVS_CONSOLE_JETON` | à saisir une fois dans le navigateur de l'écran géant et de la télécommande |
| 6 | Facultatif : la **clé Apertus** (API CSCS) | `.env` : `APERTUS_API_KEY` | sans clé : forme déterministe, dite à l'écran |
| 7 | Accès en lecture au dépôt GitHub depuis le VPS (clé de déploiement ou jeton) | `git clone` | le dépôt est privé |

## Commandes pour la session locale (dans l'ordre)

```sh
# 0. depuis l'iMac
ssh <utilisateur>@<ip>

# 1. une seule fois : Docker et le dépôt
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git curl
sudo usermod -aG docker "$USER" && newgrp docker
sudo ufw allow 80,443/tcp && sudo ufw allow 443/udp
git clone <url-du-dépôt> club-pulse && cd club-pulse && git checkout foire-2026   # ou main après la fusion d'Hiba

# 2. une seule fois : la configuration (aucun secret dans le dépôt)
cp .env.example .env && chmod 600 .env
nano .env           # DOMAINE, PUBLIC_BASE_URL, DOMAINE_VISITE, PUBLIC_VISITE_URL, HACKVS_SECRET, HACKVS_CONSOLE_JETON (+ APERTUS_API_KEY)

# 3. déployer (et à chaque mise à jour)
./deploy.sh         # pull, build, redémarrage, vérification de /sante — « OK » ou les journaux en cas d'échec

# 4. contrôle de charge contre le serveur déployé (même script que la mesure locale, PREUVES.md)
cd prototype && python3 scripts/charge_salle.py --url "https://<domaine>" --jeton "<HACKVS_CONSOLE_JETON>" --n 80

# 5. APRÈS LE PITCH : tout effacer du mode salle (et vérifier)
./purge.sh          # ou ./purge.sh --tout pour effacer aussi le journal du Club
```

## Pendant le pitch

- **Écran géant** : `https://<domaine>/salle/ecran` (saisir le jeton de console une fois) — QR, compteur, constellation.
- **Télécommande** : `https://<domaine>/salle/regie` (téléphone ou portable du présentateur, même jeton).
- **Téléphones de la salle** : ils scannent le QR ; aucun compte, aucun nom ; passe de 2 heures ; 80 au plus.
- Tous les liens et QR partent de `PUBLIC_BASE_URL` : si le domaine change, modifier `.env` puis `./deploy.sh`.

## Ce que la configuration garantit (et ses limites)

- **Une seule instance** de l'application : le journal SQLite (`volume pulse`) et le mode salle (en mémoire) sont
  locaux au conteneur. Le mode salle ne survit pas à un redémarrage — voulu : c'est une séance de cinq minutes.
- Derrière Caddy, la console exige le jeton (`HACKVS_CONSOLE_JETON`) : sans lui, elle refuse tout.
- Aucun secret dans le dépôt (`.env` est ignoré par git ; test `test_deploiement.py`).
- **Non vérifié ici** : la construction de l'image sur le VPS, le certificat, la charge réelle à travers Internet —
  à faire à l'étape 3 et 4, et à consigner dans PREUVES.md (« serveur déployé »).
