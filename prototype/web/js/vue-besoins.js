// Vue « Mes besoins » : liste, détail, modification (nouvelle version), offres reçues, correspondances, clôture.
import { $, api, dateCourte, emettre, erreurBloc, etat, h, occupe, libre, prenom, titreBesoin, toast, transition } from "./outils.js";
import { aUneCompetence, blocResultats, editeurCriteres, empreinte, frise } from "./composants.js";
import { ouvrirMessage } from "./dialogue.js";

const s = { ouvert: null, brouillon: null, empreinteServeur: null };

export async function vueBesoins() {
  const racine = $("#vue-besoins");
  let besoins, relations;
  try {
    [besoins, relations] = await Promise.all([api("/api/besoins"), api("/api/relations")]);
  } catch (e) { racine.replaceChildren(erreurBloc(e.message, vueBesoins)); return; }
  if (!besoins.length) {
    racine.replaceChildren(h("div", { class: "vide" }, h("strong", {}, "Aucun besoin pour l'instant."),
      "Exprimez-en un dans l'onglet « Nouveau besoin ».",
      h("div", { class: "actions" }, h("button", { class: "btn primaire", type: "button", onclick: () => emettre("vue", "nouveau") }, "Exprimer un besoin"))));
    return;
  }
  if (!s.ouvert || !besoins.some((b) => b.id === s.ouvert)) s.ouvert = besoins[0].id;
  const liste = h("div", { class: "liste-besoins", role: "list" }, besoins.map((b) => {
    const offres = relations.filter((r) => r.besoin_id === b.id && r.je_suis_destinataire && r.etat === "proposee").length;
    return h("button", { class: "ligne-besoin", type: "button", role: "listitem", "aria-current": String(b.id === s.ouvert),
      onclick: () => { s.ouvert = b.id; s.brouillon = null; vueBesoins(); } },
      h("span", { class: "titre" }, titreBesoin(b.besoin)),
      h("span", { class: "statut " + b.statut }, b.libelle_statut.split(" (")[0].split(" :")[0]),
      h("span", { class: "meta" }, `Version ${b.version} · créé le ${dateCourte(b.cree_le)}` + (b.anonyme ? " · nom masqué dans la Bourse" : "")
        + (offres ? ` · ${offres} proposition${offres > 1 ? "s" : ""} d'aide en attente` : "")));
  }));
  const detail = h("div", { id: "detail-besoin" });
  racine.replaceChildren(h("h1", {}, "Mes besoins"), besoins.length > 1 ? liste : null, detail);
  await rendreDetail(besoins.find((b) => b.id === s.ouvert), relations.filter((r) => r.besoin_id === s.ouvert));
}

export function ouvrirBesoin(id) { s.ouvert = id; s.brouillon = null; }

async function rendreDetail(b, relations) {
  const zone = $("#detail-besoin");
  const clos = ["resolu", "retire"].includes(b.statut);
  if (!s.brouillon || s.brouillon.id !== b.id || s.brouillon.version !== b.version) {
    s.brouillon = { id: b.id, version: b.version, besoin: structuredClone(b.besoin), anonyme: b.anonyme };
  }
  const brouillon = s.brouillon;
  s.empreinteServeur = empreinte(b.besoin);
  const modifie = () => empreinte(brouillon.besoin) !== s.empreinteServeur || brouillon.anonyme !== b.anonyme;

  const btnModifs = h("button", { class: "btn primaire", type: "button", hidden: true, onclick: async (ev) => {
    if (!aUneCompetence(brouillon.besoin)) { toast("Gardez au moins une compétence recherchée."); return; }
    occupe(ev.currentTarget, "Enregistrement…");
    try {
      await api(`/api/besoins/${b.id}`, { methode: "PUT", corps: { besoin: brouillon.besoin, anonyme: brouillon.anonyme } });
      toast(`Nouvelle version enregistrée (version ${b.version + 1}). Correspondances recalculées.`, "info");
      s.brouillon = null; emettre("rafraichir");
    } catch (e) { toast(e.message, "erreur"); libre(ev.currentTarget); }
  } }, `Enregistrer les modifications (version ${b.version + 1})`);
  const btnAnnulerModifs = h("button", { class: "btn", type: "button", hidden: true, onclick: () => { s.brouillon = null; vueBesoins(); } }, "Annuler les modifications");

  const zoneResultats = h("div", { class: "resultats", "aria-live": "polite" }, h("div", { class: "squelette" }));
  const surChangement = () => {
    const m = modifie();
    btnModifs.hidden = !m; btnAnnulerModifs.hidden = !m;
    zoneResultats.classList.toggle("obsolete", m);
    zoneResultats.querySelector(".bandeau-obsolete")?.remove();
    if (m) zoneResultats.prepend(h("div", { class: "bandeau-obsolete", role: "status" },
      `Critères modifiés : ces correspondances concernent la version ${b.version}. Enregistrez pour les recalculer.`));
  };

  const offres = relations.filter((r) => r.initiateur === "aidant" && r.etat === "proposee");
  const acceptees = relations.filter((r) => ["acceptee", "rencontre_planifiee", "rencontre_faite", "cloturee"].includes(r.etat));

  zone.replaceChildren(
    h("section", { class: "bloc" },
      h("div", { class: "detail-tete" },
        h("div", {}, h("p", { class: "surtitre" }, `${b.libelle_statut} · version ${b.version}`),
          h("h2", {}, titreBesoin(b.besoin))),
        h("div", { class: "barre-actions" }, actionsBesoin(b, acceptees))),
      b.note_cloture ? h("p", { class: "aide" }, `Note de clôture : ${b.note_cloture}`) : null,
      h("p", { class: "texte-surligne" }, b.besoin.texte),
      editeurCriteres(brouillon.besoin, { onChange: surChangement, lectureSeule: clos }),
      !clos && b.statut !== "brouillon" ? h("label", { class: "bascule", style: "margin-top:14px" },
        h("input", { type: "checkbox", checked: brouillon.anonyme, onchange: (e) => { brouillon.anonyme = e.target.checked; surChangement(); } }),
        h("span", {}, "Masquer mon nom dans la Bourse")) : null,
      h("div", { class: "actions" }, btnModifs, btnAnnulerModifs)),
    offres.length ? h("section", { class: "bloc" }, h("h2", {}, "Propositions d'aide reçues"),
      offres.map((r) => carteOffre(r))) : null,
    clos ? null : h("section", { class: "bloc" }, h("h2", {}, "Qui peut vous aider"), zoneResultats));
  surChangement();
  if (clos) return;
  try {
    const res = await api(`/api/besoins/${b.id}/correspondances`);
    zoneResultats.replaceChildren(blocResultats(res, { action: (sug) => actionCorrespondance(b, sug) }));
    surChangement();
  } catch (e) { zoneResultats.replaceChildren(erreurBloc(e.message)); }
}

