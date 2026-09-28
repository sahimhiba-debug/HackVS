// Le Fil du Club : interface du prototype. JavaScript natif, sans dépendance ni build.
// Tout le contenu issu des données est inséré via textContent (jamais innerHTML).
"use strict";

const $ = (sel) => document.querySelector(sel);
const etat = { config: null, besoin: null, resultat: null, cible: null, telemetrie: null };

const EXEMPLES = [
  ["Transport frigorifique vers Zurich",
   "On lance nos jus d'abricot en Suisse alémanique. Je cherche un transporteur frigorifique qui livre Zurich deux fois par semaine, idéalement germanophone, et pas un concurrent."],
  ["Sécurité pour notre stand",
   "Pour la prochaine Foire, il nous faut de la sécurité pour notre stand le soir."],
  ["Mot ambigu",
   "Je cherche quelqu'un pour la sécurité."],
  ["Certification ISO 27001",
   "Nous cherchons quelqu'un pour nous accompagner vers la certification ISO 27001 d'ici l'été prochain."],
];

const ETAPES_FRISE = [
  ["demandee", "Demandée"], ["acceptee", "Acceptée"], ["rencontre_planifiee", "Rencontre planifiée"],
  ["rencontre_faite", "Rencontre faite"], ["cloturee", "Résultat noté"],
];
const RESULTATS = { utile: "Utile", affaire_en_cours: "Affaire en cours", pas_pertinent: "Pas pertinent" };
const PROVENANCE = {
  offre: "déclaré dans son offre", presentation: "déduit de sa présentation",
  langues: "langues du profil", zones_service: "zones desservies du profil", recherche: "ce qu'elle/il recherche",
};
const LANGUES = { fr: "français", de: "allemand", en: "anglais", it: "italien" };

// ---------------------------------------------------------------- utilitaires
function h(tag, attrs = {}, ...enfants) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const e of enfants.flat()) {
    if (e === null || e === undefined || e === false) continue;
    el.append(e instanceof Node ? e : document.createTextNode(String(e)));
  }
  return el;
}

