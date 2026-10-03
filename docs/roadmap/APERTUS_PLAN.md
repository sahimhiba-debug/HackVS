# Plan Apertus — rendre l'IA suisse utile aux demandes du Club

## État mesuré (01.10.2026)

- Sur la tâche « comprendre une demande » (extraction structurée), **Apertus-v1.5-70B** (API CSCS) donne une sortie
  **acceptée et juste dans 1 cas sur 26** ; 25 sorties sont rejetées par la validation du code (durées hors bornes,
  capacités hors catalogue, jours non ISO). Ce que voit le membre est juste dans 17/26 cas, contre 16/26 pour les
  règles seules. Source : `prototype/eval/resultats_comprendre_action.md` (CLAIMS n° 39, classe B).
- Latence : médiane 5,3 s, p95 6,0 s (n = 30). La démonstration de scène tourne **sans modèle**.
- Ce résultat ne dit rien d'une qualité générale d'Apertus : il dit que **le prompt actuel** ne suffit pas pour cette tâche.

## Stratégie

1. **Jeu de test humain figé** : les phrases recueillies par le QR de la Foire (formulaire Tally). Règles, fixées
   avant toute mesure :
   - la **langue réelle** de chaque phrase est détectée (pas la page choisie : une réponse anglaise est passée par la
     page française) ;
   - une colonne **domaine = club | hors_club**, remplie par une personne dans la feuille d'annotation ; les phrases
     hors_club restent dans le jeu comme **tests d'abstention** (« ce n'est pas une demande pour le Club ») ;
   - **consentement** : le formulaire promet « votre phrase sert seulement à tester une IA suisse » — ces phrases ne
     passent **que par Apertus**, jamais par un modèle frontière du banc (la comparaison frontière reste sur les 26 cas
     et le synthétique) ;
   - **jamais utilisées pour entraîner** ; **aucune phrase individuelle** dans le pitch, les slides ou la documentation
     publique : des agrégats seulement (nombre, langues, part de demandes implicites ou vagues).
2. **Données d'entraînement synthétiques « réponse d'abord »** : on fixe la sortie attendue (capacité, rôle, date,
   bornes), puis Apertus 70B rédige des demandes FR / DE / CH-DE qui y mènent ; filtrage par le validateur du code.
3. **Décodage contraint** : la sortie suit le schéma (JSON, vocabulaire fermé de la taxonomie), l'abstention est une
   sortie valide.
4. **Fine-tuning LoRA** d'Apertus 8B (ou d'un modèle plus petit de la famille) sur quelques milliers d'exemples FR / DE.
5. **Service en Suisse** (hébergement suisse, nLPD) ; **parité IA allumée / éteinte garantie** (testée en CI :
   `test_parite_ia.py`) — l'état métier ne dépend jamais du modèle.
6. **Le produit fabrique ses propres annotations** : quand un membre corrige ce que l'IA a compris, la correction
   devient un exemple étiqueté — **avec son consentement explicite**, séparé du consentement d'usage.

## Objectifs

Des objectifs chiffrés (exactitude, taux d'abstention juste) seront fixés **après** l'annotation humaine du jeu figé
et **mesurés avant d'être affichés**. Aucun chiffre n'est revendiqué aujourd'hui au-delà du 1/26 mesuré.
