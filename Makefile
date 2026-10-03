# Club Pulse — commandes du dépôt. Chaque cible échoue (code ≠ 0) au premier contrôle en échec.
#   make setup          dépendances (exécution + facultatives + outils), versions exactes de constraints.txt
#   make quality-check  TOUT : secrets, lint, types, tests, bout en bout, évaluations, cohérence du pitch
#   make demo           serveur de démonstration : http://127.0.0.1:8000/console et /app
#   make demo HOTE=0.0.0.0 URL_PUBLIQUE=http://<ip-du-portable>:8000
#                       la même, joignable par de VRAIS téléphones (point d'accès du portable) ; la console reste
#                       réservée à cette machine
PY ?= python
P = prototype
export HACKVS_SEMANTIQUE ?= 0
HOTE ?= 127.0.0.1
URL_PUBLIQUE ?=

.PHONY: setup browsers lint typecheck test e2e e2e-salle sonde-ia latence-ia banc-ia banc-ia-dry-run banc-ia-comparer eval secrets audit coverage demo quality-check mutation perf

setup:
	cd $(P) && $(PY) -m pip install -r requirements-dev.txt -c constraints.txt

browsers:
	cd $(P) && $(PY) -m playwright install chromium

secrets:
	$(PY) $(P)/scripts/verifier_secrets.py

lint:
	cd $(P) && $(PY) -m ruff check .

typecheck:
	cd $(P) && $(PY) -m mypy app adaptateurs plateforme intelligence

E2E = tests/test_e2e_scene.py tests/test_e2e_pulse.py tests/test_e2e_action.py tests/test_e2e_capacites.py tests/test_e2e_hermetique.py tests/test_e2e_serveur.py tests/test_e2e_ia.py tests/test_e2e_foire.py

test:
	cd $(P) && $(PY) -m pytest -q $(addprefix --ignore=,$(E2E))

e2e:
	cd $(P) && HACKVS_FOIRE=$${HACKVS_FOIRE:-1} HACKVS_E2E_OBLIGATOIRE=1 $(PY) -m pytest -q tests/test_e2e_scene.py tests/test_e2e_pulse.py tests/test_e2e_action.py tests/test_e2e_capacites.py tests/test_e2e_hermetique.py tests/test_e2e_serveur.py tests/test_e2e_ia.py tests/test_e2e_foire.py

# Mode salle : les mêmes E2E, réseau LOCAL seul (espace réseau vide, extérieur injoignable vérifié) et IA OFF
e2e-salle:
	cd $(P) && sudo -E env "PATH=$$PATH" HACKVS_FOIRE=$${HACKVS_FOIRE:-1} HACKVS_E2E_OBLIGATOIRE=1 unshare --net $(PY) scripts/mode_salle.py -- \
	  $(PY) -m pytest -q tests/test_e2e_scene.py tests/test_e2e_pulse.py tests/test_e2e_action.py tests/test_e2e_capacites.py tests/test_e2e_hermetique.py tests/test_e2e_serveur.py tests/test_e2e_ia.py tests/test_e2e_foire.py

# Sonde du fournisseur de langage (clé en variable d'environnement APERTUS_API_KEY ; sans clé : UNKNOWN, dit)
sonde-ia:
	cd $(P) && $(PY) scripts/sonde_publicai.py

# Latence RÉELLE d'Apertus (n appels séquentiels, médiane, p95, erreurs) → docs/audit/latence_apertus.md. Preuve technique
# SÉPARÉE de la démonstration (qui tourne sans modèle). Exige APERTUS_API_KEY, APERTUS_BASE_URL, APERTUS_MODEL ; N=30 par défaut.
N ?= 30
latence-ia:
	cd $(P) && $(PY) scripts/mesurer_latence_apertus.py --n $(N)

# Banc MÉTIER de la tâche IA du produit (comprendre_action, 26 cas fictifs figés, attentes fixées avant exécution), par
# le chemin du produit, pour UN fournisseur → eval/resultats_banc/<fournisseur>.md (+ .json, sorties brutes).
#   make banc-ia FOURNISSEUR=apertus|openai|claude   (exige les variables de ce fournisseur ; sinon rien n'est appelé)
#   make banc-ia-dry-run                              (fournisseurs FACTICES, aucun réseau → prototype/var/banc_dry_run/)
#   make banc-ia-comparer                             (comptes côte à côte → eval/resultats_banc/comparaison.md)
# Docs : docs/BANC_MULTI_FOURNISSEURS.md
FOURNISSEUR ?= apertus
banc-ia:
	cd $(P) && $(PY) -m eval.banc_comprendre_action --fournisseur $(FOURNISSEUR)

banc-ia-dry-run:
	cd $(P) && env -u APERTUS_API_KEY -u OPENAI_API_KEY -u ANTHROPIC_API_KEY $(PY) -m eval.banc_comprendre_action --dry-run tous \
	  && $(PY) -m eval.comparer_bancs --dossier var/banc_dry_run

banc-ia-comparer:
	cd $(P) && $(PY) -m eval.comparer_bancs

eval:
	cd $(P) && $(PY) -m eval.run_eval --verifier && $(PY) -m eval.eval_decisions --verifier \
	  && $(PY) scripts/validate_competition_claims.py --sans-benchmark --verifier

audit:
	cd $(P) && $(PY) -m pip_audit -r constraints.txt --progress-spinner off

coverage:
	cd $(P) && $(PY) -m coverage run --source=app,intelligence,plateforme,adaptateurs -m pytest -q && $(PY) -m coverage report --skip-covered

# obligatoire avant tout tag de démonstration (demo-*) ; aussi en CI : nuit, à la demande, et quand le registre change
# Jamais sur la machine de démonstration pendant le hackathon (TODO-DEMO.md) : nuit, CI, avant un tag demo-*.
mutation:
	cd $(P) && $(PY) scripts/mutation_capacites.py

# Démonstration DURABLE (F29) : journal de Club Pulse dans un FICHIER, secret STABLE tiré une fois et gardé hors dépôt
# (prototype/var/ est ignoré par git). Un kill -9 puis `make demo` : même monde, mêmes sessions, même passe juré, rejeu
# IA sans rappeler le modèle. Nouvelle démonstration : bouton de la régie (le journal est vidé, le secret reste).
# Téléphones réels (R-01) : HOTE=0.0.0.0 pour écouter le point d'accès, URL_PUBLIQUE pour que le QR juré et les liens
# pointent vers le portable (sinon ils encodent 127.0.0.1, que le téléphone prend pour lui-même).
demo:
	cd $(P) && mkdir -p var && (test -s var/secret_demo || $(PY) -c "import secrets; print(secrets.token_urlsafe(48))" > var/secret_demo) \
	  && chmod 600 var/secret_demo && HACKVS_SECRET="$$(cat var/secret_demo)" HACKVS_ESSAIS_DB=var/club_pulse.db \
	  HACKVS_MODE=demo HACKVS_DB=:memory: HACKVS_DECISIONS_DB=:memory: HACKVS_CYCLE_DB=:memory: \
	  HACKVS_URL_PUBLIQUE="$(URL_PUBLIQUE)" $(PY) -m uvicorn app.main:app --host $(HOTE) --port 8000 --no-access-log

quality-check: secrets lint typecheck test e2e eval
	@echo "quality-check : tout est vert"

# Mesures de performance reproductibles (vrai serveur, n itérations, moyenne / médiane / p95) : docs/audit/FINAL_AUDIT.md § 8
perf:
	cd $(P) && $(PY) scripts/mesurer_perf.py
