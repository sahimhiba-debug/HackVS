> **HISTORIQUE — rédigé avant le registre des capacités (28–30.09.2026).** Conservé pour la traçabilité des décisions ; ne décrit PAS le produit actuel, et ses chiffres, routes et noms de fichiers peuvent être faux aujourd'hui. État actuel : [README](/README.md) · [index de la documentation](/docs/README.md).

# Déploiement (facultatif) : une URL publique pour que le jury essaie sur son téléphone

**Rien n'a été déployé.** Publier une URL expose le prototype sur Internet : c'est une décision de Hiba.
Données 100 % fictives, aucun secret requis en mode règles.

## Image Docker (vérifiée le 28.09.2026)
```bash
docker build -t fil-du-club .                       # depuis la racine du dépôt
docker run -p 8080:8080 fil-du-club                 # http://localhost:8080 · /scene · /presentation · /club · /rejoindre
```
Vérifié ici : image de 249 Mo, utilisateur non root, pages principales et QR code répondent 200.
Deux adaptations ont été **propres à l'environnement de vérification** (non commitées) : l'image de base tirée de
`mirror.gcr.io` (Docker Hub répondait 429) et le certificat du proxy de l'environnement ajouté pour `pip`.
Si Docker Hub limite vos téléchargements : `docker build --build-arg BASE=mirror.gcr.io/library/python:3.11-slim -t fil-du-club .`

## Cloud Run (GCP, région Zurich)
```bash
gcloud run deploy fil-du-club --source . --region europe-west6 \
  --min-instances 1 --max-instances 1 --timeout 3600 --session-affinity \
  --allow-unauthenticated --memory 512Mi
# puis, avec l'URL obtenue :
gcloud run services update fil-du-club --region europe-west6 --set-env-vars HACKVS_URL_PUBLIQUE=https://…run.app
```
Pourquoi ces options :
- **une seule instance** (`--max-instances 1`) : SQLite et le flux temps réel sont locaux au conteneur ; deux instances verraient deux Clubs différents ;
- **`--min-instances 1`** : pas de démarrage à froid pendant le pitch, au prix d'un coût faible mais non nul tant que le service existe ;
- **`--timeout 3600` et `--session-affinity`** : les flux temps réel (SSE) restent ouverts ;
- **`--allow-unauthenticated`** : rend l'URL publique (**décision de Hiba**) ; à supprimer après l'événement (`gcloud run services delete fil-du-club --region europe-west6`).
- Données : `/tmp/fil.db`, **effacées à chaque redémarrage** (voulu pour une démo).

Claude en production : ajouter la clé via Secret Manager (`--set-secrets ANTHROPIC_API_KEY=…:latest`) et `HACKVS_LLM=claude`. Jamais en clair.

## Sans cloud : même réseau Wi-Fi
`uvicorn app.main:app --host 0.0.0.0` puis `HACKVS_URL_PUBLIQUE=http://<ip-du-portable>:8000`. Le QR de `/rejoindre` et de la dernière diapositive pointe alors vers le portable. Dépend du Wi-Fi de la salle (souvent filtré).