async function api(chemin, corps) {
  const rep = await fetch(chemin, corps === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps),
  });
  const data = await rep.json().catch(() => ({}));
  if (!rep.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Erreur ${rep.status}`);
  return data;
}

let minuteurToast;
function toast(msg, erreur = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (erreur ? " erreur" : ""); t.hidden = false;
  clearTimeout(minuteurToast); minuteurToast = setTimeout(() => (t.hidden = true), 4200);
}

function transition(fn) {
  if (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.startViewTransition(fn);
  } else fn();
}

function montrer(id) {
  const b = $(id);
  if (b.hidden) { b.hidden = false; b.classList.remove("entre"); void b.offsetWidth; b.classList.add("entre"); }
}

function etape(n) {
  document.querySelectorAll(".etapes li").forEach((li) => {
    const k = Number(li.dataset.etape);
    li.classList.toggle("active", k === n);
    li.classList.toggle("faite", k < n);
    if (k === n) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
  });
}

function occupe(bouton, texte) {
  bouton.disabled = true; bouton.dataset.libelle = bouton.textContent;
  bouton.replaceChildren(h("span", { class: "chargement" }, texte));
}
function libre(bouton) { bouton.disabled = false; bouton.textContent = bouton.dataset.libelle; }

// ---------------------------------------------------------------- démarrage
async function init() {
  try {
    etat.config = await api("/api/etat");
  } catch (e) {
    toast("Serveur injoignable : lancez l'API (voir README).", true); return;
  }
  const c = etat.config;
  const badges = $("#badges");
  if (c.donnees_fictives) {
    badges.append(h("span", { class: "badge demo" }, "Démo · données fictives"));
    $("#bandeau-demo").hidden = false;
  } else badges.append(h("span", { class: "badge live" }, "Mode réel"));
  badges.append(c.analyseur_claude_disponible
    ? h("span", { class: "badge live", title: "Le texte est analysé en direct par Claude, puis validé par le code." }, "Analyse : Claude en direct")
    : h("span", { class: "badge local", title: "Analyse par règles locales, sans réseau ni IA générative." }, "Analyse : règles locales"));
  $("#pied-mode").textContent = c.donnees_fictives ? "données fictives, aucun message réel envoyé" : "mode réel";
  document.querySelectorAll(".demo-seul").forEach((e) => (e.hidden = !c.donnees_fictives));
  if (c.utilisateur) {
    $("#vous").textContent = `Vous êtes ${c.utilisateur.nom} · ${c.utilisateur.entreprise}, ${c.utilisateur.commune}` +
      (c.donnees_fictives ? " (personnage fictif)" : "");
  }
  $("#aide-analyse").textContent = c.analyseur_claude_disponible
    ? "Votre texte est envoyé à Claude, puis chaque critère est vérifié par le code."
    : "Analyse locale : rien ne quitte cette machine.";

  for (const [libelle, texte] of EXEMPLES) {
    $("#exemples").append(h("button", { class: "exemple", type: "button", onclick: () => { $("#texte").value = texte; $("#texte").focus(); } }, libelle));
  }
  const sel = $("#ajout-concept");
  for (const k of c.concepts) sel.append(h("option", { value: k.valeur }, k.libelle));
  sel.addEventListener("change", () => {
    if (!sel.value || !etat.besoin) return;
    const k = c.concepts.find((x) => x.valeur === sel.value);
    if (!etat.besoin.criteres.some((x) => x.type === "expertise" && x.valeur === k.valeur)) {
      const premier = !etat.besoin.criteres.some((x) => x.type === "expertise");
      etat.besoin.criteres.push({ type: "expertise", valeur: k.valeur, libelle: k.libelle, obligatoire: premier, extrait: null, note: "ajouté par vous" });
    }
    sel.value = ""; rendreCriteres();
  });
  $("#opt-concurrents").addEventListener("change", (e) => { if (etat.besoin) etat.besoin.exclure_concurrents = e.target.checked; });
  $("#opt-exposants").addEventListener("change", (e) => { if (etat.besoin) etat.besoin.inclure_exposants = e.target.checked; });

  $("#btn-analyser").addEventListener("click", analyser);
  $("#texte").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) analyser(); });
  $("#btn-rechercher").addEventListener("click", rechercher);
  $("#btn-envoyer").addEventListener("click", envoyer);
  $("#btn-annuler-intro").addEventListener("click", () => { $("#bloc-intro").hidden = true; etape(3); $("#bloc-resultats").scrollIntoView({ behavior: "smooth" }); });
  $("#comparaison").addEventListener("toggle", (e) => { if (e.target.open) comparer(); });
  $("#btn-reset").addEventListener("click", reinitialiser);
  installerMicro();
  etape(1);
  rendreSuivi();
}

// Saisie vocale : amélioration progressive, uniquement si le navigateur la propose.
function installerMicro() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const zone = $("#texte");
  const enveloppe = h("div", { class: "saisie" });
  zone.replaceWith(enveloppe); enveloppe.append(zone);
  if (!SR) return;
  const rec = new SR(); rec.lang = "fr-CH"; rec.interimResults = true; rec.continuous = false;
  const btn = h("button", { class: "micro", type: "button", "aria-pressed": "false", "aria-label": "Dicter votre besoin",
    title: "Dicter (reconnaissance vocale du navigateur, peut nécessiter une connexion)" });
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>';
  let base = "";
  btn.addEventListener("click", () => {
    if (btn.getAttribute("aria-pressed") === "true") { rec.stop(); return; }
    base = zone.value ? zone.value.trim() + " " : "";
    try { rec.start(); btn.setAttribute("aria-pressed", "true"); } catch { /* déjà actif */ }
  });
  rec.onresult = (ev) => { zone.value = base + Array.from(ev.results).map((r) => r[0].transcript).join(""); };
  rec.onend = () => btn.setAttribute("aria-pressed", "false");
  rec.onerror = (ev) => { btn.setAttribute("aria-pressed", "false"); toast(`Dictée indisponible (${ev.error}). Tapez votre besoin.`, true); };
  enveloppe.append(btn);
}

// ---------------------------------------------------------------- étape 2
async function analyser() {
  const texte = $("#texte").value.trim();
  if (!texte) { toast("Décrivez votre besoin en une ou deux phrases."); $("#texte").focus(); return; }
  const b = $("#btn-analyser");
  occupe(b, etat.config.analyseur_claude_disponible ? "Claude analyse votre besoin…" : "Analyse…");
  try {
    const r = await api("/api/analyser", { texte });
    etat.besoin = r.besoin; etat.telemetrie = r.telemetrie;
    ["#bloc-resultats", "#bloc-intro"].forEach((s) => ($(s).hidden = true));
    transition(() => { rendreCriteres(); montrer("#bloc-criteres"); });
    etape(2);
    $("#bloc-criteres").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) { toast(e.message, true); }
  finally { libre(b); }
}

function surligner(texte, criteres) {
  const p = $("#texte-surligne"); p.replaceChildren();
  const plages = [];
  for (const c of criteres) {
    if (!c.extrait) continue;
    const i = texte.indexOf(c.extrait);
    if (i >= 0 && !plages.some(([d, f]) => i < f && d < i + c.extrait.length)) plages.push([i, i + c.extrait.length, c]);
  }
  plages.sort((a, b) => a[0] - b[0]);
  let pos = 0;
  for (const [d, f, c] of plages) {
    p.append(texte.slice(pos, d), h("mark", { class: c.type, title: c.libelle }, texte.slice(d, f)));
    pos = f;
  }
  p.append(texte.slice(pos));
}

function rendreCriteres() {
  const b = etat.besoin;
  surligner(b.texte, b.criteres);
  const ul = $("#criteres"); ul.replaceChildren();
  const principale = b.criteres.find((c) => c.type === "expertise" && c.obligatoire);
  b.criteres.forEach((c, i) => {
    const type = { expertise: "Compétence recherchée", langue: "Langue", zone: "Zone à desservir" }[c.type];
    ul.append(h("li", { class: "critere" + (c === principale ? " principal" : ""), style: `animation-delay:${i * 60}ms` },
      h("span", { class: "type" }, c === principale ? "Besoin principal" : type),
      h("span", { class: "valeur" }, c.libelle),
      c.extrait ? h("span", { class: "source" }, `d'après « ${c.extrait} »`) : null,
      c.note ? h("span", { class: "note" }, c.note) : null,
      h("span", { class: "ligne" },
        h("button", {
          class: "pastille " + (c.obligatoire ? "oblig" : "souhait"), type: "button", "aria-pressed": String(c.obligatoire),
          title: "Obligatoire : les profils qui ne remplissent pas ce critère sont écartés.",
          onclick: () => { c.obligatoire = !c.obligatoire; rendreCriteres(); },
        }, c.obligatoire ? "Obligatoire" : "Souhaité"),
        h("button", { class: "retirer", type: "button", "aria-label": `Retirer ${c.libelle}`,
          onclick: () => { b.criteres.splice(i, 1); rendreCriteres(); } }, "×"))));
  });

  const amb = $("#ambiguites"); amb.replaceChildren();
  for (const a of b.ambiguites || []) {
    amb.append(h("div", { class: "question" },
      h("p", {}, `« ${a.extrait} » : que voulez-vous dire ?`),
      h("div", { class: "choix" }, a.options.map((o) => h("button", { class: "exemple", type: "button", onclick: () => {
        // Le sens choisi devient le besoin principal ; les autres compétences passent en « souhaité ».
        b.criteres.forEach((x) => { if (x.type === "expertise") x.obligatoire = false; });
        b.criteres.unshift({ type: "expertise", valeur: o.valeur, libelle: o.libelle, obligatoire: true, extrait: a.extrait, note: "précisé par vous" });
        b.ambiguites = b.ambiguites.filter((x) => x !== a);
        rendreCriteres();
      } }, o.libelle)))));
  }
  $("#opt-concurrents").checked = !!b.exclure_concurrents;
  $("#opt-exposants").checked = !!b.inclure_exposants;
  $("#contexte").textContent = b.contexte && b.contexte.length
    ? "Noté, mais non vérifiable dans les profils : " + b.contexte.join(" · ") : "";
  const av = $("#avertissements"); av.replaceChildren(...(b.avertissements || []).map((a) => h("li", {}, a)));
}

