// Vue « Nouveau besoin » : texte → critères (progressifs puis validés) → aperçu → visibilité → enregistrement.
import { $, api, emettre, etat, h, occupe, libre, toast, transition, prenom } from "./outils.js";
import { aUneCompetence, blocComparaison, blocResultats, editeurCriteres, empreinte, surligner } from "./composants.js";
import { ouvrirMessage } from "./dialogue.js";

const EXEMPLES = [
  ["Transport frigorifique vers Zurich", "On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique qui livre Zurich deux fois par semaine, idéalement germanophone, et pas un concurrent."],
  ["Négation", "Je ne cherche pas un installateur frigorifique mais un transporteur frigorifique pour livrer Genève."],
  ["Mot ambigu", "Je cherche quelqu'un pour la sécurité."],
  ["Hors catalogue", "Je cherche un apiculteur pour polliniser mes vergers d'abricotiers."],
  ["Aucune bonne réponse", "Nous cherchons quelqu'un pour nous accompagner vers la certification ISO 27001."],
];

const s = { texte: "", besoin: null, final: false, provisoires: [], apercu: null, empreinteApercu: null, besoinId: null, flux: null };

export function vueNouveau() {
  const racine = $("#vue-nouveau");
  racine.replaceChildren(
    h("section", { class: "bloc", "aria-labelledby": "t-besoin" },
      h("p", { class: "surtitre", id: "vous-etes" }),
      h("h1", { id: "t-besoin" }, "Que cherchez-vous", h("br"), "cette semaine ?"),
      h("label", { class: "sr", for: "texte" }, "Votre besoin"),
      h("div", { class: "saisie" }, h("textarea", { id: "texte", rows: "3", maxlength: "1500",
        placeholder: "Ex. : Je cherche un transporteur frigorifique qui livre Zurich deux fois par semaine…" })),
      h("div", { class: "exemples", "aria-label": "Exemples" }, EXEMPLES.map(([l, t]) =>
        h("button", { class: "pilule", type: "button", onclick: () => { $("#texte").value = t; $("#texte").focus(); } }, l))),
      h("div", { class: "actions" },
        h("button", { class: "btn primaire", id: "btn-analyser", type: "button", onclick: analyser }, "Analyser mon besoin"),
        h("span", { class: "aide", id: "aide-analyse" }))),
    h("section", { class: "bloc", id: "bloc-criteres", hidden: true, "aria-labelledby": "t-criteres" },
      h("h2", { id: "t-criteres" }, "Ce que j'ai compris"),
      h("div", { id: "zone-surligne" }), h("div", { id: "zone-editeur" })),
    h("section", { class: "bloc", id: "bloc-apercu", hidden: true, "aria-labelledby": "t-apercu" },
      h("h2", { id: "t-apercu" }, "Qui peut vous aider"),
      h("div", { class: "resultats", id: "zone-apercu", "aria-live": "polite" })),
    h("section", { class: "bloc", id: "bloc-visibilite", hidden: true, "aria-labelledby": "t-visibilite" },
      h("h2", { id: "t-visibilite" }, "Et maintenant ?"),
      h("div", { class: "visibilite" },
        h("label", { class: "bascule" }, h("input", { type: "radio", name: "visibilite", value: "publie", checked: true }),
          h("span", {}, h("strong", {}, "Publier dans la Bourse du Club"),
            h("small", {}, "Seuls les membres qui correspondent et acceptent les introductions voient votre besoin ; ils peuvent vous proposer leur aide."))),
        h("label", { class: "bascule" }, h("input", { type: "radio", name: "visibilite", value: "prive" }),
          h("span", {}, h("strong", {}, "Garder privé"), h("small", {}, "Vous sollicitez vous-même les membres proposés ci-dessus."))),
        h("label", { class: "bascule" }, h("input", { type: "checkbox", id: "anonyme" }),
          h("span", {}, "Masquer mon nom dans la Bourse", h("small", {}, "Votre nom n'est révélé qu'à la personne dont vous acceptez la proposition.")))),
      h("div", { class: "actions" },
        h("button", { class: "btn rouge", id: "btn-enregistrer", type: "button", onclick: enregistrer }, "Publier dans la Bourse"))));
  racine.querySelectorAll("input[name=visibilite]").forEach((r) => r.addEventListener("change", majBoutonEnregistrer));
  $("#texte").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) analyser(); });
  installerMicro();
  majEntete();
}

export function majEntete() {
  const m = etat.moi;
  if (!m || !$("#vous-etes")) return;
  $("#vous-etes").textContent = `${m.nom} · ${m.entreprise}, ${m.commune}` + (etat.config.donnees_fictives ? " · personnage fictif" : "");
  $("#aide-analyse").textContent = etat.config.analyseur_claude_disponible
    ? "Votre texte est analysé par Claude, puis chaque critère est vérifié par le code."
    : "Analyse locale par règles : rien ne quitte cette machine.";
}

