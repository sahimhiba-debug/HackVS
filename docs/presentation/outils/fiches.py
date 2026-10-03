"""PDF présentateur : le texte à dire (03b) à gauche, ce que le jury voit à droite (écrans réels + aperçus de slides)."""
import base64
import html
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

R = Path("/home/user/HackVS")
CAP = R / "docs/presentation/captures"
POLICE = base64.b64encode((R / "prototype/web/pulse/polices/plus-jakarta-sans-latin-wght-normal.woff2").read_bytes()).decode()
SORTIE = Path(sys.argv[1])


def img(nom, cls=""):
    b = base64.b64encode((CAP / nom).read_bytes()).decode()
    return f"<img class='{cls}' src='data:image/png;base64,{b}'>"


def reel(nom, legende, cls="ecran"):
    return f"<figure><span class='tag reel'>ÉCRAN RÉEL</span>{img(nom, cls)}<figcaption>{legende}</figcaption></figure>"


def carton(phrase, legende="carton : fond noir, une phrase"):
    return (f"<figure><span class='tag apercu'>APERÇU DE SLIDE</span><div class='slide noir'><b>{phrase}</b></div>"
            f"<figcaption>{legende}</figcaption></figure>")


def slide(contenu, legende, cls="clair"):
    return (f"<figure><span class='tag apercu'>APERÇU DE SLIDE</span><div class='slide {cls}'>{contenu}</div>"
            f"<figcaption>{legende}</figcaption></figure>")


def avenir(titre, detail):
    return (f"<figure><span class='tag avenir'>À VENIR — PAS ENCORE DANS LE DÉPÔT</span><div class='slide vide'>"
            f"<b>{titre}</b><span>{detail}</span></div></figure>")


def dire(*lignes):
    out = []
    for l in lignes:
        if l.startswith("["):
            out.append(f"<p class='geste'>{html.escape(l)}</p>")
        elif l.startswith("V1 —") or l.startswith("V2 —"):
            qui, reste = l.split("—", 1)
            out.append(f"<p><span class='qui {qui.strip().lower()}'>{qui.strip()}</span>{html.escape(reste.strip())}</p>")
        elif l.startswith("!"):
            out.append(f"<p class='variante'>{html.escape(l[1:])}</p>")
        else:
            out.append(f"<p>{html.escape(l)}</p>")
    return "".join(out)


def montrer(*points):
    return "<div class='doigt'><b>Ce que vous montrez</b><ul>" + "".join(f"<li>{html.escape(p)}</li>" for p in points) + "</ul></div>"


def temps(acte, titre, horaire, texte, visuel, apres="", deux=False):
    return (f"<section class='temps{' deux' if deux else ''}'><header><span class='acte'>{acte}</span><h2>{titre}</h2>"
            f"<span class='horaire'>{horaire}</span></header><div class='grille'><div class='dire'><div class='lab'>Ce que vous dites</div>{texte}{apres}</div>"
            f"<div class='voit'><div class='lab'>Ce que le jury voit</div>{visuel}</div></div></section>")


T = []
# ---------- ACTE 1
T.append(temps("Acte 1", "La carte", "0:00 → 0:35",
    dire("[une carte de visite plein écran]",
         "Voici le document le plus optimiste du monde professionnel.",
         "On le donne avec conviction. On se regarde dans les yeux. Et on dit : « On s'appelle. »",
         "Levez la main si vous avez déjà donné une carte en disant « on s'appelle ».",
         "[mains] Gardez la main levée si vous avez appelé.",
         "[rire] Merci. Vous pouvez baisser la main. Ici, personne ne juge. Moi non plus, j'ai une boîte à chaussures pleine de cartes à la maison."),
    avenir("Photo : une vraie carte de visite, à plat, plein écran",
           "Nom et entreprise fictifs (Sophie — tisanes de plantes alpines). Pas de logo Club Pulse, pas de titre. "
           "Slide 1 — photo à faire côté design. La même carte revient à la fin (acte 9)."),
    montrer("Rien : vous regardez le jury, pas l'écran.", "Vous levez vous-même la main en premier — ils suivent.")))
T.append(temps("Acte 1", "Et après ?", "0:35 → 0:45",
    dire("[slide « Et après ? »]", "Et après ?", "[deux secondes de silence — on compte dans sa tête : un… deux…]"),
    slide("<b class='geant'>Et après ?</b>", "slide 2 — la même revient en 8 (après le film) et en 17 (fin)", "noir"),
    montrer("Rien. Le silence fait le travail. Ne pas enchaîner trop vite.")))
