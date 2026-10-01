# Déploiement public sur Cloud Run — procédure reproductible (01.10.2026)

**Rien n'est déployé à ce jour.** Publier une URL expose le prototype (monde 100 % fictif) sur Internet : décision et
compte GCP de Hiba. Cette procédure remplace, pour Club Pulse, le guide historique `docs/DEPLOIEMENT.md`.

## Ce qui a été vérifié avant (image construite depuis le commit `29a5063`)

- Image du `Dockerfile` du dépôt : 551 Mo, utilisateur non root, écoute sur `$PORT`, démarrage ≈ 5 s.
  Dans l'environnement de vérification seulement : image de base tirée de `mirror.gcr.io` (Docker Hub : 429) et
  `apt-get` retiré (Debian bloqué par le réseau de l'environnement) — sans effet sur Club Pulse. Cloud Build utilise le
  `Dockerfile` tel quel.
- Conteneur lancé avec `HACKVS_SECRET`, `HACKVS_CONSOLE_JETON`, `HACKVS_URL_PUBLIQUE` et la vraie API Apertus (CSCS) :
  **29/29** contrôles — `/app`, `/console`, `/etabli`, `/projection`, `/demo/regie` (200 + CSP), console fermée sans
  le jeton (403), jeton transmis aux onglets ouverts depuis la console, régie montée, QR juré décodé =
  `<URL_PUBLIQUE>/app?jure=…`, passe juré ouvert sur un téléphone simulé. « Comprendre ma demande » a réellement
  appelé Apertus depuis le conteneur (3,6 s et 7,0 s ; une sortie acceptée, une rejetée → repli). Aucune erreur 500.
- Non vérifié : un vrai déploiement Cloud Run, un vrai téléphone sur un réseau mobile.

## Commandes (à lancer par Hiba, depuis la racine du dépôt, sur le commit voulu — `gel-demo` après le gel)

```bash
PROJET=<id-du-projet-gcp>
REGION=europe-west6                    # Zurich
SERVICE=club-pulse
gcloud config set project "$PROJET"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# 1. Secrets — SANS retour à la ligne (le jeton de console est comparé à l'octet près)
python3 -c "import secrets; print(secrets.token_urlsafe(48), end='')" | gcloud secrets create hackvs-secret --data-file=-
python3 -c "import secrets; print(secrets.token_urlsafe(24), end='')" | gcloud secrets create hackvs-console-jeton --data-file=-
# facultatif — IA réelle : la clé CSCS, tapée sans écho (jamais dans l'historique du terminal ni dans le dépôt)
read -rs CLE && printf '%s' "$CLE" | gcloud secrets create apertus-api-key --data-file=- && unset CLE
NUM=$(gcloud projects describe "$PROJET" --format='value(projectNumber)')
for s in hackvs-secret hackvs-console-jeton apertus-api-key; do
  gcloud secrets add-iam-policy-binding "$s" --role=roles/secretmanager.secretAccessor \
    --member="serviceAccount:${NUM}-compute@developer.gserviceaccount.com"
done

# 2. Construction (Cloud Build, Dockerfile du dépôt) et déploiement
#    sans IA : retirer la ligne APERTUS_* de --set-env-vars et « ,APERTUS_API_KEY=… » de --set-secrets
gcloud run deploy "$SERVICE" --source . --region "$REGION" \
  --min-instances 1 --max-instances 1 --session-affinity --timeout 300 --memory 512Mi --cpu 1 \
  --allow-unauthenticated \
  --set-secrets HACKVS_SECRET=hackvs-secret:latest,HACKVS_CONSOLE_JETON=hackvs-console-jeton:latest,APERTUS_API_KEY=apertus-api-key:latest \
  --set-env-vars APERTUS_BASE_URL=https://api.inference.cscs.ch/v1,APERTUS_MODEL=swiss-ai/Apertus-v1.5-70B,APERTUS_BUDGET_S=12 \
  --labels commit=$(git rev-parse --short HEAD)

# 3. L'URL publique, réinjectée pour le QR juré (crée une révision → monde neuf : à faire AVANT la présentation)
URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
gcloud run services update "$SERVICE" --region "$REGION" --update-env-vars HACKVS_URL_PUBLIQUE="$URL"
echo "$URL"

# 4. Contrôles
for p in /app /console /etabli /projection /demo/regie; do curl -s -o /dev/null -w "$p %{http_code}\n" "$URL$p"; done   # 200
curl -s -o /dev/null -w "console sans jeton : %{http_code}\n" -H "X-Pulse-Console: 1" "$URL/api/pulse/console/personas"  # 403
gcloud secrets versions access latest --secret hackvs-console-jeton; echo                                               # à saisir dans /console

# 5. Après l'événement
gcloud run services delete "$SERVICE" --region "$REGION"
for s in hackvs-secret hackvs-console-jeton apertus-api-key; do gcloud secrets delete "$s" --quiet; done
```

## Pourquoi ces réglages

| Réglage | Raison |
|---|---|
| `--max-instances 1` | **impératif** : le monde, le journal SQLite et le verrou sont dans le conteneur ; deux instances = deux Clubs |
| `--min-instances 1` | pas de démarrage à froid pendant le pitch (coût faible mais continu tant que le service existe) |
| `--session-affinity` | sans effet avec une instance ; garde le même comportement si l'on en ajoutait une par erreur |
| `HACKVS_CONSOLE_JETON` | **obligatoire** : avec lui, la console exige ce jeton exact et ne regarde plus l'adresse ; sans lui, elle n'accepte que la machine locale — sur Cloud Run, où la requête n'arrive pas de 127.0.0.1, elle devrait refuser tout le monde (403), animatrice comprise — non vérifié sur Cloud Run |
| `HACKVS_SECRET` (≥ 32 car.) | sessions et passes juré valides tant que l'instance vit |
| `HACKVS_URL_PUBLIQUE` | le QR juré encode `<URL>/app?jure=…` ; sans elle, il encoderait l'adresse interne |
| `APERTUS_*` (facultatif) | « Comprendre ma demande » appelle Apertus ; budget 12 s puis repli ; sans ces variables : règles simples, dites à l'écran |
| SQLite dans le conteneur | **le monde repart à neuf** à chaque nouvelle révision ou redémarrage de l'instance — voulu pour une démo |
| Healthcheck | aucun point dédié : la sonde de démarrage TCP par défaut de Cloud Run suffit ; `GET /app` → 200 pour un contrôle manuel |

## À décider avant de publier (Hiba)

1. **IA allumée sur l'URL publique ?** Mesuré le 01.10 (CLAIMS n° 39–40) : sortie acceptée et juste 1/26 ; latence médiane
   5,3 s. Allumée : le juré attend ≈ 5–7 s et voit le plus souvent « Règles simples, aucun modèle utilisé » (sortie
   rejetée → repli) — honnête, mais peu flatteur. Éteinte (sans `APERTUS_*`) : réponse immédiate par les règles.
   L'interrupteur de la console (« Éteindre l'IA ») bascule sans redéployer.
2. Compte GCP et facturation ; suppression du service après l'événement.

Rappels : ne jamais mettre une URL fictive dans le dépôt ; ne jamais passer une clé par `--set-env-vars`.