// ---------------------------------------------------------------- étape 3
async function rechercher() {
  const b = $("#btn-rechercher");
  if (!etat.besoin.criteres.some((c) => c.type === "expertise")) {
    toast("Ajoutez au moins une compétence recherchée."); return;
  }
  occupe(b, "Recherche dans le Club…");
  try {
    etat.resultat = await api("/api/rechercher", { besoin: etat.besoin });
    $("#bloc-intro").hidden = true;
    $("#comparaison").open = false;
    transition(() => { rendreResultats(); montrer("#bloc-resultats"); });
    etape(3);
    $("#bloc-resultats").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) { toast(e.message, true); }
  finally { libre(b); }
}

function carte(s, { piste = false } = {}) {
  const p = s.profil;
  const niveau = piste ? ["piste", "Piste plus large · non vérifiée"]
    : s.niveau === "forte" ? ["forte", "Correspondance forte"] : ["partielle", "Correspondance partielle · à vérifier"];
  return h("article", { class: "carte" + (s.niveau === "partielle" || piste ? " partielle" : "") },
    h("div", {},
      h("span", { class: "niveau " + niveau[0] }, niveau[1]),
      h("h3", { class: "qui" }, p.nom),
      h("p", { class: "ou" }, `${p.fonction} · ${p.entreprise} · ${p.commune}` + (p.type === "exposant" ? " · exposant" : ""))),
    piste ? null : h("div", { class: "cta" },
      h("button", { class: "primaire", type: "button", onclick: () => ouvrirIntro(s) }, "Demander une introduction")),
    h("div", { class: "corps" },
      h("ul", { class: "pourquoi", "aria-label": "Pourquoi" }, s.preuves.map((pr) =>
        h("li", {}, h("span", { class: "coche", "aria-hidden": "true" }, "✓"),
          h("span", {},
            h("span", { class: "citation" }, pr.champ === "langues" ? `Parle ${LANGUES[pr.extrait] || pr.extrait}`
              : pr.champ === "zones_service" ? `Dessert : ${pr.extrait}` : `« ${pr.extrait} »`),
            h("span", { class: "provenance" }, ["langues", "zones_service"].includes(pr.champ)
              ? PROVENANCE[pr.champ] : `${pr.critere} · ${PROVENANCE[pr.champ]}`))))),
      s.a_verifier.length ? h("ul", { class: "averifier" }, s.a_verifier.map((a) => h("li", {}, a))) : null,
      s.reciprocite ? h("p", { class: "reciproque" }, `Réciprocité : cherche elle-même / lui-même « ${s.reciprocite.extrait} »`) : null));
}

