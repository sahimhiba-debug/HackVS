# 07 — Questions du jury, version complète (six jurys simulés)

Préparé le 03.10 par un sous-agent qui a joué six jurés (direction de la Foire, comité du Club, expert technique, expert
IA, financeur, juriste données), à partir des seules sources du dépôt (CLAIMS, PREUVES, roadmap, conformité, script v2).
Chaque réponse se dit en 15 à 30 secondes ; « Preuve » et « Ne pas dire » sont pour nous, pas pour l'oral.

- Le **top 20** sur une page : [qa/TOP20.md](qa/TOP20.md) (et `qa/TOP20.pdf`).
- L'**entraînement** : `qa/qa-entrainement.html` (double-clic) — une question au hasard, la réponse cachée, un chrono de 30 s.
- La version courte d'origine : [07_QA_JURY.md](07_QA_JURY.md).

**Ce que le dépôt ne permet pas d'affirmer** (relevé par le sous-agent, donc jamais dit comme un fait) : un prix ou un
modèle économique chiffré (hypothèse seulement) ; le coût total du pilote (seul l'hébergement, « quelques dizaines de
CHF par mois », est sourcé) ; le temps du secrétariat par semaine (pas mesuré) ; des contrats de sous-traitance (CSCS,
Tailscale, Cloudflare, hébergeur, e-mail : pas encore faits) ; « le CSCS n'enregistre ni les demandes ni les réponses »
(non sourcé) ; des tests sur de vrais téléphones à travers le tunnel (à faire au rituel) ; la durée de conservation,
l'effacement complet du journal et le chiffrement au repos (non faits, THREAT_MODEL § 4).

## Juré 1 — Direction de la Foire du Valais

Ce qui l'intéresse : ce que la Foire y gagne, l'image publique, les exposants, la fiabilité devant le public.

Réponses à dire en 15 à 30 secondes. « Preuve » et « Ne pas dire » sont pour nous, pas pour l'oral.

### 1. Concrètement, qu'est-ce que la Foire y gagne ?

**Q** : Concrètement, qu'est-ce que la Foire y gagne ?