function majBoutonEnregistrer() {
  const pub = document.querySelector("input[name=visibilite]:checked")?.value === "publie";
  $("#btn-enregistrer").textContent = s.besoinId ? "Voir ce besoin" : pub ? "Publier dans la Bourse" : "Enregistrer (privé)";
  $("#anonyme").disabled = !pub;
}

// ------------------------------------------------------------------ analyse (flux)
async function analyser() {
  const texte = $("#texte").value.trim();
  if (!texte) { toast("Décrivez votre besoin en une ou deux phrases."); $("#texte").focus(); return; }
  const b = $("#btn-analyser");
  occupe(b, etat.config.analyseur_claude_disponible ? "Claude analyse…" : "Analyse…");
  Object.assign(s, { texte, besoin: null, final: false, provisoires: [], apercu: null, empreinteApercu: null, besoinId: null });
  ["#bloc-apercu", "#bloc-visibilite"].forEach((x) => ($(x).hidden = true));
  $("#bloc-criteres").hidden = false;
  rendreCriteres();
  try {
    await analyserFlux(texte);
  } catch {
    try {  // repli : appel simple
      const r = await api("/api/analyser", { corps: { texte } });
      s.besoin = r.besoin; s.final = true;
    } catch (e) { toast(e.message, "erreur"); }
  } finally { libre(b); }
  if (!s.final) return;
  transition(() => rendreCriteres());
  $("#bloc-criteres").scrollIntoView({ behavior: "smooth", block: "start" });
  if (aUneCompetence(s.besoin)) apercu();
}

function analyserFlux(texte) {
  return new Promise((resolve, reject) => {
    s.flux?.close();
    const es = new EventSource(`/api/analyser/flux?texte=${encodeURIComponent(texte)}`);
    s.flux = es;
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data);
      if (ev.type === "provisoire") { s.provisoires.push(ev.critere); rendreCriteres(); }
      else if (ev.type === "final") { s.besoin = ev.besoin; s.final = true; s.provisoires = []; es.close(); resolve(); }
    };
    es.onerror = () => { es.close(); s.final ? resolve() : reject(new Error("flux interrompu")); };
  });
}

function rendreCriteres() {
  $("#zone-surligne").replaceChildren(surligner(s.texte, s.besoin, s.provisoires));
  if (!s.final) {
    $("#zone-editeur").replaceChildren(
      s.provisoires.length ? editeurCriteres({ criteres: [], exclusions: [] }, { lectureSeule: true, provisoires: s.provisoires }) : h("div", { class: "squelette" }),
      h("p", { class: "aide" }, h("span", { class: "chargement" }, "Critères provisoires : en attente de vérification par le code.")));
    return;
  }
  $("#zone-editeur").replaceChildren(
    editeurCriteres(s.besoin, { onChange: () => { marquerObsolete(); } }),
    h("div", { class: "actions" },
      h("button", { class: "btn primaire", id: "btn-apercu", type: "button", onclick: apercu }, "Trouver qui peut m'aider"),
      s.besoin.analyseur !== "regles" ? h("span", { class: "aide" }, `Analyse : ${LIBELLES_ANALYSEUR[s.besoin.analyseur] || s.besoin.analyseur}`) : null));
}

// ------------------------------------------------------------------ aperçu des correspondances
function marquerObsolete() {
  const zone = $("#zone-apercu");
  if (!s.apercu || empreinte(s.besoin) === s.empreinteApercu) { zone.classList.remove("obsolete"); zone.querySelector(".bandeau-obsolete")?.remove(); return; }
  if (zone.classList.contains("obsolete")) return;
  zone.classList.add("obsolete");
  zone.prepend(h("div", { class: "bandeau-obsolete", role: "status" },
    "Critères modifiés : ces résultats ne correspondent plus à votre besoin.",
    h("button", { class: "btn petit", type: "button", onclick: apercu }, "Actualiser")));
}

const LIBELLES_ANALYSEUR = {
  "regles+semantique": "règles + IA locale", "regles+semantique (question)": "règles + IA locale (à confirmer par vous)",
  claude: "Claude, vérifié par le code", apertus: "Apertus, vérifié par le code", "regles (repli)": "règles (modèle indisponible)",
};

