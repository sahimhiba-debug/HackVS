// INTERFACE EN ALLEMAND du téléphone (P3 n°5) — selon la langue préférée du membre (« Où je suis, ma langue » : de),
// ou ?lang=de. TRADUCTION À RELIRE PAR UN GERMANOPHONE : le bandeau le dit sur chaque écran.
// Couche de traduction de l'INTERFACE seulement (libellés, boutons, titres, messages) : les données du Club (titres de
// capacités, textes des membres) restent dans la langue où elles ont été écrites. Texte exact → texte exact ; ce qui
// n'est pas dans le dictionnaire reste en français (jamais une traduction inventée à la volée).
export const DE = {
  "Mes actions": "Meine Aktionen", "Agir à plusieurs": "Gemeinsam handeln", "Proposer un essai": "Einen Versuch vorschlagen",
  "Souvenirs et accords": "Erinnerungen und Zusagen", "Demandes": "Anfragen", "Demandes du Club": "Anfragen des Clubs",
  "Oui": "Ja", "Non": "Nein", "Pas cette fois": "Diesmal nicht", "Je peux aider": "Ich kann helfen",
  "Aucune demande pour vous en ce moment.": "Im Moment gibt es keine Anfrage für Sie.",
  "Mes données": "Meine Daten", "Mes consentements": "Meine Einwilligungen", "Mes consentements (reçus)": "Meine Einwilligungen (Belege)",
  "Mes données : ce que le Club sait de moi, pourquoi, jusqu'à quand": "Meine Daten: was der Club über mich weiss, warum, bis wann",
  "Consentement retiré. Personne ne sera prévenu que c'est vous.": "Einwilligung zurückgezogen. Niemand erfährt, dass Sie es waren.",
  "Choix enregistré.": "Auswahl gespeichert.", "Enregistré.": "Gespeichert.", "Enregistrer": "Speichern", "Confirmé.": "Bestätigt.",
  "Je confirme": "Ich bestätige", "Continuer": "Weiter", "Chargement…": "Wird geladen…",
  "Comprendre ma demande": "Meine Anfrage verstehen", "Chercher une proposition": "Einen Vorschlag suchen",
  "Votre besoin": "Ihr Bedarf", "Ce que vous voulez réaliser": "Was Sie erreichen möchten",
  "Ce qui comptera comme réalisé": "Was als erreicht gilt", "Quand êtes-vous disponible ?": "Wann sind Sie verfügbar?",
  "Pour qu'on vous dise oui plus facilement :": "Damit man Ihnen leichter zusagt:",
  "Où je suis, ma langue": "Wo ich bin, meine Sprache", "Ma carte devient mon profil": "Meine Visitenkarte wird mein Profil",
  "Photographier ma carte": "Meine Visitenkarte fotografieren", "Sans photo : le formulaire": "Ohne Foto: das Formular",
  "Hors ligne : les actions attendront le réseau.": "Offline: Aktionen warten auf das Netz.",
  "De retour en ligne.": "Wieder online.", "Le serveur ne répond pas : réessayez.": "Der Server antwortet nicht: bitte erneut versuchen.",
  "Impossible d'afficher cet écran": "Dieser Bildschirm kann nicht angezeigt werden",
  "Monde de démonstration : personnes, entreprises et dates inventées": "Demo-Welt: erfundene Personen, Unternehmen und Daten",
  "Démonstration : membres et entreprises fictifs.": "Demo: fiktive Mitglieder und Unternehmen.",
  "Activez votre compte du Club": "Aktivieren Sie Ihr Club-Konto", "Code d'invitation": "Einladungscode",
  "Note privée": "Private Notiz", "Garder cette note": "Diese Notiz behalten", "Note gardée, privée.": "Notiz gespeichert, privat.",
  "Noté. Personne d'autre ne le saura.": "Notiert. Niemand sonst erfährt es.",
  "Mes réponses aux demandes": "Meine Antworten auf Anfragen", "Mes accords": "Meine Zusagen", "Aucun accord.": "Keine Zusage.",
  "Ce que j'ai déclaré": "Was ich angegeben habe", "Ce qui sera partagé": "Was geteilt wird", "Pourquoi": "Warum",
  "Historique": "Verlauf", "Navigation": "Navigation",
};
export const BANDEAU = "Übersetzung — von einer deutschsprachigen Person zu prüfen · traduction à relire par un germanophone";

export function langueVoulue(declaree) {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "de" || q === "fr") return q;
  return declaree === "de" ? "de" : "fr";
}

function traduireNoeud(n) {
  if (n.nodeType === Node.TEXT_NODE) {
    const t = n.nodeValue.trim();
    if (t && DE[t]) n.nodeValue = n.nodeValue.replace(t, DE[t]);
    return;
  }
  if (n.nodeType !== Node.ELEMENT_NODE) return;
  for (const a of ["placeholder", "aria-label", "title"]) { const v = n.getAttribute(a); if (v && DE[v]) n.setAttribute(a, DE[v]); }
  for (const c of n.childNodes) traduireNoeud(c);
}

export function activer() {
  document.documentElement.lang = "de";
  traduireNoeud(document.body);
  new MutationObserver((ms) => ms.forEach((m) => m.addedNodes.forEach(traduireNoeud))).observe(document.body, { childList: true, subtree: true });
  if (!document.querySelector("[data-role=traduction]")) {
    const b = document.createElement("p");
    b.dataset.role = "traduction";
    b.textContent = BANDEAU;
    b.style.cssText = "margin:0;padding:6px 12px;font-size:12px;background:#FBF0DC;color:#8a5a00;text-align:center";
    document.body.prepend(b);
  }
}
