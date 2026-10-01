# Banc multi-fournisseurs — Apertus, OpenAI, Claude sur les mêmes 26 cas

Outil d'ingénierie, pas une fonctionnalité : il compare des modèles sur LA tâche IA du produit (`comprendre_action`,
« Agir à plusieurs → Comprendre ma demande »), par le chemin du produit, avec la MÊME validation.

## Choisir le fournisseur (produit et banc)

| `LLM_PROVIDER` | Effet |
|---|---|
| *(absent)* | comportement d'origine : Apertus si `APERTUS_*` est configuré, sinon forme déterministe |
| `apertus` · `openai` · `claude` | ce fournisseur s'il est configuré ; sinon forme déterministe (jamais un autre à sa place) |
| `deterministe` · `aucun` | aucun modèle |
| autre valeur | erreur explicite au démarrage |

| Fournisseur | Variables obligatoires | Facultatives |
|---|---|---|
| Apertus | `APERTUS_API_KEY`, `APERTUS_BASE_URL`, `APERTUS_MODEL` | `APERTUS_DELAI_S`, `APERTUS_BUDGET_S` |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` | `OPENAI_BASE_URL` (défaut `https://api.openai.com/v1`), `OPENAI_TEMPERATURE` (défaut 0 ; `defaut` = ne pas l'envoyer), `OPENAI_DELAI_S`, `OPENAI_BUDGET_S` |
| Claude (API Messages) | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | `HACKVS_ANTHROPIC_BASE_URL` (défaut `https://api.anthropic.com` ; `ANTHROPIC_BASE_URL` est volontairement ignorée), `ANTHROPIC_TEMPERATURE`, `ANTHROPIC_DELAI_S`, `ANTHROPIC_BUDGET_S` |

Le code n'impose aucun nom de modèle : `OPENAI_MODEL` et `ANTHROPIC_MODEL` sont choisis le jour du banc et figurent
dans chaque rapport. Claude est appelé par son API (le modèle), pas par l'agent Claude Code.

## Ce que chaque fournisseur reçoit — identique

Mêmes 26 cas (`prototype/eval/cas_comprendre_action.json`, SHA-256 `34bfcc37bf2f8e2f…`), même date simulée, même
prompt versionné (`comprendre_action_v1`) et même consigne de schéma dans le message système, même message utilisateur
(catalogue des capacités compris), température 0, 900 jetons au plus, même budget (12 s), même schéma de sortie, même
validation du produit, même repli. Seul diffère le FORMAT de l'API (`intelligence/ia.py`) : sortie contrainte par
`response_format` json_schema strict (Apertus, OpenAI) ou par un outil imposé dont `input_schema` est ce schéma (Claude).
Si un serveur refuse la contrainte, la consigne seule reste — et le rapport le compte (« contrainte serveur refusée »).

## Commandes (depuis la racine du dépôt)

```bash
make banc-ia-dry-run                       # ce soir : fournisseurs FACTICES, AUCUN réseau → prototype/var/banc_dry_run/
make banc-ia FOURNISSEUR=apertus           # APERTUS_* requis   → prototype/eval/resultats_banc/apertus.md (+ .json)
make banc-ia FOURNISSEUR=openai            # OPENAI_* requis    → prototype/eval/resultats_banc/openai.md (+ .json)
make banc-ia FOURNISSEUR=claude            # ANTHROPIC_* requis → prototype/eval/resultats_banc/claude.md (+ .json)
make banc-ia-comparer                      # → prototype/eval/resultats_banc/comparaison.md
```

Sans les variables du fournisseur demandé : « NON EXÉCUTÉ », rien n'est appelé, rien n'est écrit (code 2). La
comparaison refuse des résultats obtenus sur des cas ou un prompt différents. Le résultat Apertus du 01.10
(`prototype/eval/resultats_comprendre_action.md`) est une preuve datée : il n'est jamais réécrit.

## Le rapport

Par fournisseur : acceptées / rejetées / indisponibles, JSON lisible, conforme au schéma, validation métier,
acceptées et justes, **acceptées mais fausses** (hallucination métier qui passe la validation), replis, contrainte
serveur refusée, latence p50 / p95. Par cas : l'attendu, puis pour chaque fournisseur « ✓ juste », « accepté FAUX :
raison », « rejeté : raison » ou « indisponible », et les latences. Sorties brutes dans le `.json`. Aucun score
composé, aucun classement : chaque question se lit sur sa colonne.

## Ne jamais exposer une clé

- Clés dans l'environnement seulement (réglages de l'environnement, Secret Manager) ; jamais dans le dépôt, une
  commande tapée en clair, un fichier `.env` suivi, ni `--set-env-vars`.
- Le serveur seul les lit ; le navigateur ne les voit jamais (vérifié : aucune dans `prototype/web/`).
- Les erreurs des fournisseurs ne gardent que « HTTP 403 », « ReadTimeout »… — jamais le corps de la réponse ni un
  en-tête ; `repr()` n'affiche ni clé ni en-tête ; le banc refuse d'écrire un rapport qui contiendrait une clé (code 3).
- Tests : `tests/test_fournisseurs_ia.py` (aucune clé dans journaux, erreurs, traces, sorties), `tests/test_banc_comprendre_action.py`
  (aucune clé dans un rapport), `make secrets` (aucune clé dans le dépôt). La suite de tests retire toute variable
  `APERTUS_*`, `OPENAI_*`, `ANTHROPIC_*`, `LLM_PROVIDER` de la machine : elle n'appelle jamais un vrai fournisseur.

## Limites connues du banc de référence (documentées, NON corrigées — une correction = une nouvelle version)

1. **Plafond 21/26 pour tout modèle.** c13 à c17 attendent une abstention (aucune exigence + une question) ; le schéma
   du produit impose au moins une exigence et le validateur 1 à 4 : aucun modèle ne peut y être juste. Le factice
   « valide » plafonne à 20/26 (il choisit aussi l'abstention pour c19, où « public » était accepté).
2. **Une exécution par fournisseur.** Les sorties varient d'un appel à l'autre, même à température 0 (Apertus,
   01.10 : c08 juste au banc, faux dans le conteneur une heure plus tard). Un écart de 1–2 cas n'est pas significatif.
3. **Notation stricte des rôles** : l'ensemble exact (une exigence de plus est une erreur) ; seuls c05, c06, c07, c09,
   c19, c21 et c22 admettent deux réponses.
4. **Contrainte de sortie non identique** d'une API à l'autre (json_schema strict vs outil imposé) : inévitable, et
   compté. La température 0 peut être refusée par certains modèles (`*_TEMPERATURE=defaut`, dit dans le rapport).
5. **Latence** mesurée depuis l'environnement de développement (proxy sortant), séquentiellement : elle dépend du
   chemin réseau et de la charge du fournisseur ; elle ne dit rien de Cloud Run ni de la salle.
6. **Petit et mono-tâche** : 26 cas fictifs, une tâche ; le prompt v1 a été écrit avant tout appel réel, pour ce produit.

## Avant d'utiliser OpenAI ou Claude DANS le produit (pas dans le banc) — non fait, volontairement

Trois libellés de l'interface ne connaissent qu'Apertus : `web/pulse/app.html` (« Préparé / Compris par Apertus »,
testés sur `fournisseur === "apertus"`) et la console (« Apertus configuré »). Avec `LLM_PROVIDER=openai|claude`, une
sortie acceptée s'afficherait « Règles simples, aucun modèle utilisé » — faux. C'est un changement de texte UX, exclu
de cette tâche : à décider et corriger AVANT tout usage produit de ces fournisseurs. Le banc n'est pas concerné.
