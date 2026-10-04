# Rapport — montage de bout en bout avec de fausses voix et un faux film (04.10)

But : prouver que `docs/video/monter.sh` produit une vidéo conforme **avant** que la vraie voix arrive.

## Conditions

- Voix : 8 fichiers `01.m4a` … `08.m4a` lus par une voix de synthèse (`espeak-ng`, français) **sur le texte final** de
  `SCRIPT_VIDEO.md`, avec **une seconde de blanc au début et à la fin**, comme le demande le guide d'enregistrement.
- Film : un faux film de **3 min 21 s** (mire et son continu), posé seul sur un faux Bureau. Il est trouvé par la
  **même détection que le lanceur** (`app/jour_j.chercher_film`).
- Carte de fin : un `equipe.txt` de test.
- Machine : Linux, 4 cœurs, ffmpeg 6.1. Sur un Mac récent, le montage devrait aller plus vite.

## Résultat du second passage (texte final)

| Vérification | Résultat |
|---|---|
| durée totale (10 à 12 min) | **11 min 30,9 s** (OK) |
| aucun silence de plus de 3 s, hors film | **aucun** (OK) |
| aucun mot interdit (script et sous-titres) | **aucun** (OK) |
| taille du fichier (au plus 400 Mo) | **96 Mo** (OK) |
| son (visé : -16 LUFS ± 2) | **-16,1 LUFS** (OK) |
| image | **H.264, 1920 × 1080** (OK) |
| carte de fin remplie | OK |
| temps de montage | 14 min 22 s |

Voix rognées par le montage : 01 = 47,6 s · 02 = 34,0 s · 03 = 11,0 s · 04 = 101,8 s · 05 = 73,4 s · 06 = 101,6 s ·
07 = 86,2 s · 08 = 20,5 s. Le film va de 1:37 à 4:58.

Secours HTML : un seul fichier de 20 Mo, sans aucune ressource extérieure. Le son est en MP3, lu par tous les
navigateurs. Vérifié dans Chromium : la durée de 691 s est lue, la lecture se lance, l'image et les sous-titres
suivent la position.

## Ce que le premier passage a corrigé

1. **Silences de plus de 3 s.**
   - Après le film, on enchaînait « Et après ? » muet pendant 2,4 s puis 0,6 s de respiration. C'est corrigé : 1,6 s.
   - À la fin, après « Merci. », la pause durait 2,6 s. C'est corrigé : 2,2 s.
   - Les vrais enregistrements ont une seconde de blanc au début et à la fin. Le montage les **rogne** désormais
     automatiquement.
   - Un silence qui commence dans le film ne compte qu'à partir de la fin du film.
2. **Le titre restait 20 s à l'écran.** Il est fixé à 5 s (`01-titre.mp4=5` dans le script). Sa ligne « Hack VS 2026 »
   est remontée pour ne plus passer sous les sous-titres.
3. **Le son du secours HTML ne se lisait pas** dans un Chromium sans le codec AAC. Il est maintenant en MP3.

Les voix de synthèse et le faux film ne sont pas dans le dépôt. `out/` et `voix/*.m4a` sont ignorés par git.
