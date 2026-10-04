# Choix de la voix de synthèse (04.10)

Les huit fichiers `01.m4a` … `08.m4a` de ce dossier sont produits par `docs/video/outils/voix_synthese.py`.

## Le moteur

**Piper** (réseau neuronal VITS) exécuté par **sherpa-onnx** : hors ligne, gratuit, sans compte.

Les voix Piper récentes ne sont publiées que sur Hugging Face, que la session de travail ne peut pas joindre. Elles ont
été prises dans les archives GitHub de sherpa-onnx, qui sont les mêmes modèles convertis.

Les anciennes archives GitHub de Piper (v0.0.2) ont été écartées : leur table de phonèmes perd le tilde des voyelles
nasales. « on », « an » et « in » y deviennent « o », « a » et « i ».

## Les trois voix comparées sur la séquence 01

Échantillons dans [comparaison/](comparaison/).

| Voix | Hauteur médiane | Étendue mélodique (p10–p90) | Remarque |
|---|---|---|---|
| **fr_FR-siwis-medium** — retenue | 210 Hz | **8,8 demi-tons** | la mélodie la plus vivante, nasales correctes, 22 kHz |
| fr_FR-upmc-medium (« jessica ») | 223 Hz | 6,6 demi-tons | plus plate, donc plus « lue » |
| fr_FR-siwis-low | 203 Hz | 7,1 demi-tons | même voix en basse qualité (16 kHz), **perd les nasales** |

Écartées d'office : fr_FR-miro-high, une voix grave (103 Hz) ; tom et gilles, des voix masculines.

**Honnêteté : ces voix n'ont pas été écoutées.** La session n'a pas de sortie son. Le choix repose sur la mesure
ci-dessus (une mélodie plus étendue sonne moins robotique) et sur la vérification des phonèmes. **Écoutez les trois
échantillons** : si vous en préférez une autre, la commande pour régénérer les voix est dans `docs/video/README.md`.

## Le rendu

- Débit **0,88**. Le 0,95 demandé donnait une vidéo de 9 min 26 s, sous les 10 minutes exigées.
- Une pause de 0,8 s à chaque « / », une respiration de 0,5 s entre les phrases, 0,9 s entre les lignes du script.

## La prononciation

Vérifiée phonème par phonème avec espeak-ng, la base de prononciation de Piper. La graphie phonétique ne sert
qu'au texte envoyé au moteur : le script et les sous-titres gardent l'orthographe normale.

| Mot | Sans correction | Corrigé en | Résultat |
|---|---|---|---|
| Apertus | apɛʁty (« a-pèr-tu ») | Apertusse | apɛʁtys (« a-pèr-tusse ») |
| Club Pulse | klœb pyls (« pulse » avec un u français) | Club Peulse | klœb pøls |
| Annecy | lu à l'anglaise | Anne-ci | ansi |
| IA, l'IA | ja (« ya ») | i a, l'i a | i a |
| Émilie, Spectrum, Crans-Montana, Martigny, Mondiaux | corrects | — | emili, spɛktʁɔm, kʁɑ̃mɔ̃tana… |
| 145, 173, 114, 1 sur 26, 45 jours, 2027 | corrects | — | « cent quarante-cinq », « une fois sur vingt-six »… |

« e-ID » n'est pas prononcé dans la vidéo : le script dit « l'identité électronique suisse ».

## Licence

Voix siwis : données SIWIS (Université d'Édimbourg), licence CC BY 4.0. Modèle Piper (rhasspy), converti par sherpa-onnx.

La carte de fin de la vidéo l'annonce : « Voix de synthèse · texte écrit par l'équipe Spectrum ».
