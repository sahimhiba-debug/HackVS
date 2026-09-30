# Évaluation du rôle EXTRACT (option 1 : le rôle tel qu'il existe)

> État au 2026-09-30 : **protocole prêt, AUCUNE passe exécutée**. L'API Public AI n'est pas joignable depuis cet
> environnement (politique réseau : `api.publicai.co` refusé, 403) et `APERTUS_API_KEY` n'y est pas posée. Aucun
> chiffre ci-dessous n'est inventé : les résultats s'écriront dans `extraction_dev.md` et `extraction_test.md` (et
> leurs fichiers `_brut.json`) quand l'API sera disponible.

## Protocole (tout est committé AVANT le moindre appel au modèle)

| Élément | Où | Preuve |
|---|---|---|
| Corpus + étiquettes-or, conventions et mesures | `prototype/eval/corpus_extraction/` | commit `61de546` (2026-09-30 19:27 UTC), `corpus.json` sha256 `5069a8d4…926937b`, committé SEUL |
| Banc, correspondance sortie → prédiction, garde-fous | `prototype/eval/eval_extraction.py` | commits `2434e51`, `9eda727` |
| Rôle, prompt, schéma, moteur | `intelligence/roles_ia.py`, `prompts/extraire_piece_v1.md` | NON modifiés (option 1) ; empreintes gelées par `--geler` après DEV |

Déroulé : (1) DEV (20 énoncés) avec le vrai modèle, pour vérifier le protocole — sans toucher au corpus ; (2) `--geler`
(empreintes du corpus, du prompt et du rôle) ; (3) TEST (30 énoncés), **une seule passe** — le banc la refuse sans
gel, après toute modification, ou si elle a déjà eu lieu ; résultats publiés tels quels, même mauvais.

## Ce que l'IA démontrerait — et seulement cela

Le rôle EXTRACT ne produit qu'une chose : les **quantités** (`attributs`, ici `places`) d'UNE pièce déjà désignée par
une demande, chaque valeur devant être écrite dans le texte du membre. La passe mesurera donc, pour l'IA :
la capacité à relever une quantité juste (précision / rappel), à ne rien extraire d'une injection ou d'un hors-sujet,
à rester sous le validateur (taux de sorties rejetées), le taux de repli, la latence — par langue (FR / DE / GSW).
Tant que la passe n'a pas eu lieu, l'IA **ne démontre rien** sur ce corpus.

## Ce que le moteur déterministe garantit, indépendamment de l'IA (F, tests en CI)

- Une sortie du modèle n'est qu'une **proposition** : rien n'est déclaré ni consenti sans la confirmation du membre
  (`test_roles_ia.py`, `test_canaris_prompts.py`).
- Toute valeur absente du texte, tout champ non demandé (consentement, statut, membre…) fait **rejeter** la sortie ;
  un seul nouvel essai ; sinon le formulaire (FALLBACK_FORM), toujours dit.
- Aucune identité du coffre dans les prompts (canari sur 150 membres, deux défenses indépendantes, contre-épreuve).
- Injections FR / DE / suisse allemand : l'état du Club ne bouge pas.
- **Parité ON / OFF non vacueuse** : IA allumée ou éteinte, même état métier (`test_parite_ia.py`, modèle scripté).
- Composition, statuts, consentements, retraits : calculés par le moteur, jamais par le modèle.

## Ce que le rôle EXTRACT ne couvre pas (schéma actuel) — rappel 0 %, jamais un succès implicite

| Champ de l'or | Pourquoi |
|---|---|
| type (lieu / objet / compétence), pièce (slot) | le rôle reçoit la pièce de la demande ; il ne l'identifie pas |
| créneau (jour, début, fin) | non produit ; le créneau vient de la demande |
| offre / retrait | non produit ; un retrait passe par le geste « Retirer mon consentement » |
| plusieurs pièces dans une phrase | une seule pièce par appel |
| RIEN vs FALLBACK | le rôle rend des attributs vides dans les deux cas (le produit montre le formulaire vide) |

Conséquence mesurée d'avance : les énoncés EXTRACTION de l'or **sans quantité** (compétence, retrait, lieu sans taille ;
5 en DEV) ne peuvent pas être extraits par ce rôle — limite du schéma, pas du modèle ; aucun énoncé EXTRACTION ne peut
être « exact » (champs non couverts).

## Findings / Next research

- Le corpus rend visible l'écart entre ce que disent les membres (plusieurs pièces, créneaux relatifs, retraits) et
  ce que le rôle actuel sait proposer (une quantité pour une pièce déjà demandée).
- **Piste d'évolution, NON implémentée** : élargir EXTRACT à plusieurs *claims typées* (type, pièce, quantité, créneau,
  offre/retrait), toujours validées par le code et présentées comme propositions au membre. À n'entreprendre qu'après la
  démo, avec un nouveau corpus TEST (celui-ci aura servi) et le même protocole (or committé seul, une passe).
- La distinction RIEN / FALLBACK (injection vs énoncé ambigu) serait à mesurer avec un signal explicite du modèle,
  lui aussi validé.