# ---------- ACTE 2
T.append(temps("Acte 2", "Le problème", "0:45 → 1:30",
    dire("[carton : « Ce qui se passe entre deux événements. »]",
         "Après, en général… rien. Pas par mauvaise volonté. La Foire, c'est dix jours, des centaines de rencontres. Et le lendemain, chacun retourne à son entreprise, à ses mails, à ses clients.",
         "[slide « le vide » : deux dates, rien entre les deux]",
         "Le Club des Affaires ne manque pas de rencontres. Il en crée plus que n'importe qui dans ce canton. Ce qui manque, c'est l'après. Le moment où une rencontre devient quelque chose qu'on fait ensemble."),
    carton("Ce qui se passe entre deux événements.", "slide 3 — carton DEMANDE")
    + slide("<div class='frise'><span>Foire du Valais</span><i></i><span>prochain événement du Club</span></div>",
            "slide 4 — « le vide » : entre les deux, rien. Pas de texte explicatif.")))
T.append(temps("Acte 2", "Le oui → Jean-Marc", "1:30 → 2:00",
    dire("[slide « Oui. »]",
         "Et quand ça arrive quand même, vous savez pourquoi ? Parce que quelqu'un a dit oui. Pas « on s'appelle ». Oui.",
         "Plutôt que de vous expliquer le problème, on va vous présenter quelqu'un. Il dit oui à tout le monde. Depuis vingt ans. Il s'appelle Jean-Marc.",
         "[carton : « L'homme qui disait oui. » — noir — le film]"),
    slide("<b class='geant encre'>Oui.</b><span class='sous'>(pas « on s'appelle »)</span>", "slide 5 — un seul mot")
    + carton("L'homme qui disait oui.", "slide 6 — carton CONTRIBUTION, 2 s, puis noir, puis le film (lancé à la main par V2)"),
    montrer("Au mot « Jean-Marc » : un pas de côté. Vous regardez le jury pendant les 3 premières secondes du film.")))
# ---------- ACTE 3
T.append(temps("Acte 3", "Le film « L'homme qui disait oui »", "2:00 → 4:25",
    dire("[on se tait, on regarde le jury regarder]",
         "!Vous ne dites rien pendant 2 min 25. Pour maîtriser la suite, sachez ce que le jury vient de voir :")
    + "<ol class='film'><li>une demande qui arrive chez Jean-Marc — c'est le <b>vrai écran « Demandes »</b> du produit (celui de l'acte 5) ;</li>"
      "<li>le <b>reçu</b>, plein cadre, 4 secondes (il revient à l'acte 5 et à l'acte 9) ;</li>"
      "<li>le premier refus ;</li><li>un oui choisi ;</li>"
      "<li>une demande dite à l'oral, mise en forme, à l'apéro final (elle prépare « Pauline écrit avec ses mots »).</li></ol>"
      "<p class='variante'>Cartons de fin : « Si Jean-Marc dit oui, c'est que c'est oui. » puis logo + « Le Club sait ce qu'il peut faire cette semaine. » "
      "→ Votre dernière phrase du pitch reprend le premier carton MOT POUR MOT.</p>",
    avenir("Le film — 21 plans, environ 2:25", "Hors deck, copie locale sur la machine + clé USB. Aucune image du film n'est reproduite ici.")
    + "<p class='petit'>Plan B si le film ne part pas : « On vous le racontera. » + Jean-Marc en trois phrases (05_FILM_INTEGRATION § 6).</p>"))
T.append(temps("Respiration", "Jean-Marc a dit oui", "4:25 → 4:40",
    dire("[dernier plan figé, puis « Et après ? »]", "Jean-Marc a dit oui. … Et après ?",
         "!Si le film finit sur un rire : attendre qu'il retombe. Sur un silence : enchaîner tout de suite."),
    avenir("Dernier plan du film, figé 3 s", "Puis la slide « Et après ? » (2/3).")
    + slide("<b class='geant'>Et après ?</b>", "slide 8 = slide 2", "noir")))
# ---------- ACTE 4
T.append(temps("Acte 4", "La révélation — l'Établi", "4:40 → 5:10",
    dire("[carton : « Le même geste. Dans le vrai produit. » — puis l'Établi, plein écran]",
         "Cette demande, vous venez de la voir arriver chez Jean-Marc. Elle existe ici. Pour de vrai.",
         "Ça, c'est l'Établi du Club. Une capacité : accueillir une délégation d'acheteurs germanophones. Il faut trois choses : une salle, quelqu'un qui parle allemand, un minibus. Deux sont là, déclarées par des membres, valables vendredi. Il manque le minibus.",
         "Le Club ne cherche pas « quelqu'un ». Il demande une chose précise — un minibus de douze places — à ceux qui pourraient l'avoir. Pas un mail à deux cents personnes. Une question, aux bonnes personnes.",
         "[Prénom], le téléphone est à toi."),
    carton("Le même geste. Dans le vrai produit.", "slide 9 — carton ESSAI")
    + reel("etabli-1-manque.png", "<b>/etabli</b> — la carte de gauche, pastille orange « il manque une pièce ». Slide 10 = cette capture (secours de l'écran vivant)."),
    montrer("La carte de gauche « Accueillir une délégation d'acheteurs germanophones ».",
            "« lieu » et « voix » : coche verte = les deux pièces qui sont là.",
            "« transport » en rouge pointillé : la pièce qui manque — c'est elle qui porte la demande.",
            "En haut : « monde fictif », « date du Club (simulée) » — c'est normal, c'est honnête.")))