function rendreResultats() {
  const r = etat.resultat;
  const cartes = $("#cartes"); cartes.replaceChildren();
  if (r.abstention) {
    $("#t-resultats").textContent = "Pas de contact fiable";
    $("#resume-resultats").textContent = `${r.nb_profils_examines} profils examinés.`;
    cartes.append(h("div", { class: "abstention" },
      h("p", { class: "grand" }, "Je préfère ne rien vous proposer plutôt qu'un mauvais contact."),
      h("p", {}, r.message),
      h("p", {}, "Vous pouvez assouplir un critère obligatoire, ou reformuler votre besoin."),
      r.pistes_elargies.length ? h("div", { class: "pistes" },
        h("p", {}, h("strong", {}, "Pistes plus larges"), " : ces membres couvrent une catégorie voisine, pas votre besoin précis."),
        r.pistes_elargies.map((s) => carte(s, { piste: true }))) : null));
  } else {
    const n = r.suggestions.length;
    $("#t-resultats").textContent = n === 1 ? "1 contact pertinent" : `${n} contacts pertinents`;
    $("#resume-resultats").textContent = `${r.nb_profils_examines} profils examinés en ${Math.max(1, Math.round(r.duree_ms))} ms. Chaque raison cite le profil mot pour mot.`;
    r.suggestions.slice(0, 3).forEach((s) => cartes.append(carte(s)));
  }
  const ec = $("#ecartes");
  const total = r.ecartes.reduce((a, e) => a + e.nombre, 0);
  ec.hidden = total === 0;
  ec.querySelector("summary").textContent = `${total} profil${total > 1 ? "s" : ""} pertinent${total > 1 ? "s" : ""} écarté${total > 1 ? "s" : ""} par vos critères ou leur choix`;
  ec.querySelector("ul").replaceChildren(...r.ecartes.map((e) => h("li", {}, `${e.nombre} × ${e.raison}`)));
}