**Réponse (15–30 s à l'oral)** : La Foire crée la rencontre. Ce qui manque, c'est l'après : personne ne sait ce que deviennent les contacts. Club Pulse donne au Club un moyen de suivre ce qui se passe après, avec des chiffres agrégés. Pour les exposants, on a prévu un parcours « Allumage Foire » d'ici la Foire 2027 : il n'est pas encore construit.

**Preuve** : docs/roadmap/ROADMAP.md (Jalon 3 « Grandir ») ; docs/presentation/03_SCRIPT_ORAL_v2.md (phrase finale) ; CLAIMS n° 43, 47 (Suivi, test_foire_suivi.py)

**Ne pas dire** : « On va augmenter la fréquentation / les retombées de la Foire. » (rien n'est mesuré)

### 2. Vous dites que personne ne mesure l'après. Vous, comment vous le mesurez ?

**Q** : Vous dites que personne ne mesure l'après. Vous, comment vous le mesurez ?

**Réponse (15–30 s à l'oral)** : Chaque oui laisse un reçu. Le reçu passe par quatre étapes : accord, essai, résultat, ou retiré. C'est le Club qui déclare le résultat : signé, test sans suite, contact établi, abandonné. L'écran Suivi compte tout ça, en agrégats. Ce soir, les chiffres viennent d'un monde fictif. Les vrais chiffres viendront du pilote.

**Preuve** : CLAIMS n° 47 (test_foire_suivi.py::test_machine_a_etats_explicite) ; n° 43 ; docs/roadmap/SUIVI_METRIQUES.md

**Ne pas dire** : « 80 % des contacts de salon ne sont jamais rappelés. » (statistique contestée, invérifiable — PREUVES.md, section Contexte)

### 3. Combien de personnes ont utilisé Club Pulse pendant la Foire ? · TOP 20 n° 2

**Q** : Combien de personnes ont utilisé Club Pulse pendant la Foire ?

**Réponse (15–30 s à l'oral)** : Personne, en vrai. Le produit tourne sur un monde fictif de 150 profils, et chaque écran le dit. Ce qu'on a recueilli de réel : 21 phrases, par le QR de la Foire. On les montre seulement en agrégats. C'est le seul point qu'on compte comme validé sur le terrain. Le reste, c'est le pilote qui le dira.

**Preuve** : docs/roadmap/etat.yaml (id: tally, seul statut « valide ») ; docs/presentation/deck/data/gel.json (v2.tally) ; CLAIMS n° 77

**Ne pas dire** : « Nos utilisateurs… » ; lire ou résumer une phrase Tally ; « validé sur le terrain » pour autre chose que les 21 phrases.

### 4. Et les exposants qui ne sont pas membres du Club ?

**Q** : Et les exposants qui ne sont pas membres du Club ?

**Réponse (15–30 s à l'oral)** : Le Club peut leur donner un passe découverte. Il est signé, utilisable une fois, valable 90 jours, limité à trois demandes, et le Club peut le révoquer. L'invité peut proposer son aide. Mais sa proposition ne remplit jamais une place à elle seule : une personne du Club confirme. « Rejoindre le Club » enregistre une intention, rien de plus.

**Preuve** : CLAIMS n° 49, 51, 52 (test_foire_decouverte.py::test_une_proposition_d_invite_ne_remplit_jamais_une_capacite) ; E2E test_e2e_foire.py::test_le_jure_devient_exposant_invite_d_annecy

**Ne pas dire** : « Les exposants deviennent membres » ; « taux de conversion » (dire « intention d'adhésion » ; la suite est simulée en démonstration).

### 5. La Haute-Savoie est région d'honneur cette année. Vous travaillez avec elle ? · TOP 20 n° 11

**Q** : La Haute-Savoie est région d'honneur cette année. Vous travaillez avec elle ?

**Réponse (15–30 s à l'oral)** : Non, pas encore. C'est une piste à contacter, pendant la Foire. La Vallée d'Aoste et Crans-Montana 2027 aussi : à contacter. Aucun partenaire n'est acquis, et on ne le présente pas comme tel.

**Preuve** : docs/roadmap/ROADMAP.md (« Pistes de partenaires — toutes à contacter ») ; etat.yaml (id: partenaire_fr, note « aucun partenaire acquis ») ; CLAIMS n° 100

**Ne pas dire** : « Notre partenaire haut-savoyard » ; « on est en discussion avec… » (aucune trace dans le dépôt).

### 6. Si la démo plante devant le public, vous faites quoi ? · TOP 20 n° 13

**Q** : Si la démo plante devant le public, vous faites quoi ?

**Réponse (15–30 s à l'oral)** : On a un plan B pour chaque étape. Si personne ne peut scanner, on montre une vidéo de 30 secondes, enregistrée sur le vrai écran, et on dit que c'est une séance simulée. Si le serveur tombe, on le relance : il revient exactement dans le même état. C'est un test, avec un arrêt brutal du serveur. Et la version 1 de la présentation reste prête.

**Preuve** : CLAIMS n° 5, 18 (test_redemarrage_kill9.py) ; docs/presentation/03_SCRIPT_ORAL_v2.md (Plan B acte 3) ; docs/RAPPORT_NUIT.md (« 3 - Passer en v1 »)

**Ne pas dire** : « Ça ne peut pas planter. »

### 7. Les visiteurs qui scannent votre QR ce soir : vous gardez leurs données ?

**Q** : Les visiteurs qui scannent votre QR ce soir : vous gardez leurs données ?

**Réponse (15–30 s à l'oral)** : Non. Aucun nom, aucun compte : chaque scan donne un passe de deux heures. Après la présentation, une commande efface tout : participants, réponses, reçus. La clé change, donc les anciens QR ne marchent plus. Et chaque écran le dit : « vos données sont effacées après la présentation ».

**Preuve** : CLAIMS n° 67, 73 (test_salle.py::test_purge_totale…, E2E test_e2e_salle.py)

**Ne pas dire** : « On n'a collecté aucune donnée. » (on en collecte pendant la séance, puis on purge) ; « on vous recontactera ».

### 8. Et pour la Foire 2027, vous proposez quoi ?

**Q** : Et pour la Foire 2027, vous proposez quoi ?

**Réponse (15–30 s à l'oral)** : Le jalon « Grandir » va jusqu'à la Foire 2027. Idée : des QR sur les stands, le passe découverte, et compter les adhésions qui en viennent. C'est prévu, pas construit pour les stands. Et ça dépend d'abord du pilote de janvier.

**Preuve** : docs/roadmap/ROADMAP.md (Jalon 3 « Grandir ») ; etat.yaml (passe découverte : construit ; partenaire_fr : prévu)

**Ne pas dire** : Un nombre d'adhésions ou d'exposants attendu (aucun dans le dépôt).

## Juré 2 — Comité du Club des Affaires

Ce qui l'intéresse : ses membres, la charge du secrétariat, la confidentialité entre membres, le pilote.

Réponses à dire en 15 à 30 secondes. « Preuve » et « Ne pas dire » sont pour nous, pas pour l'oral.

### 1. Nos membres ont déjà trop d'applications. Pourquoi ils utiliseraient celle-là ? · TOP 20 n° 12

**Q** : Nos membres ont déjà trop d'applications. Pourquoi ils utiliseraient celle-là ?

**Réponse (15–30 s à l'oral)** : Parce qu'on ne leur demande pas d'aller sur une plateforme. Ils reçoivent une demande précise, et ils répondent avec un bouton : oui, non, ou pas cette fois. Au plus une demande par semaine, c'est testé. On peut aussi répondre depuis l'e-mail : c'est construit, mais l'envoi est simulé aujourd'hui. Est-ce qu'ils répondront vraiment ? On ne sait pas encore. C'est la question du pilote.

**Preuve** : CLAIMS n° 26 (test_capacites_regles.py), n° 29 (E2E test_etabli_telephones_reponse_recu_retrait_anonyme), n° 58, 59 (test_foire_distance.py)

**Ne pas dire** : « Ça prend dix secondes » (jamais chronométré) ; « sans compte » pour un membre.

### 2. Avec 145 entreprises, on finira toujours par deviner qui a dit non. · TOP 20 n° 3

**Q** : Avec 145 entreprises, on finira toujours par deviner qui a dit non.

**Réponse (15–30 s à l'oral)** : Parfois, oui. On ne vous promet pas le contraire. Ce qu'on garantit, et c'est testé : on ne nomme jamais personne, on ne demande jamais pourquoi. Tout chiffre qui vient de moins de trois entreprises s'affiche « moins de trois ». Deux représentants de la même entreprise comptent une fois. Le téléphone dit « personne ne sera prévenu que c'est vous », pas « personne ne saura ».

**Preuve** : CLAIMS n° 41, 42 (test_foire_anonymat.py::test_message_de_retrait_ne_promet_pas_l_impossible), n° 43 ; docs/roadmap/FINANCEMENT_JURIDIQUE.md (seuil en entreprises distinctes)

**Ne pas dire** : « Personne ne saura jamais » ; « anonymat garanti ».

### 3. Vous avez notre liste de membres. Qu'est-ce que vous en avez fait ?

**Q** : Vous avez notre liste de membres. Qu'est-ce que vous en avez fait ?

**Réponse (15–30 s à l'oral)** : On n'a gardé que la colonne métier. Aucun nom n'est dans notre code. On s'en sert pour compter : 145 entreprises, 25 métiers. D'après la liste, le Club pourrait assembler 8 capacités types sur 9 ; il manque un interprète. Le classement par métier, c'est nous qui l'avons proposé : il est à confirmer avec vous.

**Preuve** : CLAIMS n° 56, 87, 88 (test_assembler.py::test_liste_du_club_huit_sur_neuf…) ; PREUVES.md, section « Liste du Club »

**Ne pas dire** : Un nom de membre ; « un de vos membres exploite déjà le train vers la France » ou tout fait sur un membre précis (non vérifié, retiré du deck).

### 4. Qui fait le travail au quotidien ? Notre secrétariat est déjà chargé. · TOP 20 n° 20

**Q** : Qui fait le travail au quotidien ? Notre secrétariat est déjà chargé.

**Réponse (15–30 s à l'oral)** : Le secrétariat garde un rôle, à temps partiel : clôturer les reçus, relayer les annonces, présenter le bilan. On a construit ce qui l'allège : un tableau des demandes bloquées, un bilan généré automatiquement, avec les mêmes chiffres que l'écran. Combien d'heures par semaine ? On ne l'a pas mesuré. Le pilote le dira.

**Preuve** : docs/roadmap/ROADMAP.md (« Équipe », risque « Le secrétariat porte trop ») ; CLAIMS n° 61, 97, 99 (test_foire_bilan.py, test_tableau_bord.py)

**Ne pas dire** : « Zéro travail pour le secrétariat » ; un nombre d'heures.

### 5. Pourquoi faire le pilote pendant les Mondiaux ? Nos membres seront débordés. · TOP 20 n° 6

**Q** : Pourquoi faire le pilote pendant les Mondiaux ? Nos membres seront débordés.

**Réponse (15–30 s à l'oral)** : C'est voulu. Quand tout le monde manque de tout, est-ce que l'entraide tient ? C'est le test le plus dur. On protège les membres : une demande à la fois, un plafond par semaine, et « pas cette fois » ne coûte rien. Si ça ne tient pas, on le saura en février, avant d'investir plus.

**Preuve** : docs/roadmap/ROADMAP.md (Jalon 2, « Risque nommé », Mondiaux 1er – 14.02.2027) ; docs/presentation/07_QA_JURY.md

**Ne pas dire** : « L'entraide tiendra, on en est sûrs. »

### 6. Cinquante volontaires sur 173 représentants : et si vous ne les trouvez pas ?

**Q** : Cinquante volontaires sur 173 représentants : et si vous ne les trouvez pas ?

**Réponse (15–30 s à l'oral)** : On ne sait pas encore si on les trouvera. Aujourd'hui, on n'a aucun volontaire inscrit. Le plan : les recruter lors d'un événement du Club, avec le mode salle que vous avez vu. Si on n'arrive pas à cinquante, c'est déjà une réponse utile pour le Club.

**Preuve** : docs/roadmap/ROADMAP.md (Jalon 1, « Recrutement de 50 volontaires ») ; etat.yaml (id: pilote, prévu)

**Ne pas dire** : « On a déjà des volontaires » ; « nos membres sont partants ».

### 7. Comment saura-t-on si le pilote a réussi ? Et qui décide ? · TOP 20 n° 15

**Q** : Comment saura-t-on si le pilote a réussi ? Et qui décide ?

**Réponse (15–30 s à l'oral)** : Les critères sont écrits d'avance, et c'est vous qui les validez. Ce qu'on propose : au moins 25 demandes, au moins 30 % de oui, un premier oui en moins de 72 heures en médiane, au moins 15 membres actifs sur 50, zéro incident de confidentialité. Avec ce volume, c'est un signal, pas une mesure fine. Le comité décide.

**Preuve** : docs/roadmap/ROADMAP.md (tableau des critères, « à valider avec le Club ») ; docs/roadmap/SUIVI_METRIQUES.md

**Ne pas dire** : « Ce sera statistiquement significatif » ; présenter les seuils comme acceptés par le Club.

### 8. Est-ce que nous, au comité, on verra qui fait quoi ?

**Q** : Est-ce que nous, au comité, on verra qui fait quoi ?

**Réponse (15–30 s à l'oral)** : Vous verrez des chiffres agrégés : demandes, réponses, partenariats par étape. Une ligne avec un nom n'apparaît que si le membre ET le Club l'ont accepté. Si l'un retire son accord, la ligne disparaît. On ne suit jamais qui ne répond pas, ni qui a lu quoi.

**Preuve** : CLAIMS n° 44, 45 (test_foire_suivi.py::test_ligne_nominative_seulement_sous_double_accord) ; docs/roadmap/SUIVI_METRIQUES.md (« Ce qu'on ne suit jamais »)

**Ne pas dire** : « Vous verrez qui ne joue pas le jeu » ; « vous aurez la liste des inactifs ».

## Juré 3 — Expert technique (architecture, sécurité, fiabilité de la démo)

Ce qui l'intéresse : où tournent les données, le tunnel, la console, la charge, les tests, la production.

Réponses à dire en 15 à 30 secondes. « Preuve » et « Ne pas dire » sont pour nous, pas pour l'oral.

### 1. Ce soir, concrètement, où tourne la démo et où sont les données ? · TOP 20 n° 4

**Q** : Ce soir, concrètement, où tourne la démo et où sont les données ?

**Réponse (15–30 s à l'oral)** : Sur notre machine, ici à Martigny. Le serveur n'écoute que sur la machine elle-même ; un tunnel chiffré lui donne une adresse publique. Le tunnel principal, c'est Tailscale Funnel ; en secours, Cloudflare. On n'a pas de budget d'hébergement pour la Foire. Le pilote, lui, serait hébergé en Suisse : ce n'est pas encore fait.

**Preuve** : docs/DEMO_TUNNEL.md ; CLAIMS n° 83 (classe B : vrai le jour J seulement si lancé ainsi) ; docs/roadmap/ROADMAP.md (Jalon 1)

**Ne pas dire** : « C'est hébergé dans un cloud suisse » ; « c'est en production ».

### 2. Le service de tunnel peut-il lire ce qui passe ?

**Q** : Le service de tunnel peut-il lire ce qui passe ?

**Réponse (15–30 s à l'oral)** : Ça dépend du tunnel. Avec Tailscale Funnel, le chiffrement se termine sur notre machine : le relais ne peut pas lire les données. Avec le secours Cloudflare, le chiffrement se termine chez Cloudflare : techniquement, il peut lire. Et c'est ce que disent les fournisseurs ; nos tests ne le vérifient pas.

**Preuve** : CLAIMS n° 84 (classe C : documentation des fournisseurs, non vérifié par nos tests) ; docs/DEMO_TUNNEL.md (tableau « Le relais peut-il lire »)

**Ne pas dire** : « Le relais ne peut pas lire les données » sans préciser « avec Tailscale Funnel, pas avec le secours Cloudflare » — et jamais si le secours est en service.

### 3. Quelqu'un dans la salle peut-il prendre la main sur votre console ? · TOP 20 n° 16

**Q** : Quelqu'un dans la salle peut-il prendre la main sur votre console ?

**Réponse (15–30 s à l'oral)** : On l'a fermée. Une requête qui passe par un tunnel n'est jamais traitée comme venant de notre machine. La console exige un jeton secret, et le script de lancement refuse de démarrer sans lui. Le QR de la salle et son jeton ne sortent pas par le tunnel. Il reste des points connus : le jeton est visible dans la liste des processus du Mac, et il n'est jamais renouvelé.

**Preuve** : CLAIMS n° 11, 85 (tests/test_tunnel.py::test_requete_relayee_par_un_tunnel_n_est_pas_locale ; test_deploiement.py::test_lanceur_tunnel_exige_jeton_et_https) ; docs/RAPPORT_NUIT.md (Audit, constat 2 ; « Restent (mineurs, dits) »)

**Ne pas dire** : « C'est impossible à pirater » ; « c'est sécurisé ».

### 4. Quatre-vingts téléphones en même temps, ça tient vraiment ?

**Q** : Quatre-vingts téléphones en même temps, ça tient vraiment ?

**Réponse (15–30 s à l'oral)** : On l'a mesuré avec 80 téléphones simulés : zéro erreur, et moins de 210 millisecondes pour 95 % des requêtes. Mais c'était sur un serveur local, pas à travers Internet. On le dit. Derrière un tunnel, tout le monde a la même adresse IP : on ne limite donc jamais par IP. De vrais téléphones à travers le tunnel : c'est la vérification du matin, pas une mesure du dépôt.

**Preuve** : CLAIMS n° 76 (classe B, scripts/charge_salle.py --local --n 80), n° 86 (test_tunnel.py::test_quatre_vingts_telephones_derriere_une_seule_ip_ne_sont_pas_bloques), n° 16 ; docs/DEMO_TUNNEL.md ; PREUVES.md (« Mode salle — charge »)

**Ne pas dire** : « Testé avec 80 vrais téléphones » ; « ça tient n'importe quelle charge ».

### 5. Comment savez-vous que vos tests testent vraiment quelque chose ?

**Q** : Comment savez-vous que vos tests testent vraiment quelque chose ?

**Réponse (15–30 s à l'oral)** : Deux choses. Chaque correction commence par un test qui échoue, puis on corrige. Et on a cassé exprès le cœur du registre, plus de 1 300 fois : 1 229 versions cassées ont été attrapées ; les 98 autres ont été examinées une par une. La suite passe sur notre machine ; la CI GitHub n'a pas tourné sur les derniers commits, donc on ne dit pas « CI verte ».

**Preuve** : CLAIMS n° 10 (1 229 / 1 327, docs/audit/mutants_survivants.txt), n° 33 ; docs/presentation/deck/data/gel.json ; docs/RAPPORT_NUIT.md (« Portes locales », « CI : n'a pas tourné »)

**Ne pas dire** : « CI verte » sur la branche foire-2026 ; « 100 % de couverture ».

### 6. Authentification, chiffrement, audit de sécurité : c'est prêt pour la production ? · TOP 20 n° 19

**Q** : Authentification, chiffrement, audit de sécurité : c'est prêt pour la production ?

**Réponse (15–30 s à l'oral)** : Non. Aujourd'hui, les membres entrent avec des codes d'invitation de démonstration ; l'authentification du Club n'est pas branchée. Il n'y a pas de chiffrement des données sur le disque. On a fait relire le code par un audit interne, et les points bloquants sont corrigés. Un audit de sécurité externe est prévu avant le lancement.

**Preuve** : docs/THREAT_MODEL.md (§ 4 « Hors portée ») ; etat.yaml (id: audit_externe, prévu) ; docs/RAPPORT_NUIT.md (section « Audit »)

**Ne pas dire** : « C'est prêt pour la production » ; « c'est audité » (sans préciser : audit interne, pas externe).

### 7. Le serveur s'arrête net pendant la démo. Qu'est-ce qu'on perd ?

**Q** : Le serveur s'arrête net pendant la démo. Qu'est-ce qu'on perd ?

**Réponse (15–30 s à l'oral)** : Rien de ce qui est enregistré. Tout passe par un journal, et le journal est la source de vérité. On l'a testé en tuant le serveur brutalement : à la relance, on retrouve le même monde, les sessions, l'étape de la démo.

**Preuve** : CLAIMS n° 5, 18 (test_redemarrage_kill9.py : vrai uvicorn, SIGKILL)

**Ne pas dire** : « On ne perd jamais rien, nulle part » (pas de sauvegarde ni multi-instance : THREAT_MODEL § 4).

### 8. Et pour le pilote, l'hébergement ?

**Q** : Et pour le pilote, l'hébergement ?

**Réponse (15–30 s à l'oral)** : Le paquet de déploiement est prêt : une image, un serveur web avec HTTPS automatique, des scripts de déploiement et de purge, sans aucun secret dans les fichiers. Mais rien n'est déployé. Au jalon « Lancer », il faut l'héberger en Suisse, ajouter des sauvegardes chiffrées et la supervision.

**Preuve** : CLAIMS n° 75 (test_deploiement.py ; « le déploiement réel n'a pas été fait ») ; docs/roadmap/ROADMAP.md (Jalon 1)

**Ne pas dire** : « C'est déjà déployé » ; « ça tourne déjà sur un VPS ».

## Juré 4 — Expert IA (Apertus, 1/26, hallucinations, données)

Ce qui l'intéresse : la mesure, sa méthode, ce qui part vers le modèle, la suite.

Réponses à dire en 15 à 30 secondes. « Preuve » et « Ne pas dire » sont pour nous, pas pour l'oral.

### 1. Une bonne réponse sur 26. Franchement, c'est mauvais, non ? · TOP 20 n° 1

**Q** : Une bonne réponse sur 26. Franchement, c'est mauvais, non ?

**Réponse (15–30 s à l'oral)** : Oui, c'est faible, et on le dit tel quel. C'est notre premier prompt, sur 26 cas écrits d'avance. Les 25 autres fois, nos règles ont arrêté la proposition. Au total, ce que voit le membre est juste 17 fois sur 26, contre 16 avec les règles seules. Ça ne dit rien d'Apertus en général : ça dit que notre prompt ne suffit pas pour cette tâche.

**Preuve** : CLAIMS n° 39 (classe B, make banc-ia → prototype/eval/resultats_comprendre_action.md) ; PREUVES.md (rejeu du 03.10 : inchangé) ; docs/roadmap/APERTUS_PLAN.md

**Ne pas dire** : « Apertus est mauvais » ; « c'est un bon score » ; « le produit n'a jamais montré une proposition fausse » (le membre voit encore 9 cas sur 26 faux, venus des règles).

### 2. Alors pourquoi garder l'IA ?

**Q** : Alors pourquoi garder l'IA ?

**Réponse (15–30 s à l'oral)** : Pour une seule chose : lire les mots du membre et proposer une structure, pour lui éviter un formulaire. Elle ne choisit jamais une capacité, un consentement ou un destinataire. C'est testé. IA allumée ou éteinte, l'état du Club est le même : c'est aussi un test. La démo de scène tourne sans modèle.

**Preuve** : CLAIMS n° 1 (test_frontiere_ia.py, test_provenance_ia.py), n° 7 (test_parite_ia.py, non vacueux) ; docs/roadmap/APERTUS_PLAN.md

**Ne pas dire** : « Propulsé par Apertus » (dire « on a sondé et mesuré Apertus ») ; « l'IA trouve les bons partenaires ».

### 3. Comment vous empêchez une hallucination d'arriver chez le membre ? · TOP 20 n° 10

**Q** : Comment vous empêchez une hallucination d'arriver chez le membre ?

**Réponse (15–30 s à l'oral)** : La proposition passe par des règles : format, vocabulaire du Club, bornes, catalogue, aucune donnée personnelle. Si elle échoue, le membre voit le formulaire, et c'est dit à l'écran. Et le membre confirme toujours. Mais une sortie qui passe les règles peut être fausse : avec l'appel d'outils, 3 sorties fausses sont passées. Donc on l'a laissé éteint.

**Preuve** : CLAIMS n° 38 (test_ia_preparer_action.py, E2E test_e2e_ia.py), n° 89 (apertus-outils : 1/26, 3 fausses acceptées) ; test_frontiere_ia.py::test_entite_inventee_rejetee

**Ne pas dire** : « L'IA ne peut pas halluciner » ; « aucune erreur ne passe ».

### 4. Pourquoi Apertus et pas un grand modèle américain ? · TOP 20 n° 9

**Q** : Pourquoi Apertus et pas un grand modèle américain ?

**Réponse (15–30 s à l'oral)** : Parce que le Club veut une IA suisse et ouverte, servie en Suisse : Apertus 1.5, servi par le CSCS à Lugano. Et notre architecture ne dépend pas du modèle : on peut en brancher un autre. Pour les 21 phrases de la Foire, on a promis « une IA suisse » : le code refuse tout autre modèle.

**Preuve** : CLAIMS n° 8 (sonde), n° 64 (test_foire_tally.py::test_consentement…) ; PREUVES.md (point d'accès api.inference.cscs.ch) ; docs/roadmap/APERTUS_PLAN.md

**Ne pas dire** : « Public AI » (dire « CSCS ») ; « Apertus est meilleur que les modèles américains » (non mesuré).

### 5. Qu'est-ce qui part vers le modèle, exactement ? · TOP 20 n° 18

**Q** : Qu'est-ce qui part vers le modèle, exactement ?

**Réponse (15–30 s à l'oral)** : Seulement le texte tapé par le membre. On remplace les noms par des pseudonymes, on retire les noms, courriels et téléphones qu'on connaît. Jamais un profil, jamais la base. Limite connue : un nom propre qu'on ne connaît pas, écrit dans le texte, n'est pas reconnu.

**Preuve** : docs/THREAT_MODEL.md (I3 : test_frontiere_ia.py::test_injection_dans_un_profil…, limite « nom propre inconnu ») ; docs/ARCHITECTURE.md (Coffre.pseudonymiser)

**Ne pas dire** : « Aucune donnée personnelle ne peut partir. »

### 6. Les 21 phrases de la Foire : Apertus les a bien comprises ?

**Q** : Les 21 phrases de la Foire : Apertus les a bien comprises ?

**Réponse (15–30 s à l'oral)** : On ne sait pas encore. Apertus a classé les 21 ; ses 21 sorties respectent le format, et 20 fois il s'est abstenu. Mais personne n'a encore annoté les bonnes réponses : donc aucune exactitude n'est mesurée. Ces phrases ne servent qu'à tester, jamais à entraîner, et on ne les montre qu'en agrégats.

**Preuve** : PREUVES.md (« Classification des 21 phrases Tally… 21 / 21 acceptées, dont 20 abstentions ; aucune exactitude mesurée ») ; CLAIMS n° 63, 64, 65 ; docs/roadmap/APERTUS_PLAN.md

**Ne pas dire** : Lire ou paraphraser une phrase ; « Apertus a compris 21 phrases sur 21 ».

### 7. Comment comptez-vous améliorer ce score ?

**Q** : Comment comptez-vous améliorer ce score ?

**Réponse (15–30 s à l'oral)** : Dans l'ordre : figer un jeu de test humain, générer des exemples synthétiques, forcer le format de sortie, puis affiner un petit Apertus. La chaîne d'affinage est prête ; un essai a produit 10 exemples, 9 gardés. Aucun entraînement n'est lancé. On fixera un objectif chiffré seulement après l'annotation, et on le mesurera avant de l'afficher.

**Preuve** : docs/roadmap/APERTUS_PLAN.md (Stratégie, Objectifs) ; CLAIMS n° 101 (test_finetune.py ; essai 9/10) ; PREUVES.md (pipeline d'affinage)

**Ne pas dire** : « Après l'affinage, on sera à X % » (aucun objectif chiffré dans le dépôt).

### 8. Et la latence ? Cinq secondes pour un membre, c'est long.

**Q** : Et la latence ? Cinq secondes pour un membre, c'est long.

**Réponse (15–30 s à l'oral)** : On l'a mesurée : médiane 5,3 secondes, et 6,0 pour 95 % des cas, sur 30 appels. Un second passage le 3 octobre donne 5,7 et 7,4. C'est mesuré depuis notre environnement de développement, pas depuis la salle. Pendant l'appel, le serveur ne gèle pas, et l'attente est bornée. Sans IA, le membre remplit trois champs.

**Preuve** : CLAIMS n° 38, 40 (make latence-ia → docs/audit/latence_apertus.md) ; PREUVES.md (rejeu du 03.10 : 5,7 s / 7,4 s)

**Ne pas dire** : « C'est instantané » ; une latence mesurée dans la salle (il n'y en a pas).

## Juré 5 — Financeur (Interreg, Innosuisse, modèle économique, coûts)

Ce qui l'intéresse : qui paie, combien, l'éligibilité, ce qui existe vraiment.

Réponses à dire en 15 à 30 secondes. « Preuve » et « Ne pas dire » sont pour nous, pas pour l'oral.

### 1. Quel est votre modèle économique ? Qui paie ? · TOP 20 n° 5

**Q** : Quel est votre modèle économique ? Qui paie ?

**Réponse (15–30 s à l'oral)** : On ne vous donnera pas un chiffre qu'on n'a pas. Notre hypothèse : un abonnement du Club, ou un service aux membres. C'est à valider avec le Club, ce n'est pas une promesse. Techniquement, c'est léger : un serveur, pas de base externe, une IA facultative.

**Preuve** : docs/presentation/07_QA_JURY.md (« Qui paie ? ») ; docs/roadmap/ROADMAP.md (« Budget — hypothèses »)

**Ne pas dire** : Un prix d'abonnement, un chiffre d'affaires, un nombre de clubs (aucun dans le dépôt).

### 2. Combien coûte le pilote ?

**Q** : Combien coûte le pilote ?

**Réponse (15–30 s à l'oral)** : Ce n'est pas encore chiffré, rien n'est engagé. Les postes sont connus : l'hébergement en Suisse, quelques dizaines de francs par mois selon notre hypothèse ; un audit de sécurité et un juriste, forfaits à demander ; deux ingénieurs pendant 30 jours, puis à mi-temps. L'IA est payée à l'appel, et le pilote peut tourner sans.

**Preuve** : docs/roadmap/ROADMAP.md (« Budget — hypothèses (à chiffrer, rien n'est engagé) », « Équipe »)

**Ne pas dire** : Un montant total ; « ça ne coûte presque rien ».

### 3. Interreg exige un chef de file français. Vous l'avez ? · TOP 20 n° 14

**Q** : Interreg exige un chef de file français. Vous l'avez ?

**Réponse (15–30 s à l'oral)** : Non. Le programme demande un chef de file en Haute-Savoie ou dans l'Ain. Notre première piste, c'est le stand de la Haute-Savoie : à contacter. Le pré-projet est un brouillon, rien n'est déposé. On vise un dépôt avant le 12 mars 2027, avec les résultats du pilote, quels qu'ils soient. Les conditions du programme sont à revérifier.

**Preuve** : docs/roadmap/FINANCEMENT_JURIDIQUE.md (Interreg) ; docs/roadmap/financement/INTERREG_PRE_PROJET.md (§ 5, tous « à contacter ») ; CLAIMS n° 100

**Ne pas dire** : « Notre partenaire français » ; « le dossier est déposé ».

### 4. Innosuisse : quelle innovation, et avec quelle haute école ?

**Q** : Innosuisse : quelle innovation, et avec quelle haute école ?

**Réponse (15–30 s à l'oral)** : La question de recherche : une demande précise, adressée à une catégorie de membres, avec un consentement prouvé, obtient-elle plus de oui, plus vite, sans exposer qui dit non ? On viserait un chèque d'innovation avec la HES-SO Valais-Wallis. Elle est à contacter : aucun accord. La contribution propre rapportée est de 40 à 60 % pour un projet d'innovation, à revérifier.

**Preuve** : docs/roadmap/financement/INNOSUISSE_NOTE.md ; docs/roadmap/FINANCEMENT_JURIDIQUE.md

**Ne pas dire** : « La HES-SO est partenaire » ; « on a obtenu un chèque ».

### 5. Pourquoi financer un projet qui n'a aucun utilisateur ?

**Q** : Pourquoi financer un projet qui n'a aucun utilisateur ?

**Réponse (15–30 s à l'oral)** : Parce que le code n'est plus le problème : la validation l'est. On propose un pilote de 45 jours, avec des critères écrits avant de commencer. Si ça ne marche pas, on le saura en février, avant de dépenser plus. Les résultats iront tels quels dans le dossier Interreg.

**Preuve** : docs/roadmap/ROADMAP.md (introduction, Jalon 2) ; docs/roadmap/financement/INTERREG_PRE_PROJET.md (§ 6)

**Ne pas dire** : « Le produit est validé sur le terrain » ; « nos premiers utilisateurs ».

### 6. Qu'est-ce qui existe vraiment, et qu'est-ce qui n'est que dans vos slides ?

**Q** : Qu'est-ce qui existe vraiment, et qu'est-ce qui n'est que dans vos slides ?

**Réponse (15–30 s à l'oral)** : Notre feuille de route le dit chantier par chantier : 22 construits et testés, 1 validé sur le terrain, 8 prévus. Un test refuse « construit » sans fichiers de test, et « validé » sans preuve réelle. Le seul validé sur le terrain, ce sont les 21 phrases de la Foire. Le pilote, le juriste, l'audit externe, les partenaires : prévus.

**Preuve** : docs/roadmap/etat.yaml ; docs/roadmap/README.md (tableau généré) ; CLAIMS n° 77 (test_feuille_de_route.py) ; gel.json (v2.etat : 22 / 1 / 8)

**Ne pas dire** : « Tout est prêt » ; « validé » pour un chantier « construit ».

### 7. Vous dépendez du CSCS. Et s'il arrête, ou si ses conditions ne conviennent pas ?

**Q** : Vous dépendez du CSCS. Et s'il arrête, ou si ses conditions ne conviennent pas ?

**Réponse (15–30 s à l'oral)** : Le produit tient sans modèle : IA allumée ou éteinte, l'état du Club est le même, c'est testé. Les conditions d'utilisation du CSCS pour un pilote sont à vérifier au jalon « Lancer ». Sinon, on passe par un hébergeur suisse, ou on reste sans IA.

**Preuve** : CLAIMS n° 7 (test_parite_ia.py) ; docs/roadmap/ROADMAP.md (Jalon 1, « Conditions d'utilisation du service d'IA » ; « Dépendances ») ; docs/roadmap/FINANCEMENT_JURIDIQUE.md (Service d'IA)

**Ne pas dire** : « Public AI » (même comme solution de relais — le dépôt l'évoque, mais c'est interdit à l'oral) ; « le CSCS nous a donné son accord ».

### 8. Pourquoi pas LinkedIn, ou un réseau comme BNI ?

**Q** : Pourquoi pas LinkedIn, ou un réseau comme BNI ?

**Réponse (15–30 s à l'oral)** : LinkedIn met en relation ; il ne sait pas ce que le Club peut faire ensemble vendredi. Nous, on part d'une demande précise, on la compose avec des membres qui disent oui, et on suit le résultat. De BNI, on reprend une leçon : mesurer les affaires conclues, pas les rencontres. Ce qu'aucun ne donne, c'est un reçu de ce qu'on a consenti.

**Preuve** : docs/presentation/07_QA_JURY.md (« Pourquoi pas LinkedIn ? ») ; docs/roadmap/BENCHMARK.md

**Ne pas dire** : Un chiffre de part de marché ou d'utilisateurs d'un concurrent (aucun dans le dépôt).

## Juré 6 — Juriste données (nLPD, RGPD, consentement, ISO/IEC TS 27560, k-anonymat, sous-traitance, hébergement)

Ce qui l'intéresse : la base légale, les transferts, l'effacement, les tiers, ce qui est promis à l'écran.

Réponses à dire en 15 à 30 secondes. « Preuve » et « Ne pas dire » sont pour nous, pas pour l'oral.

### 1. Quelle est votre base légale ?

**Q** : Quelle est votre base légale ?

**Réponse (15–30 s à l'oral)** : Le consentement, finalité par finalité. Chaque oui donne un reçu : référence, finalité, date, révocable. Retirer, c'est un geste. Et il n'y a pas de décision automatisée : l'IA propose, le membre décide. C'est notre analyse générale, pas un avis juridique. L'analyse d'impact avec un juriste est prévue.

**Preuve** : docs/roadmap/FINANCEMENT_JURIDIQUE.md (Cadre juridique) ; CLAIMS n° 1 (test_frontiere_ia.py) ; docs/conformite/REGISTRE_TRAITEMENTS.md

**Ne pas dire** : « On est conformes nLPD et RGPD. »

### 2. Vous avez des membres en France. Le RGPD, les transferts, un représentant dans l'UE ? · TOP 20 n° 7

**Q** : Vous avez des membres en France. Le RGPD, les transferts, un représentant dans l'UE ?

**Réponse (15–30 s à l'oral)** : Le RGPD s'applique aux membres qui résident en France. On hébergerait en Suisse. La Commission européenne a confirmé l'adéquation de la Suisse le 15 janvier 2024 : à confirmer dans l'analyse d'impact. Le représentant dans l'UE : question ouverte, à vérifier. Analyse générale, pas un avis juridique.

**Preuve** : docs/roadmap/FINANCEMENT_JURIDIQUE.md (RGPD, Décision d'adéquation) ; docs/conformite/REGISTRE_TRAITEMENTS.md (« Représentant dans l'UE : à vérifier »)

**Ne pas dire** : « Le RGPD ne s'applique pas, on est en Suisse » ; « tout est réglé pour la France ».

### 3. Vos reçus sont certifiés ISO/IEC TS 27560 ? · TOP 20 n° 8

**Q** : Vos reçus sont certifiés ISO/IEC TS 27560 ?

**Réponse (15–30 s à l'oral)** : Non : alignés, pas certifiés. Personne ne les a évalués. On exporte chaque reçu dans le format de cette norme, avec le vocabulaire DPV, et un test vérifie nos champs obligatoires. Mais on a choisi les termes sans accès à la spécification : c'est à relire par quelqu'un qui la connaît.

**Preuve** : docs/conformite/RECU_27560.md (« Aligné, jamais certifié », « Limites ») ; CLAIMS n° 90 (test_recu_27560.py ; l'alignement lui-même : classe C)

**Ne pas dire** : « Certifié » ; « conforme à la norme ».

### 4. Votre « moins de trois », c'est vraiment du k-anonymat ?

**Q** : Votre « moins de trois », c'est vraiment du k-anonymat ?

**Réponse (15–30 s à l'oral)** : C'est un seuil d'affichage, pas une garantie mathématique sur toute la base. Tout chiffre qui vient de moins de trois entreprises distinctes s'affiche « moins de trois ». Un rôle porté par moins de trois n'est jamais dit dans un avis de retrait. Ça empêche de compter, pas toujours de deviner. En salle ce soir, le seuil porte sur des passes : la salle est anonyme, et purgée après.

**Preuve** : CLAIMS n° 41, 43, 92 ; docs/roadmap/FINANCEMENT_JURIDIQUE.md (seuil en entreprises distinctes) ; docs/RAPPORT_NUIT.md (Audit, constat 11, « dit, non corrigé »)

**Ne pas dire** : « Anonymat garanti » ; « k-anonymat au sens strict ».

### 5. Droit à l'effacement : votre journal est en ajout seul. Vous effacez vraiment ? · TOP 20 n° 17

**Q** : Droit à l'effacement : votre journal est en ajout seul. Vous effacez vraiment ?

**Réponse (15–30 s à l'oral)** : Les identités sont rangées à part du journal. « Tout effacer » retire l'identité ; ce qui reste dans le journal ne porte qu'un pseudonyme, et l'écran l'annonce avant le geste. C'est testé, y compris après redémarrage. Ce qui n'est pas fait : la durée de conservation et l'effacement complet du journal, et le chiffrement sur disque. C'est pour l'analyse d'impact.

**Preuve** : CLAIMS n° 23 (test_effacement.py::test_tout_effacer_oublie_le_membre_et_survit_au_redemarrage ; E2E test_tout_effacer_annonce_ce_qui_reste_avant_le_geste) ; docs/THREAT_MODEL.md (§ 4)

**Ne pas dire** : « Tout est effacé partout » ; « il ne reste aucune trace ».

### 6. Qui sont vos sous-traitants ? Le CSCS, le tunnel, l'hébergeur, l'e-mail ?

**Q** : Qui sont vos sous-traitants ? Le CSCS, le tunnel, l'hébergeur, l'e-mail ?

**Réponse (15–30 s à l'oral)** : Pour le pilote, on ne prévoit aucun transfert hors de Suisse. Le modèle d'IA est servi par le CSCS, à Lugano : ses conditions sont à vérifier. Hébergeur et e-mails : pas encore choisis. Ce soir, la démo passe par un tunnel : avec Tailscale Funnel, le relais ne peut pas lire les données ; avec le secours Cloudflare, il le peut techniquement. Les contrats avec ces tiers : pas encore faits, c'est pour l'analyse d'impact.

**Preuve** : docs/conformite/REGISTRE_TRAITEMENTS.md (Transferts hors de Suisse) ; docs/roadmap/ROADMAP.md (Jalon 1) ; docs/DEMO_TUNNEL.md ; CLAIMS n° 84

**Ne pas dire** : « Aucun tiers ne voit rien » ; « le relais ne peut pas lire » sans préciser le tunnel ; « Public AI ».

### 7. Les jurés qui scannent ce soir : où est l'information, et peuvent-ils retirer leur accord ?

**Q** : Les jurés qui scannent ce soir : où est l'information, et peuvent-ils retirer leur accord ?

**Réponse (15–30 s à l'oral)** : Aucun nom, aucun compte : chaque scan donne un passe de deux heures. Sans consentement, rien n'est déclaré. Chaque écran dit que tout est effacé après la présentation, et la purge est testée. Une limite qu'on connaît : en salle, on ne peut retirer qu'après avoir dit oui. Ce sera corrigé après le gel.

**Preuve** : CLAIMS n° 67, 68, 73 (test_salle.py) ; docs/RAPPORT_NUIT.md (Audit, constat 20) ; page /confidentialite (CLAIMS n° 94, « à valider par un juriste »)

**Ne pas dire** : « Ils peuvent tout retirer à tout moment » ; « on ne collecte rien ».

### 8. Les photos de cartes de visite, les 21 phrases de la Foire : que devient tout ça ?

**Q** : Les photos de cartes de visite, les 21 phrases de la Foire : que devient tout ça ?

**Réponse (15–30 s à l'oral)** : La photo de la carte n'est jamais conservée : ni dans le journal, ni sur le disque. L'entreprise confirmée part avec « tout effacer ». Pour les phrases de la Foire, on a promis qu'elles servent seulement à tester une IA suisse. Le code refuse tout autre modèle. Elles restent hors du code publié, ne servent jamais à entraîner, et on ne montre que des agrégats.

**Preuve** : CLAIMS n° 81 (test_carte_profil.py), n° 63, 64 (test_foire_tally.py::test_consentement…) ; docs/roadmap/APERTUS_PLAN.md (règles du jeu figé)

**Ne pas dire** : Citer une phrase ; « on garde les cartes pour enrichir les profils ».
