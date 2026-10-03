# 07 — Questions difficiles du jury, réponses courtes

Trois phrases au plus, prononçables, honnêtes. Chaque réponse distingue **aujourd'hui** (prouvé dans le dépôt) et
**prévu ensuite**. Les références entre parenthèses sont pour nous, pas pour l'oral. Source : `docs/audit/CLAIMS.md`,
`FINAL_AUDIT.md`, `THREAT_MODEL.md`, `DEMO_SCRIPT.md`.

## Produit et concept

**Pourquoi pas LinkedIn ?**
LinkedIn met en relation ; il ne sait pas ce que le Club peut faire ensemble vendredi à 14 h. Club Pulse ne cherche pas
des contacts : il assemble des pièces déclarées, datées, consenties, pour une capacité précise. Et quand une pièce
disparaît, il le dit — LinkedIn ne le saura jamais.

**Pourquoi pas un matching classique ?**
Un matching répond « qui ressemble à qui ». Nous répondons « qu'est-ce que le Club peut faire, aujourd'hui, avec ce que
ses membres ont réellement déclaré » — et il manque quoi. Ce n'est pas une suggestion, c'est un état, recalculé à
chaque changement.

**Pourquoi un « essai » plutôt qu'une mise en relation ?**
Parce qu'une mise en relation finit par « on s'appelle ». Un essai a une date, des pièces, des gens qui ont dit oui
chacun sur leur téléphone, et un résultat qu'on constate — ou qu'on déclare inconnu. On n'affiche jamais plus que ce
qui est prouvé : « fiche reçue » n'est pas « présentation tenue ».

**Qu'est-ce qui marche aujourd'hui, et qu'est-ce qui est prévu ?**
Aujourd'hui : le registre des capacités, la demande minimale, les trois boutons, le reçu, le retrait anonyme, la
recomposition, l'action collective avec créneau commun et adaptation, le journal rejouable — tout ça testé, dans un
monde fictif. Prévu ensuite : de vrais membres, l'authentification du Club, une IA meilleure sur nos tâches, un
déploiement public durable. Aucun utilisateur réel n'a utilisé le produit : on ne prétend pas le contraire.

