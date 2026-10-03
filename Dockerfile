# Image de démonstration Club Pulse + prototype « Le Fil du Club » (données fictives). Une seule instance (voir fin).
# Construire depuis la racine du dépôt :  docker build -t fil-du-club .
# Lancer :                                 docker run -p 8080:8080 fil-du-club   →  http://localhost:8080
ARG BASE=python:3.11-slim
FROM ${BASE}
ENV ORT_DISABLE_TELEMETRY=1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 HACKVS_MODE=demo HACKVS_DB=/tmp/fil.db \
    HACKVS_ESSAIS_DB=/srv/prototype/var/club_pulse.db
WORKDIR /srv
COPY prototype/requirements.txt prototype/requirements.txt
COPY prototype/constraints.txt prototype/constraints.txt
RUN apt-get update && apt-get install -y --no-install-recommends libsodium23 && rm -rf /var/lib/apt/lists/*  # intentions scellées : ristretto255 (sinon repli plus lent)
RUN pip install --no-cache-dir -r prototype/requirements.txt -c prototype/constraints.txt   # versions exactes testées
# ANNÉE 1 · LOT 1 : journal sur PostgreSQL (HACKVS_ESSAIS_DB=postgresql://…) — `docker build --build-arg AVEC_POSTGRES=1`
ARG AVEC_POSTGRES=0
RUN if [ "$AVEC_POSTGRES" = "1" ]; then pip install --no-cache-dir "psycopg[binary]>=3.1"; fi
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
# Journal de Club Pulse : /srv/prototype/var/club_pulse.db — un volume (`-v pulse:/srv/prototype/var`) le garde d'un
# conteneur à l'autre. Secrets : HACKVS_SECRET (≥ 32 caractères, STABLE : sessions, passes juré et rejeu IA en dépendent)
# et HACKVS_CONSOLE_JETON se passent à `docker run -e`. Sans secret : secret aléatoire par démarrage (sessions
# invalidées, sorties IA non rejouées après un redémarrage). Sans jeton, la console du Club ne répond qu'à la machine
# locale — depuis l'hôte d'un conteneur, il FAUT donc `-e HACKVS_CONSOLE_JETON=<jeton>` (la console le demande).
# ANNÉE 1 · LOT 1 : disponibilité — le journal répond et son schéma est au dernier niveau (/sante/pret)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/sante/pret', timeout=4)" || exit 1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-access-log --timeout-keep-alive 5"]