# ---------- ACTE 5
T.append(temps("Acte 5", "La demande sur le téléphone", "5:10 → 5:40",
    dire("[V2 ouvre l'onglet Demandes]",
         "V2 — Je suis Pauline. Membre fictive. Voilà la demande sur mon téléphone.",
         "V1 — La même qu'à l'écran. Trois boutons : Oui. Non. Pas cette fois. On peut dire non sans se justifier, c'est écrit dessus. Essayez ça dans un comité.",
         "Pauline a un minibus. Elle n'a pas envie de remplir un formulaire — personne n'a envie de remplir un formulaire. Alors elle écrit avec ses mots."),
    reel("tel-1-demande.png", "<b>/app</b>, téléphone de Pauline, onglet « Demandes » (en rouge en bas).", "tel"),
    montrer("La grosse phrase noire : c'est la même demande que la pièce rouge de l'Établi.",
            "Les trois boutons Oui / Non / Pas cette fois.",
            "La petite ligne sous les boutons : « Vous pouvez refuser sans vous justifier ».")))
T.append(temps("Acte 5", "Pauline écrit avec ses mots", "5:40 → 6:10",
    dire("[V2 tape : « Mon minibus a 14 places, libre vendredi après-midi. » et appuie sur « Proposer à partir de mon texte »]",
         "V2 — « Mon minibus a quatorze places, libre vendredi après-midi. » Je demande une proposition.",
         "V1 — Ce soir, l'intelligence artificielle est éteinte. Exprès. Le produit propose quand même la structure : trois champs, et Pauline les remplit elle-même. Quatorze. C'est une garantie : IA allumée ou éteinte, le Club obtient le même résultat. Et la meilleure façon de le prouver, c'est de la laisser éteinte.",
         "!Seulement si le test de samedi a donné 3 sur 3 (IA allumée) : « Le modèle a lu sa phrase et a sorti le chiffre : quatorze places. Il propose. Il ne décide rien. Le code vérifie que c'est un nombre, et qu'il est au moins douze. Et c'est Pauline qui répond. »",
         "[V2 vérifie « 14 », appuie sur Oui]"),
    reel("tel-1b-proposition.png", "Après « Proposer à partir de mon texte », IA éteinte : le produit l'écrit lui-même — « forme déterministe, sans IA ».", "tel"),
    montrer("Le texte de Pauline dans la case.",
            "La ligne grise « forme déterministe, sans IA » : la preuve à l'écran que l'IA est éteinte.",
            "Le champ « places (au moins 12) » avec 14 : c'est Pauline qui le remplit, pas une machine.")))
T.append(temps("Acte 5", "Oui → la carte passe au vert", "6:10 → 6:25",
    dire("V2 — Oui.",
         "V1 — Regardez l'Établi. [la carte passe au vert] L'anneau que vous avez vu se fermer chez Jean-Marc, dans le produit, c'est ça : le Club peut le faire. Il y a une minute, il manquait une pièce. Maintenant, la capacité existe. Pas parce qu'un algorithme a décidé. Parce que Pauline a dit oui."),
    reel("etabli-2-peut.png", "<b>/etabli</b> juste après le Oui : bordure verte, pastille verte « le Club peut le faire », trois coches vertes."),
    montrer("La bordure verte autour de la carte — c'est « l'anneau » du film (D-PRES-2 : pas d'anneau dans le produit, on fait le pont à l'oral).",
            "La pastille verte « le Club peut le faire ».",
            "« transport » a maintenant sa coche verte, comme les deux autres.")))
T.append(temps("Acte 5", "Le reçu", "6:25 → 6:40",
    dire("Et sur son téléphone, elle a un reçu.",
         "[V2 ouvre « Mes consentements (reçus) »]",
         "V2 — Valable. Donné le six octobre. Jusqu'au neuf. Avec une référence. Et je peux le retirer quand je veux.",
         "V1 — Daté. Référencé. Révocable. Ce n'est pas une carte de visite. C'est un engagement — avec un reçu. Comme au pressing, mais pour un minibus."),
    reel("tel-2-recu-carte.png", "Le reçu sur le téléphone de Pauline (zoom). C'est aussi l'image de la slide 18 (D-PRES-3 : écran réel, aucune maquette).", "recu"),
    montrer("« valable » en vert.", "« donné le mardi 06.10 · jusqu'au vendredi 09.10 · référence … » — les trois mots : daté, référencé, révocable.",
            "Le bouton « Retirer mon consentement » — il sert tout de suite après.")))