async function comparer() {
  const zone = $("#comparaison-contenu");
  zone.replaceChildren(h("span", { class: "chargement" }, "Comparaison…"));
  try {
    const r = await api("/api/comparer", { besoin: etat.besoin });
    const col = (titre, res, mots) => h("div", { class: "colonne" }, h("h3", {}, titre),
      res.suggestions.length ? h("ol", {}, res.suggestions.slice(0, 3).map((s) =>
        h("li", {}, `${s.profil.nom} · ${s.profil.entreprise}`, mots ? h("span", { class: "mots" }, s.preuves[0].extrait) : null)))
        : h("p", { class: "vide" }, "Aucun résultat (abstention)."));
    zone.replaceChildren(
      col("Le Fil du Club", r.moteur, false),
      col("Mots-clés + mêmes filtres", r.reference, true),
      h("p", { class: "note-honnete" }, "Les deux colonnes appliquent les mêmes filtres (consentement, zone, langue, concurrence). Seul le classement diffère. Données fictives : comparaison illustrative, pas une validation."));
  } catch (e) { zone.replaceChildren(h("p", {}, e.message)); }
}

// ---------------------------------------------------------------- étape 4
async function ouvrirIntro(s) {
  etat.cible = s.profil;
  $("#t-intro").textContent = `Demander une introduction à ${s.profil.nom}`;
  $("#message").value = "";
  montrer("#bloc-intro"); etape(4);
  $("#btn-envoyer").textContent = etat.config.donnees_fictives ? "Envoyer la demande (simulation)" : "Envoyer la demande";
  $("#bloc-intro").scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const r = await api(`/api/introductions/brouillon?cible_id=${encodeURIComponent(s.profil.id)}`, { besoin: etat.besoin });
    $("#message").value = r.message;
  } catch (e) { toast(e.message, true); }
}

async function envoyer() {
  const b = $("#btn-envoyer");
  occupe(b, "Enregistrement…");
  try {
    await api("/api/introductions", { cible_id: etat.cible.id, besoin: etat.besoin, message: $("#message").value });
    toast(etat.config.donnees_fictives ? "Demande enregistrée (simulation, rien n'a été envoyé)." : "Demande envoyée.");
    $("#bloc-intro").hidden = true;
    await rendreSuivi();
    etape(5);
    $("#bloc-suivi").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) { toast(e.message, true); }
  finally { libre(b); }
}

// ---------------------------------------------------------------- étape 5
async function agir(intro, action, extra = {}) {
  try {
    await api(`/api/introductions/${intro.id}/${action}`, { acteur: extra.acteur || "demandeur", ...extra });
    await rendreSuivi();
  } catch (e) { toast(e.message, true); }
}