**Comment passer du prototype à la plateforme du Club ?**
Trois chantiers, dans cet ordre : brancher l'annuaire et l'authentification du Club (aujourd'hui, des codes
d'invitation de démonstration) ; un essai réel avec cinq membres volontaires et cinq vraies demandes ; puis l'hébergement
durable, qui est préparé (une image, une procédure Cloud Run, rien de déployé). Le cœur — règles, journal, consentement —
ne change pas.

**Que se passe-t-il si un membre refuse ?**
Rien ne lui est reproché, et rien ne lui est redemandé pendant sept jours. La demande repart vers un autre membre de la
même catégorie ; s'il n'y en a pas, la capacité reste « à une pièce près » et l'Établi le dit. Refuser est un bouton,
sans justification — c'est écrit sur l'écran.

**Consentement et retrait ?**
Dire oui, c'est déclarer une pièce pour un créneau et consentir à son usage pour cette capacité seulement ; on a un
reçu daté. Retirer, c'est un geste sur son téléphone ; l'écran commun dit « ce composant n'est plus disponible », par
son rôle, jamais par le nom — testé. Un consentement retiré le reste ; un nouvel accord a son propre reçu.

## IA

**Pourquoi l'IA ?**
Pour une seule chose : lire les mots d'un membre et proposer une structure — une quantité, un rôle, un créneau — afin
qu'il n'ait pas à remplir un formulaire. Elle ne choisit jamais une capacité, un consentement ni un destinataire : c'est
testé, et le produit tient sans elle.

**Pourquoi Apertus ?**
Parce que le Club veut une IA suisse et ouverte, servie depuis la Suisse, qui n'enregistre ni les demandes ni les
réponses d'après son opérateur. Et parce que notre architecture ne dépend pas du modèle : Apertus se branche par trois
variables, un autre modèle aussi. Aujourd'hui, c'est Apertus qu'on a sondé et mesuré.

**Que se passe-t-il si l'IA se trompe ?**
Sa proposition passe par des règles : schéma, vocabulaire du Club, bornes, catalogue. Si elle est fausse, elle n'arrive
jamais à l'écran : le membre voit le formulaire, et il décide. On l'a mesuré : sur 26 cas, Apertus propose juste du
premier coup une fois — les 25 autres fois, les règles l'ont arrêtée.

**Et si on coupe l'IA ?**
Il y a un interrupteur sur l'Établi. IA allumée ou éteinte, l'état du Club est le même — c'est un test de la suite,
pas une promesse. Sans IA, le membre remplit trois champs lui-même.

**Ce 1 sur 26, c'est mauvais, non ?**
Oui, c'est faible, et on le dit tel quel plutôt que de l'arrondir. C'est une mesure du premier jour, avec le premier
prompt, et elle nous donne le juge pour la suite : les mêmes 26 cas, figés. Ce qui compte pour le Club, c'est que le
produit n'a jamais montré une proposition fausse.

## Données et sécurité

**Où sont les données ? Qu'est-ce qui sort du serveur ?**
Tout est sur une machine du Club — ce soir, ce portable, sans Internet. Vers le modèle ne part que le texte tapé par le
membre, débarrassé des noms, courriels et téléphones connus, jamais un profil ni la base. Le journal ne contient que
des pseudonymes ; l'écran commun ne montre que des rôles.

**nLPD, RGPD ?**
Consentement par finalité, daté, révocable en un geste, avec reçu ; « Mes données » montre à chaque membre ce que le
Club sait, pourquoi, jusqu'à quand ; « Tout effacer » retire son identité du coffre. Ce qui n'est pas fait : un avis
juridique, la rétention et l'effacement complet du journal, le chiffrement au repos — prévu ensuite, dit dans notre
modèle de menaces.

**Spam, abus, un membre qui remplit tout ?**
Des plafonds, testés : trente écritures par minute et par membre, cinq essais de code par minute, le passe juré limité
à quinze minutes et à usage unique. Au-delà, le serveur refuse poliment et le reste du Club n'attend pas. Lire ne
capte rien : aucune lecture n'écrit.

**Et un juré qui scanne le QR, il crée un compte ?**
Non : le passe juré vaut quinze minutes, sans compte, une seule fois ; le téléphone dit « vous jouez Markus,
personnage fictif », et ce qu'il fait est journalisé comme venant du jury. Ce n'est pas le parcours d'un membre, c'est
une porte pour vous.

**Et si le serveur tombe pendant la démo ?**
On le relance et le monde revient tel quel : les sessions, le passe juré, l'étape de la démo — on l'a fait avec un
`kill -9`, c'est un test. Le journal est la source de vérité ; on rejoue, on n'improvise pas.

## Foire 2026 — les questions attendues (ajoutées le 03.10)

**Anonymat à cinquante membres : on devine forcément qui s'est retiré ?**
Parfois, oui — et on ne vous promettra pas le contraire. Ce que le système garantit, testé : il ne nomme jamais, il ne
demande jamais pourquoi, et quand un rôle est porté par moins de trois membres, il ne dit même plus le rôle (« un
composant n'est plus disponible »). Le téléphone dit « Personne ne sera prévenu que c'est vous » — pas « personne ne
saura ». Dans un petit club, on peut parfois deviner ; on ne l'aide pas.

**Les données des membres français ?**
Le RGPD s'applique à eux en plus de la nLPD. L'hébergement en Suisse est licite (décision d'adéquation de l'UE, à
confirmer dans l'analyse d'impact), le consentement est prouvé par le reçu, et le retrait purge l'identité : le journal
est séparé des identités. La question d'un représentant dans l'UE est ouverte. C'est une analyse générale, pas un avis
juridique — détail dans `docs/roadmap/FINANCEMENT_JURIDIQUE.md`.

**Comment suivez-vous les partenariats ?**
Avec l'écran que vous avez vu : demandes, réponses, délai avant le premier oui, partenariats par étape — demande,
accord, essai, résultat —, résultats déclarés par le Club quand il clôture un reçu. Des agrégats seulement ; sous
trois personnes, l'écran dit « moins de trois ». Une ligne nominative n'apparaît que si le membre ET le Club l'ont
permis. On ne suit jamais les vues, ni les inscrits inactifs, ni des « matchs » d'IA. Les chiffres montrés ce soir
sont ceux du monde de démonstration.

**Pourquoi un juré peut-il répondre sans compte ?**
Ce n'est pas un compte, c'est un passe découverte : signé, utilisable une seule fois, valable quatre-vingt-dix jours,
révocable par le Club, limité à trois demandes. L'invité déclare son entreprise et reçoit un reçu, comme un membre.
Mais sa réponse est une proposition : elle ne remplit jamais une capacité à elle seule — le Club confirme, une
personne décide. Et « Rejoindre le Club » enregistre une intention, rien de plus ; la suite (un membre de la
commission qui écrit) est simulée en démonstration.

**Et les membres éloignés — Haut-Valais, Vaud, Haute-Savoie ?**
C'est la phase 2 de la feuille de route : interface en allemand, statut de membre à distance, réponse depuis l'e-mail,
adhésion croisée avec un partenaire français. Aujourd'hui, ce qui existe : les écrans d'invité en français et en
allemand, et la zone déclarée par l'invité. Prévu ensuite, pas fait.

## Économie

**Qui paie ? Ça coûte combien ?**
On ne vous donnera pas un chiffre qu'on n'a pas mesuré. Techniquement, c'est léger : un serveur, pas de base externe,
une IA facultative facturée à l'appel. Le modèle économique — abonnement du Club, service aux membres — est une
hypothèse à valider avec le Club, pas une promesse.

**Combien de membres, combien d'utilisateurs ?**
Le Club compte une cinquantaine de membres. Utilisateurs réels du prototype : zéro — tout ce que vous avez vu est un
monde fictif (150 profils), et chaque écran le dit. On n'a pas voulu simuler une
adoption. La première chose à faire après ce week-end, c'est cinq vrais membres et cinq vraies demandes.

## Réponses à ne pas donner

- Ne jamais dire « sans compte » pour un membre (seulement pour le passe juré : « quinze minutes, sans compte » ; le
  passe découverte : « sans être membre »).
- Ne jamais dire « conversion » : « intention d'adhésion ».
- Ne jamais dire « dix secondes ».
- Ne jamais citer un chiffre absent de la slide 14 ou de la slide 16.
- Ne jamais dire « propulsé par Apertus » : « on a sondé et mesuré Apertus ».
- Si on ne sait pas : « On ne l'a pas mesuré ; voilà comment on le mesurerait. »