# ---------- ACTE 6
T.append(temps("Acte 6", "Le retrait", "6:40 → 7:00",
    dire("V1 — Maintenant, la question que tout le monde se pose : et si Pauline change d'avis ?",
         "[V2 appuie sur « Retirer mon consentement »]",
         "V2 — Je retire. Et le téléphone me dit : « Personne ne sera prévenu que c'est vous. »",
         "V1 — L'Établi dit : « un composant n'est plus disponible ». Même pas « transport » : ici, une seule personne a un minibus, le dire, ce serait la montrer du doigt. Pas de « c'est Pauline qui nous a lâchés » à l'apéro. Le système ne nomme jamais, il ne demande jamais pourquoi. Dans un petit club, on peut parfois deviner — on ne vous promet pas l'impossible. Et la demande repart, vers un autre membre — jamais vers elle."),
    "<div class='rangee'>" + reel("tel-2b-retrait.png", "Téléphone : « consentement retiré » + le message en bas.", "tel petit")
    + reel("etabli-3-retrait-carte.png", "<b>/etabli</b> (zoom sur la carte) après le retrait : pastille rouge « un consentement ne vaut plus », et en bas de la carte la phrase sans nom.") + "</div>",
    montrer("Téléphone : le bandeau noir du bas « Consentement retiré. Personne ne sera prévenu que c'est vous. »",
            "Établi : la ligne en bas de la carte « un composant n'est plus disponible » — ni prénom, ni rôle (porté par moins de 3 membres).",
            "Établi : « Recomposition proposée… une demande est adressée aux membres qui peuvent la fournir » = la demande repart."),
    deux=True))
T.append(temps("Acte 6", "Le passe découverte (Foire 2026, seulement si validé au rituel)", "après le retrait, 0:50",
    dire("[onglet /suivi → « Le Club cherche » → « Inviter un contact » sur la demande du minibus ; un juré scanne]",
         "Ce minibus, le Club ne l'a pas trouvé chez lui. Alors il cherche dehors. Ce QR, c'est un passe découverte : trois mois pour essayer le Club sans en être membre. Scannez : vous êtes exposant invité d'Annecy. Votre entreprise, votre métier, votre région — et un reçu, comme Pauline. « Je peux aider. »",
         "Le manque est comblé. À confirmer par le Club — par une personne, pas par une machine. Et votre nom d'entreprise n'est nulle part sur cet écran.",
         "!COUPE PRÉVUE : en retard au reçu (8:40) ou étape non validée → on saute directement à Suivi."),
    "<div class='rangee'>" + reel("tel-4-decouverte.png", "Le téléphone de l'invité : le reçu du passe découverte (90 jours, révocable), la demande, « Je peux aider ».", "tel petit")
    + reel("suivi-2-propose.png", "<b>/suivi</b>, « Le Club cherche » : « un invité propose son aide — à confirmer par le Club ». Aucun nom d'entreprise.") + "</div>",
    deux=True))
T.append(temps("Acte 6", "Suivi (toujours joué)", "20 s",
    dire("[onglet « Suivi »]",
         "Vous nous avez dit que le Club ne sait jamais où en sont les partenariats. Voilà l'écran. Des demandes, des oui, des étapes, des résultats. Jamais un nom : en dessous de trois personnes, l'écran dit « moins de trois ». Et ce sont les chiffres du monde de démonstration — c'est écrit en haut.",
         "Voilà pour l'essai. Maintenant, ce qui est prouvé."),
    reel("suivi-1.png", "<b>/suivi</b> : demandes envoyées, réponses oui « < 3 », invités ayant contribué « < 3 », bandeau « monde de démonstration ». C'est aussi la slide 11S."),
    deux=False))
