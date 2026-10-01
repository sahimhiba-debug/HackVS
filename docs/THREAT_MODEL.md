# Modèle de menaces — Club Pulse

> Portée : l'application du membre (`/app`), la console du Club (`/console`), l'API `/api/pulse/*`, la couche IA
> (`intelligence/ia.py`) et le journal. Démonstration **fictive**, un processus, pas d'exposition publique décidée
> (la publication est une décision de l'équipe). Chaque mesure renvoie à un test ; chaque risque résiduel est écrit.

## 1. Ce que l'on protège

| Actif | Pourquoi c'est grave | Classe |
|---|---|---|
| Identités (nom, courriel, organisation) | un annuaire aspiré ou une identité révélée sans accord | IDENTITÉ |
| Notes de rencontre privées | ce que l'on pense d'une personne rencontrée | PRIVÉ |
| Refus et silences | savoir qui a dit non abîme une relation professionnelle | SENSIBLE |
| Recherches non publiées | révèle une stratégie d'entreprise | PRIVÉ |
| Sessions, codes d'invitation, secret de signature | prise de contrôle d'un compte | secret |
| Clé Apertus | coût, usage au nom du Club | secret |
| Intégrité du journal | la mémoire vérifiée du Club (ce qui a vraiment débloqué) | AUDIT |

## 2. Acteurs et frontières de confiance

```
[membre A] ─┐                                  ┌─► [fournisseur IA externe : Apertus]  (frontière 3 : sortie non fiable)
[membre B] ─┼─► (frontière 1 : HTTP) ─► API ──┤
[console]  ─┘   entrée non fiable            └─► [coffre d'identités] ◄── (frontière 2 : le moteur ne voit que des pseudonymes)
[site tiers dans le navigateur d'un membre] ── requêtes intersites (frontière 1 bis)
```
Acteurs hostiles considérés : membre curieux (voir plus que ce qu'on lui montre), membre malveillant (injecter via son
profil, épuiser l'attention des autres), tiers sur Internet (deviner des codes, forger des sessions, CSRF), modèle de
langage qui « obéit » à une injection ou invente, opérateur négligent (journaux, secrets, dépendances).

## 3. Menaces, mesures, preuves (STRIDE)

| # | Menace | Mesure | Preuve | Résiduel |
|---|---|---|---|---|
| S1 | **Usurpation** : forger une session | jeton `pid.expiration.HMAC-SHA256` (temps constant, 12 h) ; secret ≥ 32 caractères ou aléatoire — **aucun secret par défaut** (le défaut public « demo-seulement » permettait de forger toute session : corrigé) | `test_securite_pulse.py::test_sessions_falsifiees…`, `::test_aucun_secret_par_defaut` | pas de révocation individuelle (expiration seulement) |
| S2 | Deviner un code d'invitation | code HMAC de 6 caractères ; 10 essais / minute / client (429) | `::test_deviner_un_code…` | limiteur en mémoire, par IP : contournable par rotation d'adresses ; en production, au proxy |
| S3 | Console appelée par un site tiers (CSRF) | en-tête personnalisé `X-Pulse-Console` exigé (pas de requête « simple ») ; aucun CORS ; jeton exact si `HACKVS_CONSOLE_JETON` | `::test_console_exige…` | sans jeton configuré, la console ne répond qu'à la machine locale (403 ailleurs, même serveur à l'écoute du réseau : `test_console_sans_jeton_ne_repond_qu_a_cette_machine`, `test_demo_salle_telephones.py`) ; derrière un mandataire local qui ne transmet pas l'adresse du client, définir `HACKVS_CONSOLE_JETON` |
| T1 | **Altération** : réponse à la place d'un autre | l'identité vient de la session, jamais du corps ; « non sollicité » → 403, « déjà répondu » → 409 | `test_intelligence_activation.py`, `test_securite_pulse.py` | — |
| T2 | État incohérent par requêtes concurrentes (TOCTOU) | un verrou par monde, requête entière dessous ; commandes atomiques | `::test_deux_acceptations_simultanees…`, `test_atomicite.py` | un processus seulement |
| T3 | Journal falsifié | ajout seul, identifiant = empreinte du contenu | `test_invariants.py` | pas de chaînage cryptographique ; accès au fichier = accès total |
| R1 | **Répudiation** : « je n'ai jamais accepté » | chaque geste est un événement daté, avec acteur ; journal de l'activation visible de la console | `vue_activation`, `journal()` | l'horodatage est la date simulée en démonstration |
| I1 | **Divulgation** : qui a décliné | jamais montré, ni au demandeur, ni aux autres participants, ni à la console ; défaut trouvé par le banc (graphe d'évolution) et corrigé | `::test_qui_a_decline_n_apparait…`, `eval/benchmark_pulse.py` (0 fuite / 754 écrans) | — |
| I2 | Identité révélée avant accord | rendu par spectateur (`politique.Rendu`) ; consentement orienté ; opportunité d'autrui → 403, activation d'autrui → 404 | `test_club_pulse.py`, `test_securite_pulse.py`, propriété `test_politique_aucun_nom_sans_raison` | — |
| I3 | Identité envoyée au modèle | pseudonymes + `nettoyer()` des textes libres ; sortie du modèle rejetée si elle contient courriel, téléphone ou URL | `test_frontiere_ia.py::test_injection_dans_un_profil…`, `::test_le_moteur_ne_voit_aucune_identite` | un nom propre inconnu du coffre écrit en texte libre n'est pas reconnu (liste de noms, pas de reconnaissance d'entités) |
| I4 | Note privée envoyée à un tiers | traitée localement par défaut ; envoi à Apertus seulement si `APERTUS_NOTES_PRIVEES=1`, tracé | `::test_note_privee_ne_quitte_pas…` | — |
| I5 | Fuite par les journaux | liste fermée de champs ; ni corps, ni en-têtes, ni message d'exception | `test_observabilite.py::test_les_journaux_ne_contiennent…` | la pile d'appels contient des noms de fichiers (pas de données) |
| I6 | Jeton dans l'adresse (historique, Referer) | retiré de l'adresse à l'arrivée ; `Referrer-Policy: no-referrer` | `test_e2e_pulse.py::test_application_face_aux_pannes_reseau` | présent brièvement dans l'URL de l'iframe de la console (démo) |
| I7 | Collègues d'une même organisation | rien de privé partagé entre cartes d'une même entreprise | `::test_collegues_d_une_meme_organisation…` | — |
| D1 | **Déni de service** : corps énorme | 64 Kio max (annoncé ou non) → 413 ; champs bornés (422) | `test_observabilite.py::test_corps_trop_volumineux…`, `test_securite_api.py` | pas de délai par requête côté serveur (uvicorn `--timeout-keep-alive 5`) |
| D2 | Épuiser l'attention d'un membre | budget de 2 sollicitations ouvertes par personne ; délai 4 jours puis alternative | invariant I6 | — |
| D3 | Coût IA : rafraîchissements | un appel par geste ; relire ne rappelle pas le modèle ; 30 appels de langage / minute / membre | `::test_relire_ses_sollicitations…` | — |
| D4 | Fournisseur IA en panne | 3 tentatives bornées, disjoncteur 60 s, repli déclaré | `test_frontiere_ia.py` | — |
| E1 | **Élévation** : membre → console | routes console derrière `X-Pulse-Console` (+ jeton) ; les sessions de membre n'y donnent rien | `::test_console_exige…` | la console n'a pas de comptes nominatifs (démo) |
| E2 | Injection de consignes au modèle | le texte des membres est une donnée ; vocabulaire fermé ; le modèle ne décide rien (il reformule) | `test_frontiere_ia.py`, `eval/cas_adversariaux.json` | — |
| E3 | XSS | DOM par `createTextNode` ; CSP par empreintes, sans `unsafe-inline`/`unsafe-eval` pour les scripts ; `nosniff` | `test_observabilite.py::test_en_tetes…`, bout en bout (toute violation CSP fait échouer) | styles en ligne permis |
| E4 | Dépendance vulnérable | versions exactes (`constraints.txt`) ; `pip-audit` en CI : aucune vulnérabilité connue | job CI `dependances` | nouvelle CVE entre deux exécutions |
| E5 | Secret commité | `scripts/verifier_secrets.py` en CI et dans `make quality-check` | CI | motifs connus seulement |

## 4. Hors portée (dit franchement)

- Authentification réelle des membres (SSO du Club) : non implémentée ; codes d'invitation de démonstration.
- Chiffrement au repos du coffre et des notes : non (mémoire du processus).
- TLS : à terminer au proxy (non fourni). `Strict-Transport-Security` à y ajouter.
- Multi-instance, sauvegarde, rétention et effacement RGPD/nLPD du journal : non traités (le coffre sait supprimer une
  identité : `Coffre.supprimer` ; le journal, lui, ne contient que des pseudonymes).
