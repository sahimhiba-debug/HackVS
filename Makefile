# Club Pulse — commandes du dépôt. Chaque cible échoue (code ≠ 0) au premier contrôle en échec.
#   make setup          dépendances (exécution + facultatives + outils), versions exactes de constraints.txt
#   make quality-check  TOUT : secrets, lint, types, tests, bout en bout, évaluations, cohérence du pitch
#   make demo           serveur de démonstration : http://127.0.0.1:8000/console et /app
PY ?= python
P = prototype
export HACKVS_SEMANTIQUE ?= 0

.PHONY: setup browsers lint typecheck test e2e e2e-salle sonde-ia eval secrets audit coverage demo quality-check mutation

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

E2E = tests/test_e2e_scene.py tests/test_e2e_pulse.py tests/test_e2e_action.py tests/test_e2e_capacites.py tests/test_e2e_hermetique.py

test:
	cd $(P) && $(PY) -m pytest -q $(addprefix --ignore=,$(E2E))

e2e:
	cd $(P) && HACKVS_E2E_OBLIGATOIRE=1 $(PY) -m pytest -q tests/test_e2e_scene.py tests/test_e2e_pulse.py tests/test_e2e_action.py tests/test_e2e_capacites.py tests/test_e2e_hermetique.py

# Mode salle : les mêmes E2E, réseau LOCAL seul (espace réseau vide, extérieur injoignable vérifié) et IA OFF
e2e-salle:
	cd $(P) && sudo -E env "PATH=$$PATH" HACKVS_E2E_OBLIGATOIRE=1 unshare --net $(PY) scripts/mode_salle.py -- \
	  $(PY) -m pytest -q tests/test_e2e_scene.py tests/test_e2e_pulse.py tests/test_e2e_action.py tests/test_e2e_capacites.py tests/test_e2e_hermetique.py

# Sonde du fournisseur de langage (clé en variable d'environnement APERTUS_API_KEY ; sans clé : UNKNOWN, dit)
sonde-ia:
	cd $(P) && $(PY) scripts/sonde_publicai.py

eval:
	cd $(P) && $(PY) -m eval.run_eval --verifier && $(PY) -m eval.eval_decisions --verifier \
	  && $(PY) scripts/validate_competition_claims.py --sans-benchmark --verifier

audit:
	cd $(P) && $(PY) -m pip_audit -r constraints.txt --progress-spinner off

coverage:
	cd $(P) && $(PY) -m coverage run --source=app,intelligence,plateforme,adaptateurs -m pytest -q && $(PY) -m coverage report --skip-covered | tail -25

# obligatoire avant tout tag de démonstration (demo-*) ; aussi en CI : nuit, à la demande, et quand le registre change
mutation:
	cd $(P) && $(PY) scripts/mutation_capacites.py

demo:
	cd $(P) && HACKVS_MODE=demo HACKVS_DB=:memory: HACKVS_DECISIONS_DB=:memory: HACKVS_CYCLE_DB=:memory: \
	  $(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log

quality-check: secrets lint typecheck test e2e eval
	@echo "quality-check : tout est vert"
