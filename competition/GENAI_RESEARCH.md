# IA générative : où multiplie-t-elle la valeur du moteur ? — pré-inscription

Écrit AVANT toute exécution d'un modèle. État de l'environnement au moment de l'écriture : **aucun modèle génératif
disponible** (aucune clé d'API configurée ; téléchargement de modèles locaux bloqué par le réseau). Aucun chiffre d'IA
n'existe donc encore ; le bras « moteur seul » est exécuté, les bras IA sont prêts et NON EXÉCUTÉS.

## Principe
Le moteur déterministe sait : filtrer, prouver, optimiser, projeter, se taire. Il ne sait PAS : comprendre une phrase qu'il
n'a jamais vue, résumer pour un humain, formuler une hypothèse. Une IA générative n'a sa place que là où elle apporte
l'un de ces trois gestes, et seulement si un contrôle déterministe peut vérifier sa sortie.

## Carte des points d'insertion (test des 4 jours)

| # | Point | Ce que le moteur rate (mesuré) | Geste IA | Contrôle déterministe | Verdict initial |
|---|---|---|---|---|---|
| G1 | Comprendre un besoin en langue libre | 22 échecs / 112 cas, surtout paraphrases et allemand / anglais libres (BENCHMARK_MEMO §4) | compréhension | vocabulaire fermé, extraits cités présents dans le texte, repli sur règles | **BENCHMARK** (3 bras + repli) |
| G2 | Synthèse du diagnostic pour l'organisation | le diagnostic est un JSON de ~7 ko : juste mais illisible | synthèse | chaque nombre et chaque identifiant cité doit exister dans les faits fournis | **BENCHMARK** (fidélité, couverture) |
| G3 | Hypothèses explicatives (« pourquoi ce groupe est-il isolé ? ») | le moteur constate, il n'explique pas | hypothèse | étiquetage HYPOTHÈSE obligatoire, faits cités vérifiés | PROTOTYPE après G2 |
| G4 | Profil depuis un texte libre (adhésion) | règles : vocabulaire fermé | compréhension | même validation que G1 | DEFER (pas de jeu étiqueté) |
| G5 | Rédaction du message d'introduction | gabarit correct mais impersonnel | style | aucune donnée privée ajoutée | DEFER (évaluation humaine requise) |
| — | Choisir QUI rencontrer / décider | — | — | — | **REJET** : décision et consentement restent déterministes (testés) |

## G1 — Comprendre le besoin : moteur seul contre IA seule contre hybride
- **Jeux.** Les 6 jeux existants (112 cas, attendus écrits avant exécution). Aucun n'a servi à régler un modèle : tous sont
  « frais » pour un LLM.
- **Bras.**
  1. MOTEUR : analyse par règles + moteur de recherche (exécuté).
  2. IA SEULE : le LLM reçoit le besoin ET les profils publics FICTIFS, et choisit directement jusqu'à 3 membres (ou
     s'abstient). Bras d'évaluation seulement : dans le produit, le LLM ne voit jamais les profils (règle testée).
  3. HYBRIDE : le LLM traduit le besoin en critères du vocabulaire fermé (validés) ; le moteur cherche et décide.
  4. HYBRIDE EN REPLI : règles d'abord ; le LLM n'est appelé que si les règles ne reconnaissent aucune compétence ou
     signalent une ambiguïté (coût réduit).
- **Métriques.** succès@3, violations de contraintes (profil interdit, visiteur, refus d'introduction), abstention
  correcte, identifiants INVENTÉS, appels au modèle, latence ; par catégorie.
- **Critères fixés d'avance.** L'hybride est retenu s'il récupère au moins la moitié des échecs du moteur SANS ajouter
  de violation. On s'attend à ce que l'IA seule ait un succès@3 comparable mais des violations et des inventions : si ce
  n'est pas le cas, on le publiera.

## G2 — Synthèse du diagnostic
- **Entrée.** Le diagnostic d'organisation (faits structurés) sur des réseaux générés.
- **Bras.** GABARIT (texte produit par du code, exécuté) ; IA SEULE (le LLM reçoit les faits bruts — relations datées —
  et écrit le diagnostic lui-même) ; HYBRIDE (le LLM reçoit NOTRE diagnostic structuré et le met en mots).
- **Métriques automatiques.** Fidélité : part des nombres et identifiants cités qui existent dans les faits fournis ;
  couverture : part des phénomènes détectés qui sont mentionnés ; inventions : entités absentes des faits.
- **Critère.** L'hybride n'est retenu que s'il est 100 % fidèle après contrôle ; la lisibilité demande un jugement humain
  (non automatisable : dit).

## Ce qu'il faut pour exécuter
Une clé fournie par l'ENVIRONNEMENT (jamais dans le chat) : variable `ANTHROPIC_API_KEY`, ou `HACKVS_LLM=apertus` et les
variables Apertus. Puis : `python -m eval.benchmark_ia` et `python -m eval.benchmark_synthese`.

## Exécuté à ce jour (sans modèle génératif)
**G1, bras MOTEUR (112 cas).** succès@3 66/86 ; violations 3/112 ; abstention correcte 92/112 ; 0 invention ; 2,5 ms.
**Pré-analyse du routage (sans modèle).** Le repli n'appellerait le modèle que sur **37/112** cas, qui contiennent
**19 des 22** échecs du moteur. Les 3 échecs hors de portée du repli sont exactement les **3 violations** (règles
confiantes mais fausses : deux paraphrases, un faux ami). Question que seule la mesure réelle tranchera : l'hybride
complet (112 appels) vaut-il ces 3 cas de plus, au triple du coût ?
**G2, bras GABARIT (5 réseaux).** Fidèle 5/5 (après correction d'un FAUX POSITIF du vérificateur : une longueur de liste
était prise pour une invention) ; couverture 80 % ; 231 mots — et **illisible** (listes brutes) : c'est précisément là
qu'une IA générative peut apporter de la valeur.
**Vérificateur de fidélité (produit).** Attaqué : un nombre en lettres et une affirmation fausse SANS nombre (« aucun
membre n'est isolé ») passaient → deux règles ajoutées (quantités en chiffres ; négation d'un phénomène détecté). Limite
déclarée : il contrôle des faits et des négations simples, pas toutes les contradictions de sens.
**Mécanique des bancs** vérifiée avec un double de test (aucun chiffre publié).

## Pour exécuter les bras IA
Configurer dans l'environnement (jamais dans le chat) SOIT `ANTHROPIC_API_KEY` et `HACKVS_LLM=claude`, SOIT
`HACKVS_LLM=apertus`, `APERTUS_API_KEY`, `APERTUS_BASE_URL`, `APERTUS_MODEL` (Apertus : les quatre bras de G1 et les
trois bras de G2 passent par son API compatible OpenAI ; l'hôte doit être autorisé par la politique réseau de
l'environnement — refusé au 29.09 : `api.publicai.co`, `api.swisscom.com`). Le rapport indique le modèle utilisé ; les
résultats d'Apertus et de Claude sont des lignes distinctes, jamais fusionnées. Puis :
`python -m eval.benchmark_ia --sortie eval/resultats_benchmark_ia.md` et
`python -m eval.benchmark_synthese --sortie eval/resultats_benchmark_synthese.md`. Coût estimé : ~112 + 37 + 112 appels
pour G1, 10 appels pour G2.