async function apercu() {
  if (!aUneCompetence(s.besoin)) { toast("Choisissez d'abord la compétence recherchée."); return; }
  const zone = $("#zone-apercu");
  $("#bloc-apercu").hidden = false;
  zone.classList.remove("obsolete");
  zone.replaceChildren(h("div", { class: "squelette" }));
  try {
    const cle = empreinte(s.besoin);
    const res = await api("/api/rechercher", { corps: { besoin: s.besoin } });
    s.apercu = res; s.empreinteApercu = cle;
    transition(() => {
      zone.replaceChildren(blocResultats(res, { action: (sug) => h("button", { class: "btn primaire", type: "button",
        onclick: () => demander(sug) }, `Solliciter ${prenom(sug.profil.nom)}`), besoin: s.besoin }), blocComparaison(s.besoin));
    });
    $("#bloc-visibilite").hidden = false;
    majBoutonEnregistrer();
    $("#bloc-apercu").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) { zone.replaceChildren(h("div", { class: "erreur-bloc", role: "alert" }, e.message)); }
}

// ------------------------------------------------------------------ enregistrement & demande
async function sauver(publier) {
  if (s.besoinId) return s.besoinId;
  const anonyme = publier && $("#anonyme").checked;
  const b = await api("/api/besoins", { corps: { besoin: s.besoin, publier, anonyme } });
  s.besoinId = b.id;
  emettre("rafraichir");
  return b.id;
}

async function enregistrer() {
  if (s.besoinId) { emettre("ouvrir-besoin", s.besoinId); return; }
  if (s.apercu && empreinte(s.besoin) !== s.empreinteApercu) { toast("Actualisez d'abord les résultats : les critères ont changé."); return; }
  const pub = document.querySelector("input[name=visibilite]:checked").value === "publie";
  const btn = $("#btn-enregistrer");
  occupe(btn, pub ? "Publication…" : "Enregistrement…");
  try {
    const id = await sauver(pub);
    toast(pub ? "Besoin publié : les membres qui correspondent le voient dans leur Bourse." : "Besoin enregistré (privé).", "info");
    emettre("ouvrir-besoin", id);
    reinitialiserFormulaire();
  } catch (e) { toast(e.message, "erreur"); libre(btn); }
}

async function demander(sug) {
  if (empreinte(s.besoin) !== s.empreinteApercu) { toast("Actualisez d'abord les résultats."); return; }
  try {
    const id = await sauver(false);
    const ok = await ouvrirMessage({
      titre: `Demander une introduction à ${sug.profil.nom}`,
      consentement: `${prenom(sug.profil.nom)} reçoit votre demande et choisit d'accepter ou non. Vos coordonnées ne sont partagées qu'après son accord.`,
      brouillonUrl: `/api/relations/brouillon?besoin_id=${id}&cible_id=${sug.profil.id}`,
      libelleEnvoi: etat.config.donnees_fictives ? "Envoyer (simulation)" : "Envoyer",
      envoyer: (message) => api("/api/relations", { corps: { besoin_id: id, cible_id: sug.profil.id, message } }),
    });
    if (ok) { toast("Demande enregistrée. Suivez-la dans l'onglet Suivi.", "info"); emettre("rafraichir"); emettre("ouvrir-besoin", id); reinitialiserFormulaire(); }
  } catch (e) { toast(e.message, "erreur"); }
}

function reinitialiserFormulaire() {
  Object.assign(s, { texte: "", besoin: null, final: false, provisoires: [], apercu: null, empreinteApercu: null, besoinId: null });
  if ($("#texte")) $("#texte").value = "";
  ["#bloc-criteres", "#bloc-apercu", "#bloc-visibilite"].forEach((x) => $(x) && ($(x).hidden = true));
}

// ------------------------------------------------------------------ dictée (amélioration progressive)
function installerMicro() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  const zone = $("#texte");
  const rec = new SR(); rec.lang = "fr-CH"; rec.interimResults = true; rec.continuous = false;
  const btn = h("button", { class: "micro", type: "button", "aria-pressed": "false", "aria-label": "Dicter votre besoin",
    title: "Dicter (reconnaissance vocale du navigateur ; Chrome envoie l'audio à ses serveurs)" });
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>';
  let base = "";
  btn.addEventListener("click", () => {
    if (btn.getAttribute("aria-pressed") === "true") { rec.stop(); return; }
    base = zone.value ? zone.value.trim() + " " : "";
    try { rec.start(); btn.setAttribute("aria-pressed", "true"); } catch { /* déjà actif */ }
  });
  rec.onresult = (ev) => { zone.value = base + Array.from(ev.results).map((r) => r[0].transcript).join(""); };
  rec.onend = () => btn.setAttribute("aria-pressed", "false");
  rec.onerror = (ev) => { btn.setAttribute("aria-pressed", "false"); toast(`Dictée indisponible (${ev.error}). Tapez votre besoin.`, "erreur"); };
  zone.parentElement.append(btn);
}
