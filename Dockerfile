# Image de démonstration Club Pulse + prototype « Le Fil du Club » (données fictives). Une seule instance (voir fin).
# Construire depuis la racine du dépôt :  docker build -t fil-du-club .
# Lancer :                                 docker run -p 8080:8080 fil-du-club   →  http://localhost:8080
ARG BASE=python:3.11-slim
FROM ${BASE}
ENV ORT_DISABLE_TELEMETRY=1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 HACKVS_MODE=demo HACKVS_DB=/tmp/fil.db
WORKDIR /srv
COPY prototype/requirements.txt prototype/requirements.txt
COPY prototype/constraints.txt prototype/constraints.txt
RUN apt-get update && apt-get install -y --no-install-recommends libsodium23 && rm -rf /var/lib/apt/lists/*  # intentions scellées : ristretto255 (sinon repli plus lent)
RUN pip install --no-cache-dir -r prototype/requirements.txt -c prototype/constraints.txt   # versions exactes testées
COPY prototype/app prototype/app
COPY prototype/intelligence prototype/intelligence
COPY prototype/prompts prototype/prompts
COPY prototype/experiences prototype/experiences
COPY prototype/plateforme prototype/plateforme
COPY prototype/adaptateurs prototype/adaptateurs
COPY prototype/data prototype/data
COPY prototype/web prototype/web
COPY docs/captures docs/captures
WORKDIR /srv/prototype
RUN useradd --create-home app && chown -R app /srv
USER app
EXPOSE 8080
# Une seule instance : SQLite et le flux temps réel sont locaux au conteneur.
# Secrets : HACKVS_SECRET (≥ 32 caractères) et HACKVS_CONSOLE_JETON se passent à `docker run -e`. Sans secret : secret
# aléatoire par démarrage (sessions invalidées au redémarrage). Sans jeton, la console du Club ne répond qu'à la machine
# locale — depuis l'hôte d'un conteneur, il FAUT donc `-e HACKVS_CONSOLE_JETON=<jeton>` (la console le demande).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-access-log --timeout-keep-alive 5"]
