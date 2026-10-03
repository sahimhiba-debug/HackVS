# Note d'architecture (une page) — reçus swiyu, demandes vocales, extraction sur le téléphone

**Statut : PRÉVU** (`etat.yaml` : `swiyu`, `voix`, `mini`). Rien de ceci n'est construit ; chaque point se mesure avant
d'être affiché. Rien ne change le principe : le reçu est la preuve du consentement, l'IA propose, le membre décide.

## 1. Reçus en attestations vérifiables dans le portefeuille swiyu

- **Contexte** : l'e-ID suisse (application swiyu) est prévue dès le **1er décembre 2026** (date du cadrage, à
  confirmer à l'approche). Le portefeuille sait détenir des attestations vérifiables émises par des tiers.
- **Proposition** : le Club devient **émetteur** ; chaque reçu de consentement (référence, finalité, date, état) est
  émis comme attestation dans le portefeuille du membre, **en plus** du reçu de l'application. Retirer son
  consentement = **révoquer** l'attestation (liste de révocation), jamais l'effacer du portefeuille du membre.
- **Ce qui ne bouge pas** : le journal du Club reste la source ; l'attestation ne contient ni le nom d'une autre
  personne, ni l'offre détaillée — seulement la finalité et l'état. Divulgation sélective : le membre ne montre que ce
  qu'il veut.
- **À vérifier** : protocole d'émission retenu par la Confédération (format, registre de confiance, conditions pour un
  émetteur associatif), coût, et l'avis du juriste (jalon « Lancer »).

## 2. Demandes vocales via l'entrée audio d'Apertus 1.5

- **Hypothèse** : Apertus 1.5 accepte une entrée audio (**expérimentale** selon le cadrage). Un membre dit sa demande
  au lieu de l'écrire ; la sortie suit EXACTEMENT le chemin du texte (schéma, validation par le code, abstention,
  repli déterministe, confirmation du membre).
- **Mesure d'abord** : un jeu de demandes **lues en français et en dialecte** (Valais romand, Haut-Valais), figé avant
  toute exécution, jugé comme les 26 cas ; aucun chiffre affiché avant la mesure. Consentement explicite pour tout
  enregistrement ; **l'audio n'est jamais conservé** (comme la photo de la carte).
- **Risque** : qualité inégale selon les accents ; la parade est le formulaire, toujours là.

## 3. Extraction sur le téléphone avec Apertus Mini

- **Idée** : un petit modèle de la famille Apertus, exécuté **sur le téléphone**, propose la structure d'une demande
  sans que le texte quitte l'appareil ; le serveur ne reçoit que ce que le membre confirme.
- **Conditions** : taille et licence du modèle compatibles avec un téléphone, exécution dans le navigateur ou une
  application ; mesure sur le même jeu humain figé que le modèle serveur (`APERTUS_PLAN.md`) ; parité garantie — sans
  modèle local, le parcours reste identique.
- **Gain attendu** (à mesurer) : confidentialité (rien ne sort avant confirmation) et latence.