# ---------- ACTE 7
T.append(temps("Acte 7", "Les preuves", "7:10 → 7:40",
    dire("[carton : « Ce qui est prouvé. Rien de plus. » — puis la slide des trois preuves]",
         "Tout ce que vous venez de voir est testé. Et chaque phrase de ce pitch est dans un registre public, dans notre dépôt : prouvée par un test, mesurée, ou retirée. Oui, retirée. On en a retiré. Ça fait mal, mais ça fait propre.",
         "Trois choses, parce qu'on n'a qu'une minute.",
         "Un. Le reçu. Chaque oui est enregistré, daté. Chaque retrait aussi — anonyme à l'écran, et c'est testé : ni le nom, ni le geste n'apparaissent nulle part.",
         "Deux. Le journal. Si ce serveur meurt pendant que je parle — on l'a fait, plusieurs fois, en le tuant sans prévenir — le monde revient tel quel. Les sessions, le passe du jury, l'endroit où on en était dans la démo. On rejoue. On n'improvise pas."),
    carton("Ce qui est prouvé. Rien de plus.", "slide 12 — carton RÉSULTAT")
    + slide("<div class='trois'><p><b>Le reçu</b> — daté, référencé, révocable.</p><p><b>Le journal</b> — le serveur meurt, le monde revient.</p>"
            "<p><b>Le retrait</b> — un rôle, jamais un nom.</p></div>", "slide 13 — trois preuves, sans icône")))
T.append(temps("Acte 7", "Les chiffres du gel", "7:40 → 8:10",
    dire("Trois. Les chiffres, figés vendredi à dix-huit heures. [GEL] tests. [GEL] parcours complets dans un vrai navigateur, aussi avec le réseau coupé. Sur le cœur du système, [GEL] mutants tués sur [GEL] — chaque survivant classé à la main. Lire ne capte rien : aucune lecture n'écrit. Et un geste sur un téléphone est sur l'écran commun en moins d'une seconde. Mesuré.",
         "Rien de tout ça n'est un argument de vente. C'est ce qui vous permet de croire ce que vous avez vu.",
         "!Les [GEL] se remplissent vendredi soir depuis PREUVES.md, après le tag gel-demo. Ne jamais dire un chiffre qui n'est pas sur la slide."),
    slide("<div class='chiffres'><div><b>[GEL]</b><span>tests</span></div><div><b>[GEL]</b><span>parcours de bout en bout, aussi réseau coupé</span></div>"
          "<div><b>[GEL]/[GEL]</b><span>mutants tués, survivants classés</span></div><div><b>&lt; 1 s</b><span>geste → écran commun (mesuré)</span></div>"
          "<div><b>0</b><span>écriture sans geste</span></div></div>", "slide 14 — reste un gabarit [GEL] jusqu'au gel")))
# ---------- ACTE 8
T.append(temps("Acte 8", "L'IA — sa place", "8:10 → 8:40",
    dire("[slide : « L'IA propose. Les règles vérifient. Le membre décide. »]",
         "Une minute sur l'intelligence artificielle. Parce que c'est un hackathon Apertus, et parce qu'on vous doit la vérité.",
         "Chez nous, l'IA fait une seule chose : elle lit les mots d'un membre et propose une structure. Jamais une décision. Jamais un nom. Jamais un consentement. Entre sa proposition et le membre, il y a des règles qui vérifient tout. Si la proposition est fausse, elle n'arrive jamais à l'écran.",
         "Apertus, c'est la couche IA : suisse, ouverte, servie depuis la Suisse. Elle répond, on l'a vérifié. Et on l'a mesurée sur notre tâche, avec vingt-six cas écrits avant de l'appeler."),
    slide("<div class='trois centre'><p><b>L'IA propose.</b></p><p><b>Les règles vérifient.</b></p><p><b>Le membre décide.</b></p></div>",
          "slide 15 — aucun logo, aucun « propulsé par »")))
T.append(temps("Acte 8", "Une fois sur vingt-six", "8:40 → 9:10",
    dire("Résultat, aujourd'hui : elle propose juste du premier coup… une fois sur vingt-six.",
         "[temps — lentement, en regardant le jury]",
         "Oui. Une. On aurait pu ne pas vous le dire. On préfère vous le dire. Parce que les vingt-cinq autres fois, les règles l'ont arrêtée, et le membre a vu le formulaire. Personne n'a vu une bêtise.",
         "Ça veut dire deux choses. Le produit tient sans l'IA — on a un interrupteur, et l'état du Club est le même, allumée ou éteinte, c'est testé. Et notre prochain chantier est clair : la rendre meilleure, avec ces mêmes vingt-six cas comme juge. Prévu ensuite. Pas aujourd'hui."),
    slide("<span class='mono'>Apertus · swiss-ai/Apertus-v1.5-70B · API d'inférence CSCS</span><b class='geant encre mono'>1 / 26</b>"
          "<span class='sous'>propositions justes du premier coup — 26 cas écrits avant l'appel</span>"
          "<span class='sous petit2'>Interrupteur. Même état du Club, IA allumée ou éteinte — testé.</span>", "slide 16 — mesure du 01.10"),
    montrer("Le lien avec la démo : c'est exactement pourquoi l'IA était éteinte à l'acte 5 — et rien n'a manqué.",
            "L'interrupteur existe aussi à l'écran : bouton « Éteindre l'IA » en haut de l'Établi.")))