function actionsBesoin(b, acceptees) {
  const act = (action, corps = {}) => async (ev) => {
    occupe(ev.currentTarget, "…");
    try { await api(`/api/besoins/${b.id}/${action}`, { corps }); emettre("rafraichir"); }
    catch (e) { toast(e.message, "erreur"); libre(ev.currentTarget); }
  };
  const res = [];
  if (b.statut === "brouillon") res.push(h("button", { class: "btn rouge petit", type: "button", onclick: act("publier") }, "Publier dans la Bourse"));
  if (b.statut === "publie") res.push(h("button", { class: "btn petit", type: "button", onclick: act("depublier") }, "Retirer de la Bourse"));
  if (!["resolu", "retire"].includes(b.statut)) {
    for (const r of acceptees) {
      res.push(h("button", { class: "btn primaire petit", type: "button",
        onclick: act("cloturer", { resolu_par: r.id, note: `Résolu grâce à ${r.autre?.nom || "un membre"}` }) }, `Résolu grâce à ${prenom(r.autre?.nom)}`));
    }
    res.push(h("button", { class: "btn petit", type: "button", onclick: (ev) => {
      if (confirm("Clore ce besoin sans suite ? Les demandes en attente seront annulées.")) act("cloturer", { note: "Clos sans suite" })(ev);
    } }, "Clore sans suite"));
  }
  return res;
}

function actionCorrespondance(b, sug) {
  const r = sug.relation;
  if (r && !["declinee", "annulee", "retiree"].includes(r.etat)) {
    return h("span", { class: "etat-relation" + (r.coordonnees_partagees ? " ok" : "") }, r.libelle_etat);
  }
  return [
    r ? h("span", { class: "aide" }, `Précédente demande : ${r.libelle_etat.toLowerCase()}`) : null,
    h("button", { class: "btn primaire", type: "button", onclick: async () => {
      const ok = await ouvrirMessage({
        titre: `Demander une introduction à ${sug.profil.nom}`,
        consentement: `${prenom(sug.profil.nom)} reçoit votre demande et choisit d'accepter ou non. Vos coordonnées ne sont partagées qu'après son accord.`,
        brouillonUrl: `/api/relations/brouillon?besoin_id=${b.id}&cible_id=${sug.profil.id}`,
        libelleEnvoi: etat.config.donnees_fictives ? "Envoyer (simulation)" : "Envoyer",
        envoyer: (message) => api("/api/relations", { corps: { besoin_id: b.id, cible_id: sug.profil.id, message } }),
      });
      if (ok) { toast("Demande envoyée.", "info"); emettre("rafraichir"); }
    } }, `Solliciter ${prenom(sug.profil.nom)}`),
  ];
}

function carteOffre(r) {
  const act = (action) => async (ev) => {
    occupe(ev.currentTarget, "…");
    try { await api(`/api/relations/${r.id}/${action}`, { corps: {} }); emettre("rafraichir"); }
    catch (e) { toast(e.message, "erreur"); libre(ev.currentTarget); }
  };
  return h("article", { class: "relation a-faire" },
    h("div", { class: "tete" }, h("span", { class: "qui" }, `${r.autre?.nom} · ${r.autre?.entreprise}`),
      h("span", { class: "sens" }, "Propose son aide")),
    h("p", { class: "message" }, r.message),
    r.besoin_modifie_depuis ? h("p", { class: "info alerte" }, "Proposition faite sur une version antérieure de votre besoin.") : null,
    h("div", { class: "boutons" },
      h("button", { class: "btn primaire petit", type: "button", onclick: act("accepter") }, "Accepter et partager nos coordonnées"),
      h("button", { class: "btn petit", type: "button", onclick: act("decliner") }, "Décliner poliment")));
}
