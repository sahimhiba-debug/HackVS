# Réseau vivant (anciennement « Le Fil du Club ») : préparation Hack VS 2026

> **Prototype préparé AVANT Hack VS** (Martigny, 3–4 octobre 2026), pour le challenge « construire une plateforme de
> networking qui active le réseau du Club des Affaires toute l'année ». Le brief officiel complet n'est pas encore connu.
> **Toutes les personnes et entreprises sont fictives.** Aucun message réel n'est envoyé.

**Le problème.** La Foire crée des rencontres. Quand elle se termine, ces relations peuvent disparaître avec elle.

**Ce que fait le produit.** Un membre écrit son besoin comme il le dirait ; le système lui propose seulement les membres
dont le profil **prouve** qu'ils peuvent aider (avec l'extrait qui le justifie), organise l'introduction **avec l'accord
des deux**, relance **seulement** quand une raison nouvelle existe, et montre à l'organisatrice ce que ses introductions
changeraient au réseau entier. Quand rien n'est prouvé, il **s'abstient** — et dit pourquoi.

**Où est l'IA.** Pas dans la démonstration : la phrase du besoin est comprise par des règles vérifiables (chaque
critère cite le texte ; l'ambigu est demandé, pas deviné). Une IA générative (Claude ou Apertus) peut s'y brancher pour
les phrases très libres, **sous contrôle du code, sans jamais décider** ; elle n'a pas encore été mesurée (aucun modèle
accessible ici) : [GENAI_RESEARCH](competition/GENAI_RESEARCH.md).

**Voir en 3 minutes** : `/demo/stage` (l'histoire en 11 étapes, touche T : tour de contrôle) · `/presentation` (deck) ·
vidéo de secours [`competition/video/demo.webm`](competition/video/demo.webm) · dossier : [`competition/`](competition/README.md).

## Ce qui fonctionne (vérifié)
| | Détail | Preuve |
|---|---|---|
| Histoire de démonstration | nouveau membre → besoin → candidats → accord → rencontre → suivi → opportunité → réseau avant/après → abstention → soirées → bilan ; rejouable à l'identique | `tests/test_scene.py`, `tests/test_e2e_scene.py` (vrai navigateur, bureau + mobile, en CI) |
| Compréhension du besoin | règles + taxonomie ; phrase du scénario et variantes comprises ; ambiguïtés explicites | `tests/test_compilateur_besoin.py` ; 112 cas écrits avant exécution |
| Preuve et abstention | chaque proposition cite une preuve ; sans preuve, abstention motivée | registre des preuves C01, C23, C24 |
| Consentement | invisible par défaut, double accord, refus jamais contourné (règle unique, vérifiée sur toutes les paires) | `test_scene.py`, `test_securite_api.py`, `test_adversarial_sprint.py` |
| Réseau | diagnostic (8 phénomènes), front de plans en conflit, contrefactuel « si cette relation disparaît », tour de contrôle | `competition/06_BENCHMARKS.md` (SYNTHETIC_BENCHMARK) |
| Ingénierie | suite pytest complète, lint, CI (qualité, bout en bout, reproductibilité des benchmarks à l'octet), registre des affirmations exécutable | `.github/workflows/ci.yml`, `competition/14_PROOF_LEDGER.md` |

**Simulé / fictif** : tous les profils, rencontres et besoins ; toutes les projections du réseau (étiquetées
SIMULATION). **Non vérifié** : Claude et Apertus contre leurs API réelles ; utilité auprès de vrais membres. Voir
[16_LIMITATIONS](competition/16_LIMITATIONS.md) et [FAILURES](competition/FAILURES.md) (48 défauts trouvés en attaquant notre propre système).

## Lancer
```bash
cd prototype
pip install -r requirements.txt            # + requirements-dev.txt pour tests et captures
python scripts/telecharger_modele.py       # facultatif : IA locale (2,2 Go, sans clé)
uvicorn app.main:app                       # http://localhost:8000
```
Pages : `/demo/stage` démonstration · `/` espace membre · `/decision` espace de décision · `/cycle` cycle des relations · `/soiree` plan de soirée · `/club` vue du Club · `/scene` deux membres en direct ·
`/presentation` pitch hors ligne. Docker : `docker build -t fil-du-club . && docker run -p 8080:8080 fil-du-club`.

Brancher un assistant IA : `claude mcp add fil-du-club -e HACKVS_API_URL=http://localhost:8000 -e HACKVS_MCP_MEMBRE=p00 -- python <chemin>/prototype/scripts/mcp_club.py` (détails : [HANDOFF.md](docs/HANDOFF.md)).

| Variable | Effet |
|---|---|
| `HACKVS_MODE=demo` (défaut) / `reel` | `reel` : uniquement `HACKVS_PROFILS=<fichier autorisé>` ; sinon 503/501, jamais de simulation |
| `HACKVS_LLM=claude` + `ANTHROPIC_API_KEY` | Analyse par Claude en flux, validée par le code ; repli affiché sur les règles |
| `HACKVS_LLM=apertus` + `APERTUS_API_KEY`, `APERTUS_BASE_URL`, `APERTUS_MODEL` | Même chose avec Apertus (API compatible OpenAI) |
| `HACKVS_SEMANTIQUE=0` | Désactive l'IA locale |

## Vérifier
```bash
python -m pytest -q                        # suite complète (dont MCP stdio/HTTP et navigateur réel si Chromium est présent)
python -m eval.eval_decisions              # 20 scénarios de la plateforme de décision
python -m eval.run_eval --verifier         # non-régression des 6 jeux
python scripts/validate_competition_claims.py   # chaque chiffre du pitch, du deck et de la vidéo est-il prouvé ?
python scripts/mesurer_scene.py            # lisibilité de la démo dans un vrai navigateur
python scripts/parcours_demo.py --url http://localhost:8000   # navigateur réel → docs/captures/
python scripts/demo_agent_mcp.py           # transcription de l'agent MCP
```

## Documentation
[ARCHITECTURE](docs/ARCHITECTURE.md) · [DEMO](docs/DEMO.md) (scénarios 60 s / 3 min / 5 min, objections) ·
[EVALUATION](docs/EVALUATION.md) · [LIMITATIONS](docs/LIMITATIONS.md) · [DECISIONS](docs/DECISIONS.md) ·
[OPEN_SOURCE_RECON](docs/OPEN_SOURCE_RECON.md) · [RESEARCH](docs/RESEARCH.md) · [ASSUMPTIONS](docs/ASSUMPTIONS.md) ·
[HANDOFF](docs/HANDOFF.md) · [DEPLOIEMENT](docs/DEPLOIEMENT.md) · [AUDIT_PACKET](docs/AUDIT_PACKET.md) · [REPRISE](docs/REPRISE.md) · [LEARNING](docs/LEARNING.md)
