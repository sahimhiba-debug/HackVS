# Top 20 — les questions les plus probables ou les plus dangereuses

Classées. Réponse courte seulement. Détail, preuve et piège dans `jury_*.md`.

**Jamais** : « validé sur le terrain » (sauf les 21 phrases) · « certifié » · « Public AI » · un nom de membre · une phrase Tally · un partenaire acquis · « le relais ne peut pas lire » sans « avec Tailscale Funnel ».

**1. Une bonne réponse sur 26. Franchement, c'est mauvais, non ?** _(Expert IA)_  
Oui, c'est faible, et on le dit tel quel : premier prompt, 26 cas écrits d'avance. Les règles ont arrêté les 25 autres. Ce que voit le membre : juste 17 fois sur 26, contre 16 avec les règles seules.

**2. Combien de personnes ont utilisé Club Pulse pendant la Foire ?** _(Direction de la Foire du Valais)_  
Personne, en vrai : monde fictif de 150 profils, dit sur chaque écran. Le seul réel : 21 phrases recueillies par le QR de la Foire, montrées en agrégats. Le pilote dira le reste.

**3. Avec 145 entreprises, on finira toujours par deviner qui a dit non.** _(Comité du Club des Affaires)_  
Parfois, oui, on ne promet pas le contraire. Garanti et testé : jamais de nom, jamais de « pourquoi », et sous trois entreprises distinctes l'écran dit « moins de trois ».

**4. Aujourd'hui, concrètement, où tourne la démo et où sont les données ?** _(Expert technique)_  
Sur notre machine, à Martigny, via un tunnel chiffré (Tailscale Funnel ; secours Cloudflare). Pas de budget d'hébergement pour la Foire ; le pilote serait hébergé en Suisse, pas encore fait.

**5. Quel est votre modèle économique ? Qui paie ?** _(Financeur)_  
Hypothèse : abonnement du Club ou service aux membres, à valider avec le Club. On ne donne pas de chiffre qu'on n'a pas. Techniquement léger : un serveur, IA facultative.

**6. Pourquoi faire le pilote pendant les Mondiaux ? Nos membres seront débordés.** _(Comité du Club des Affaires)_  
C'est voulu : quand tout le monde manque de tout, l'entraide tient-elle ? Une demande à la fois, plafond par semaine, « pas cette fois » ne coûte rien. Si ça ne tient pas, on le saura en février.

**7. Vous avez des membres en France. Le RGPD, les transferts, un représentant dans l'UE ?** _(Juriste données)_  
Le RGPD s'applique à eux. Hébergement prévu en Suisse ; adéquation confirmée par la Commission le 15 janvier 2024, à confirmer dans l'analyse d'impact. Représentant dans l'UE : à vérifier.

**8. Vos reçus sont certifiés ISO/IEC TS 27560 ?** _(Juriste données)_  
Non : alignés, pas certifiés, personne ne les a évalués. Export au format de la norme avec DPV, champs vérifiés par un test ; termes choisis sans la spécification, à relire.

**9. Pourquoi Apertus et pas un grand modèle américain ?** _(Expert IA)_  
Le Club veut une IA suisse et ouverte, servie en Suisse : Apertus 1.5, servi par le CSCS à Lugano. L'architecture ne dépend pas du modèle.

**10. Comment vous empêchez une hallucination d'arriver chez le membre ?** _(Expert IA)_  
La proposition passe par des règles (format, vocabulaire, bornes, catalogue) ; sinon formulaire, et le membre confirme toujours. Une sortie validée peut être fausse : c'est pour ça que l'appel d'outils reste éteint.

**11. La Haute-Savoie est région d'honneur cette année. Vous travaillez avec elle ?** _(Direction de la Foire du Valais)_  
Non, pas encore : c'est une piste à contacter. La Vallée d'Aoste et Crans-Montana 2027 aussi. Aucun partenaire n'est acquis.

**12. Nos membres ont déjà trop d'applications. Pourquoi ils utiliseraient celle-là ?** _(Comité du Club des Affaires)_  
On ne leur demande pas d'aller sur une plateforme : une demande précise, trois boutons, au plus une par semaine. S'ils répondront vraiment, on ne sait pas encore : c'est la question du pilote.

**13. Si la démo plante devant le public, vous faites quoi ?** _(Direction de la Foire du Valais)_  
On a un plan B : vidéo de 30 s enregistrée sur le vrai écran, dite comme simulée. Si le serveur tombe, il revient dans le même état — c'est testé. La v1 reste prête.

**14. Interreg exige un chef de file français. Vous l'avez ?** _(Financeur)_  
Non. Il faut un chef de file en Haute-Savoie ou dans l'Ain ; première piste, le stand de la Haute-Savoie, à contacter. Brouillon, rien déposé ; dépôt visé avant le 12 mars 2027, avec les résultats du pilote.

**15. Comment saura-t-on si le pilote a réussi ? Et qui décide ?** _(Comité du Club des Affaires)_  
Critères écrits d'avance, à valider par vous : ≥ 25 demandes, ≥ 30 % de oui, premier oui < 72 h en médiane, ≥ 15 actifs sur 50, zéro incident. Un signal, pas une mesure fine. Le comité décide.

**16. Quelqu'un dans la salle peut-il prendre la main sur votre console ?** _(Expert technique)_  
Fermée : une requête venue du tunnel n'est jamais « locale », la console exige un jeton, le lanceur refuse de démarrer sans. Points connus : jeton visible dans les processus du Mac, jamais renouvelé.

**17. Droit à l'effacement : votre journal est en ajout seul. Vous effacez vraiment ?** _(Juriste données)_  
Identités rangées à part ; « tout effacer » retire l'identité, le journal ne garde qu'un pseudonyme, annoncé avant le geste — testé. Pas fait : durée de conservation, effacement complet du journal, chiffrement sur disque.

**18. Qu'est-ce qui part vers le modèle, exactement ?** _(Expert IA)_  
Seulement le texte tapé, avec pseudonymes et sans les noms, courriels et téléphones connus. Jamais un profil ni la base. Limite : un nom propre inconnu écrit dans le texte n'est pas reconnu.

**19. Authentification, chiffrement, audit de sécurité : c'est prêt pour la production ?** _(Expert technique)_  
Non. Codes d'invitation de démonstration, pas encore l'authentification du Club ; pas de chiffrement sur disque. Audit interne fait, bloquants corrigés ; audit externe prévu avant le lancement.

**20. Qui fait le travail au quotidien ? Notre secrétariat est déjà chargé.** _(Comité du Club des Affaires)_  
Le secrétariat garde un temps partiel : clôturer les reçus, relayer les annonces, le bilan. Tableau et bilan automatique l'allègent. Combien d'heures : pas mesuré, le pilote le dira.