# ---------- ACTE 9
T.append(temps("Acte 9", "La carte et le reçu", "9:10 → 9:50",
    dire("[carton : « Et après, maintenant, il se passe quelque chose. » — puis la carte, et le reçu réel à côté]",
         "Vous vous souvenez de cette carte.",
         "La voilà. Et à côté, ce que Pauline a dans la poche en sortant d'ici : un reçu. Daté. Référencé. Qu'elle peut retirer. Même geste de la main. Mais cette fois, il engage."),
    carton("Et après, maintenant, il se passe quelque chose.", "slide 17 — carton REÇU")
    + "<figure><span class='tag apercu'>APERÇU DE SLIDE 18</span><div class='slide clair cote'>"
      "<div class='vide mini'><b>la carte de la slide 1</b><span>photo à venir</span></div>" + img("tel-2-recu-carte.png", "recu-mini") + "</div>"
      "<figcaption>À gauche la carte (même cadrage qu'au début), à droite le reçu RÉEL du téléphone — pas de maquette (D-PRES-3).</figcaption></figure>"))
T.append(temps("Acte 9", "La phrase finale", "9:50 → 10:00",
    dire("Et après ? … Après, maintenant, il se passe quelque chose.",
         "La Foire crée la rencontre. Club Pulse crée l'après.",
         "Si Jean-Marc dit oui, c'est que c'est oui.",
         "[noir — deux secondes — « Merci. »]",
         "!La dernière phrase se DIT, elle ne s'écrit pas sur la slide. Mot pour mot le carton de fin du film. On ne change pas un mot."),
    carton("La Foire crée la rencontre. Club Pulse crée l'après.", "slide 19 — 3 s")
    + slide("", "slide 20 — noir. Puis slide 21 (logo + « Club des Affaires · Foire du Valais ») pendant les questions.", "noir")))

FIL = [("0:00", "Acte 1", "La carte", "photo de carte (à venir) → « Et après ? »"),
       ("0:45", "Acte 2", "Le problème", "cartons + « le vide » + « Oui. »"),
       ("2:00", "Acte 3", "Le film", "film 2:25 — on se tait"),
       ("4:25", "Respiration", "Et après ?", "dernier plan figé → « Et après ? »"),
       ("4:40", "Acte 4", "La révélation", "ÉCRAN RÉEL : Établi « il manque une pièce »"),
       ("5:10", "Acte 5", "La démo", "ÉCRAN RÉEL : téléphone → Oui → Établi vert → reçu"),
       ("6:40", "Acte 6", "Le retrait", "ÉCRAN RÉEL : retrait anonyme (+ QR juré si validé)"),
       ("7:10", "Acte 7", "Les preuves", "trois preuves + chiffres [GEL]"),
       ("8:10", "Acte 8", "L'IA", "trois lignes + « 1 / 26 »"),
       ("9:10", "Acte 9", "La carte et le reçu", "carte + reçu réel → phrase finale → noir")]