async function rendreSuivi() {
  let intros = [];
  try { intros = await api("/api/introductions"); } catch { return; }
  const zone = $("#suivi"); zone.replaceChildren();
  if (!intros.length) { $("#bloc-suivi").hidden = true; return; }
  montrer("#bloc-suivi");
  for (const i of intros) {
    const prenom = i.cible ? i.cible.nom.split(" ")[0] : "la personne";
    const idx = ETAPES_FRISE.findIndex(([k]) => k === i.etat);
    const arret = i.etat === "refusee" || i.etat === "annulee";
    // Dernière étape atteinte avant un refus ou une annulation.
    const dernierOk = arret ? Math.max(0, ...i.historique.map((e) => ETAPES_FRISE.findIndex(([k]) => k === e.etat))) : idx;
    const boutons = [];
    const sim = etat.config.donnees_fictives;
    if (i.etat === "demandee" && sim) {
      boutons.push(h("button", { class: "simulation", type: "button", onclick: () => agir(i, "accepter", { acteur: "cible" }) }, `Simuler : ${prenom} accepte`));
      boutons.push(h("button", { class: "simulation", type: "button", onclick: () => agir(i, "refuser", { acteur: "cible" }) }, `Simuler : ${prenom} décline`));
    }
    if (i.etat === "acceptee") {
      const d = h("input", { type: "date", "aria-label": "Date de la rencontre" });
      boutons.push(d, h("button", { type: "button", onclick: () => d.value ? agir(i, "planifier", { date_rencontre: d.value }) : toast("Choisissez une date.") }, "Planifier la rencontre"));
    }
    if (i.etat === "rencontre_planifiee") boutons.push(h("button", { type: "button", onclick: () => agir(i, "confirmer_rencontre") }, "La rencontre a eu lieu"));
    if (i.etat === "rencontre_faite") {
      for (const [k, v] of Object.entries(RESULTATS)) boutons.push(h("button", { type: "button", onclick: () => agir(i, "cloturer", { resultat: k }) }, v));
    }
    if (["demandee", "acceptee", "rencontre_planifiee"].includes(i.etat)) {
      boutons.push(h("button", { type: "button", class: "lien", onclick: () => agir(i, "annuler") }, "Annuler"));
    }
    zone.append(h("article", { class: "intro" },
      h("div", { class: "tete" },
        h("span", { class: "qui" }, i.cible ? `${i.cible.nom} · ${i.cible.entreprise}` : i.cible_id),
        h("span", { class: "etat" }, i.libelle_etat + (i.resultat ? ` : ${RESULTATS[i.resultat]}` : ""))),
      h("ol", { class: "frise", "aria-label": "Progression" }, ETAPES_FRISE.map(([k, lib], j) =>
        h("li", { class: arret && j > dernierOk ? "stop" : j < (arret ? dernierOk + 1 : idx) ? "ok" : j === idx ? "courant" : "" }, lib))),
      h("p", { class: "coord" }, i.coordonnees_partagees
        ? `Coordonnées partagées avec ${prenom}` + (i.simulation ? " (simulation : aucune coordonnée réelle)" : "")
        : "Coordonnées non partagées tant que la demande n'est pas acceptée."),
      i.date_rencontre ? h("p", { class: "coord" }, `Rencontre prévue le ${new Date(i.date_rencontre).toLocaleDateString("fr-CH")}`) : null,
      boutons.length ? h("div", { class: "boutons" }, boutons) : null));
  }
}

async function reinitialiser() {
  try {
    await api("/api/demo/reinitialiser", {});
    ["#bloc-criteres", "#bloc-resultats", "#bloc-intro", "#bloc-suivi"].forEach((s) => ($(s).hidden = true));
    $("#texte").value = ""; etat.besoin = null; etape(1);
    window.scrollTo({ top: 0, behavior: "smooth" });
    toast("Démo réinitialisée.");
  } catch (e) { toast(e.message, true); }
}

init();
