// Vue « Bourse » : les besoins publiés par d'autres membres auxquels VOUS pouvez répondre.
// Moment central de la démo : un besoin devient, pour un autre membre, une occasion concrète d'aider.
import { $, api, dateCourte, emettre, erreurBloc, etat, h, LANGUES, prenom, toast } from "./outils.js";
import { lieux } from "./composants.js";
import { ouvrirMessage } from "./dialogue.js";

const vus = new Set();   // pour animer l'arrivée des nouveaux besoins
let premierChargement = true;

export async function vueBourse() {
  const racine = $("#vue-bourse");
  let items;
  try { items = await api("/api/bourse"); }
  catch (e) { racine.replaceChildren(erreurBloc(e.message, vueBourse)); return; }
  const ouverts = items.filter((x) => !x.relation || !["declinee", "annulee", "retiree"].includes(x.relation.etat));
  const entete = [
    h("p", { class: "surtitre" }, "Bourse des besoins du Club"),
    h("h1", {}, ouverts.length ? (ouverts.length === 1 ? "Un membre a besoin de ce que vous faites." : `${ouverts.length} membres ont besoin de ce que vous faites.`)
      : "Personne n'a besoin de vous… pour l'instant."),
    h("p", { class: "sous" }, "Vous ne voyez que les besoins qui correspondent à votre profil, selon les mêmes règles que la recherche de leur auteur."),
  ];
  if (!items.length) {
    racine.replaceChildren(...entete, h("div", { class: "vide" }, h("strong", {}, "Aucun besoin ne correspond à votre profil."),
      "Quand un membre publie un besoin qui correspond à votre offre, il apparaît ici, avec la raison."));
    premierChargement = false;
    return;
  }
  racine.replaceChildren(...entete, h("div", { class: "cartes" }, items.map((x) => carteOpportunite(x))));
  items.forEach((x) => vus.add(x.besoin.id));
  premierChargement = false;
}

function puceCritere(c, cle) {
  const lib = c.type === "texte_libre" ? `« ${c.valeur} »` : c.type === "langue" ? `Parle ${c.libelle}` : c.libelle;
  const type = { expertise: cle ? "Besoin principal" : "Souhaité", zone: "Intervenir en", implantation: "Implanté·e en", langue: c.obligatoire ? "Langue" : "Langue (souhaité)", texte_libre: "Hors catalogue" }[c.type];
  return h("div", { class: "puce" + (cle ? " cle" : "") }, h("small", {}, type), lib);
}

function pucePreuve(pr, cle) {
  const lib = pr.champ === "langues" ? `Vous parlez ${LANGUES[pr.extrait] || pr.extrait}`
    : pr.champ === "zones_service" ? `Vous intervenez en ${pr.extrait}`
    : pr.champ === "commune" ? `Implanté·e à ${pr.extrait}` : `« ${pr.extrait} »`;
  const type = pr.champ === "offre" ? "Votre offre déclarée" : pr.champ === "presentation" ? "Votre présentation" : "Votre profil";
  return h("div", { class: "puce" + (cle ? " cle" : "") }, h("small", {}, type), lib);
}

function carteOpportunite({ besoin: b, correspondance: c, relation: r }) {
  const auteur = b.auteur || { nom: "Un membre du Club" };
  const qui = auteur.anonyme ? "Un membre du Club" : auteur.nom;
  const criteres = b.besoin.criteres;
  const principal = criteres.find((x) => x.type === "expertise" || x.type === "texte_libre");
  const nouvelle = !premierChargement && !vus.has(b.id);
  const fil = h("div", { class: "fil", "aria-hidden": "true" });
  fil.innerHTML = '<svg viewBox="0 0 64 100" preserveAspectRatio="none"><path d="M0 28 C 26 28, 38 28, 64 28"/></svg>';
  const actif = r && !["declinee", "annulee", "retiree"].includes(r.etat);

  return h("article", { class: "opportunite" + (nouvelle ? " nouvelle" : ""), "aria-label": `Besoin de ${qui}` },
    h("div", { class: "bandeau" },
      h("strong", {}, b.statut === "en_cours" ? "Besoin en cours" : "Nouveau besoin du Club"),
      h("span", {}, `Publié le ${dateCourte(b.cree_le)}` + (b.version > 1 ? ` · modifié (version ${b.version})` : ""))),
    h("div", { class: "accroche" },
      h("h2", { class: "titre-opportunite" }, `${qui} cherche : ${principal ? (principal.type === "texte_libre" ? principal.valeur : principal.libelle.toLowerCase()) : "…"}`),
      h("p", { class: "aide" }, auteur.anonyme ? `${auteur.entreprise} · ${auteur.commune || "Valais"} · nom révélé si la personne accepte votre aide`
        : `${auteur.fonction ? auteur.fonction + " · " : ""}${auteur.entreprise} · ${auteur.commune}`)),
    c ? h("div", { class: "pont" },
      h("div", { class: "cote" }, h("h3", {}, "Son besoin"), criteres.map((x) => puceCritere(x, x === principal))),
      fil,
      h("div", { class: "cote" }, h("h3", {}, "Pourquoi vous"), c.preuves.map((p, i) => pucePreuve(p, i === 0)))) : null,
    c?.a_verifier?.length ? h("ul", { class: "averifier", style: "padding:0 22px" }, c.a_verifier.map((a) => h("li", {}, a))) : null,
    h("div", { class: "pied-carte" },
      c ? h("span", { class: "niveau " + c.niveau }, c.niveau === "forte" ? "Correspondance forte" : "Correspondance partielle · à vérifier")
        : h("span", { class: "aide" }, "Ne correspond plus à votre profil ou à ses critères"),
      actif ? h("span", { class: "etat-relation" + (r.coordonnees_partagees ? " ok" : "") },
        r.initiateur === "aidant" ? `Votre proposition : ${r.libelle_etat.toLowerCase()}` : `Vous a sollicité·e : ${r.libelle_etat.toLowerCase()}`)
        : c ? h("button", { class: "btn rouge", type: "button", onclick: () => proposer(b, qui) }, "Proposer mon aide") : null));
}

async function proposer(b, qui) {
  const ok = await ouvrirMessage({
    titre: `Proposer votre aide à ${qui === "Un membre du Club" ? "ce membre" : prenom(qui)}`,
    consentement: "La personne choisit d'accepter ou non votre proposition. Les coordonnées ne sont partagées qu'après son accord" + (qui === "Un membre du Club" ? ", et son nom vous sera révélé à ce moment-là." : "."),
    brouillonUrl: `/api/relations/brouillon?besoin_id=${b.id}`,
    libelleEnvoi: etat.config.donnees_fictives ? "Proposer mon aide (simulation)" : "Proposer mon aide",
    envoyer: (message) => api("/api/relations", { corps: { besoin_id: b.id, message } }),
  });
  if (ok) { toast("Proposition envoyée. Suivez-la dans l'onglet Suivi.", "info"); emettre("rafraichir"); }
}