fil = "".join(f"<tr><td class='mono'>{a}</td><td><b>{b}</b></td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in FIL)

COUV = f"""<section class='couv'>
<div class='sur'>Club Pulse — Hack VS 2026 · fiches du présentateur</div>
<h1>Ce que je dis,<br>ce que le jury voit</h1>
<p>Le texte simple (03b) à gauche, l'image exacte à l'écran à droite, minute par minute. Pour répéter, comprendre
chaque écran et savoir où pointer du doigt.</p>
<div class='legende'>
<p><span class='tag reel'>ÉCRAN RÉEL</span> capture du vrai produit, prise en rejouant la démo (monde fictif, date simulée, IA éteinte).
C'est ce que le jury verra en direct.</p>
<p><span class='tag apercu'>APERÇU DE SLIDE</span> idée de la slide, pour se repérer. Le deck final est fait côté design (06_SLIDE_CONTENT).</p>
<p><span class='tag avenir'>À VENIR</span> photo de la carte, film : pas encore dans le dépôt, rien n'est inventé ici.</p>
<p><span class='qui v1'>V1</span> parle au jury · <span class='qui v2'>V2</span> tient le téléphone · <span class='geste'>[entre crochets]</span> ne se dit pas ·
<span class='variante'>encadré jaune</span> = note pour vous.</p></div>
<h3>Le fil en une page</h3><table class='fil'>{fil}</table>
<p class='petit'>Généré le {date.today().strftime('%d.%m.%Y')} depuis docs/presentation/03b_SCRIPT_A_DIRE.md et docs/presentation/captures/ (branche claude/modest-bohr-xvk53n).
Chiffres [GEL] : à remplir après le gel de vendredi 18:00.</p></section>"""

PENSE = """<section class='temps pense'><header><span class='acte'>Avant de monter</span><h2>Pense-bête pour V1</h2></header>
<ul class='gros'>
<li><b>Trois sourires qui marchent :</b> la boîte à chaussures (acte 1), « essayez ça dans un comité » et le pressing (acte 5), « ça fait mal, mais ça fait propre » (acte 7). Un seul par acte ; si personne ne rit, on ne remet pas une couche.</li>
<li><b>« Une fois sur vingt-six »</b> se dit lentement, en regardant le jury. C'est le moment le plus honnête du pitch — et celui qu'ils retiendront.</li>
<li><b>On ne dit jamais :</b> « dix secondes », « sans compte » (sauf pour le passe juré), « nos utilisateurs », « propulsé par Apertus », « révolutionnaire », un nom de technologie, un chiffre qui n'est pas sur la slide.</li>
<li><b>La phrase finale ne change pas d'un mot :</b> « Si Jean-Marc dit oui, c'est que c'est oui. »</li>
<li><b>Si un écran plante pendant la démo :</b> les captures de ce document sont aussi les slides de secours 11a–11f (04_DEMO_RUNBOOK § 5). On continue le texte sans s'excuser.</li>
<li><b>« monde fictif », « FICTIF », « date simulée »</b> visibles à l'écran : ce n'est pas un défaut, c'est une preuve d'honnêteté. Ne pas les cacher.</li>
</ul></section>"""

CSS = f"""
@font-face {{ font-family: PJS; src: url(data:font/woff2;base64,{POLICE}) format('woff2'); font-weight: 200 800; }}
@page {{ size: A4 landscape; margin: 11mm 12mm 13mm 12mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: PJS, "DejaVu Sans", sans-serif; color: #141923; font-size: 10.6pt; line-height: 1.42; margin: 0; }}
.mono {{ font-family: "DejaVu Sans Mono", monospace; }}
section {{ page-break-after: always; }}
.couv h1 {{ font-size: 28pt; line-height: 1.05; margin: 3mm 0 2mm; font-weight: 800; }}
.couv .sur {{ color: #CD2128; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; font-size: 9.5pt; }}
.couv > p {{ font-size: 12pt; color: #374151; max-width: 200mm; margin: 0 0 3mm; }}
.legende {{ background: #F3F4F6; border-radius: 3mm; padding: 2mm 4mm; font-size: 9.6pt; }}
.legende p {{ margin: 1.4mm 0; }}
.couv h3 {{ margin: 4mm 0 1.5mm; }}
table.fil {{ border-collapse: collapse; width: 100%; font-size: 9.6pt; }}
.fil td {{ border-bottom: 1px solid #E5E7EB; padding: .7mm 2mm; }}
.petit, .couv p.petit {{ font-size: 8.4pt; color: #6B7280; }}
header {{ display: flex; align-items: baseline; gap: 4mm; border-bottom: 2px solid #CD2128; padding-bottom: 1.5mm; margin-bottom: 3mm; }}
header h2 {{ margin: 0; font-size: 17pt; font-weight: 800; flex: 1; }}
.acte {{ background: #CD2128; color: #fff; font-weight: 800; font-size: 9pt; padding: .6mm 2.5mm; border-radius: 9mm; text-transform: uppercase; letter-spacing: .05em; }}
.horaire {{ font-family: "DejaVu Sans Mono", monospace; color: #6B7280; font-size: 10pt; }}
.grille {{ display: grid; grid-template-columns: 41% 1fr; gap: 6mm; }}
.deux .grille {{ grid-template-columns: 34% 1fr; }}
.lab {{ font-size: 8pt; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: #6B7280; margin-bottom: 1.5mm; }}
.dire p {{ margin: 0 0 2.2mm; }}
.geste {{ color: #6B7280; font-style: italic; font-size: 9.4pt; }}
.qui {{ display: inline-block; font-weight: 800; font-size: 8pt; padding: 0 1.8mm; border-radius: 2mm; margin-right: 1.5mm; color: #fff; }}
.qui.v1 {{ background: #141923; }} .qui.v2 {{ background: #CD2128; }}
.variante {{ background: #FEF9C3; border-left: 3px solid #CA8A04; padding: 1.5mm 2.5mm; font-size: 9.3pt; }}
ol.film {{ margin: 0 0 2mm 5mm; padding: 0; font-size: 9.8pt; }} ol.film li {{ margin-bottom: 1mm; }}
.doigt {{ background: #ECFDF5; border-left: 3px solid #16A34A; padding: 1.5mm 3mm; margin-top: 3mm; font-size: 9.2pt; }}
.doigt ul {{ margin: 1mm 0 0 4mm; padding: 0; }} .doigt li {{ margin-bottom: .8mm; }}
figure {{ margin: 0 0 3mm; position: relative; }}
figcaption {{ font-size: 8.4pt; color: #4B5563; margin-top: 1mm; }}
.tag {{ display: inline-block; font-size: 7.2pt; font-weight: 800; letter-spacing: .08em; padding: .3mm 2mm; border-radius: 1.5mm; margin-bottom: 1mm; }}
.tag.reel {{ background: #16A34A; color: #fff; }} .tag.apercu {{ background: #E5E7EB; color: #374151; }}
.tag.avenir {{ background: #fff; color: #6B7280; border: 1px dashed #9CA3AF; }}
img.ecran {{ width: 100%; max-height: 112mm; object-fit: contain; object-position: left top; border: 1px solid #D1D5DB; border-radius: 1.5mm; display: block; }}
img.tel {{ height: 150mm; border: 1px solid #D1D5DB; border-radius: 4mm; display: block; }}
img.tel.petit {{ height: 132mm; }}
img.recu {{ width: 112mm; border: 1px solid #D1D5DB; border-radius: 3mm; display: block; }}
.rangee {{ display: flex; gap: 4mm; align-items: flex-start; }} .rangee figure:first-child {{ flex: 0 0 auto; max-width: 62mm; }} .rangee figure:last-child {{ flex: 1 1 0; min-width: 95mm; }} .rangee figure:last-child img.ecran {{ max-height: 150mm; }}
.slide {{ aspect-ratio: 16/9; width: 100%; max-height: 74mm; border-radius: 2mm; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 6mm; border: 1px solid #D1D5DB; }}
.voit .slide + figcaption {{ }}
.voit figure:has(+ figure) .slide, .voit figure + figure .slide {{ max-height: 58mm; padding: 3mm; }}
.voit figure:has(+ figure) .slide.noir b {{ font-size: 17pt; }}
.voit figure:has(+ figure img.ecran) .slide {{ max-height: 34mm; }}
.voit figure + figure img.ecran {{ max-height: 104mm; }}
.voit figure:has(+ figure) .slide.vide {{ max-height: 70mm; }}
.slide.noir {{ background: #000; color: #fff; }}
.slide.noir b {{ font-size: 21pt; font-weight: 800; line-height: 1.2; }}
.slide.clair {{ background: #fff; }}
.slide.vide {{ background: repeating-linear-gradient(45deg, #F9FAFB, #F9FAFB 4mm, #F3F4F6 4mm, #F3F4F6 8mm); border: 2px dashed #9CA3AF; color: #4B5563; gap: 2mm; }}
.slide.vide b {{ font-size: 13pt; }} .slide.vide span {{ font-size: 9.4pt; max-width: 120mm; }}
.geant {{ font-size: 40pt !important; font-weight: 800; }} .encre {{ color: #141923; }}
.sous {{ color: #6B7280; font-size: 10pt; margin-top: 2mm; }} .petit2 {{ font-size: 8.6pt; }}
.frise {{ display: flex; align-items: center; width: 100%; gap: 3mm; font-weight: 800; font-size: 11pt; }}
.frise i {{ flex: 1; border-top: 2px solid #141923; }}
.trois p {{ font-size: 13pt; margin: 2mm 0; text-align: left; }} .trois.centre p {{ text-align: center; font-size: 17pt; }}
.chiffres {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 3mm; width: 100%; }}
.chiffres b {{ display: block; font-family: "DejaVu Sans Mono", monospace; font-size: 15pt; }}
.chiffres span {{ font-size: 7.6pt; color: #4B5563; }}
.slide.cote {{ flex-direction: row; gap: 5mm; max-height: none !important; aspect-ratio: auto; padding: 4mm; }}
.vide.mini {{ width: 45%; aspect-ratio: 85/55; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #9CA3AF; border-radius: 2mm; background: #F9FAFB; font-size: 9pt; }}
img.recu-mini {{ width: 48%; border: 1px solid #D1D5DB; border-radius: 2mm; }}
.pense ul.gros {{ font-size: 12pt; line-height: 1.5; }} .pense li {{ margin-bottom: 3mm; }}
"""

page = f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{COUV}{''.join(T)}{PENSE}</body></html>"
(SORTIE.with_suffix(".html")).write_text(page, encoding="utf-8")
with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = nav.new_page()
    pg.set_content(page, wait_until="load")
    pg.evaluate("document.fonts.ready")
    pg.pdf(path=str(SORTIE), landscape=True, format="A4", print_background=True, prefer_css_page_size=True,
           display_header_footer=True, header_template="<span></span>",
           footer_template="<div style='font-size:7pt;color:#9CA3AF;width:100%;text-align:center;font-family:DejaVu Sans'>"
                           "Club Pulse — fiches du présentateur · <span class='pageNumber'></span> / <span class='totalPages'></span></div>")
    nav.close()
print(SORTIE)
