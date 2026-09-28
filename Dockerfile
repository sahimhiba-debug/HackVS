# Image de démonstration « Le Fil du Club » (données fictives).
# Construire depuis la racine du dépôt :  docker build -t fil-du-club .
# Lancer :                                 docker run -p 8080:8080 fil-du-club   →  http://localhost:8080
ARG BASE=python:3.11-slim
FROM ${BASE}
ENV ORT_DISABLE_TELEMETRY=1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 HACKVS_MODE=demo HACKVS_DB=/tmp/fil.db
WORKDIR /srv
COPY prototype/requirements.txt prototype/requirements.txt
RUN pip install --no-cache-dir -r prototype/requirements.txt
COPY prototype/app prototype/app
COPY prototype/data prototype/data
COPY prototype/web prototype/web
COPY docs/captures docs/captures
WORKDIR /srv/prototype
RUN useradd --create-home app && chown -R app /srv
USER app
EXPOSE 8080
# Une seule instance : SQLite et le flux temps réel sont locaux au conteneur.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
