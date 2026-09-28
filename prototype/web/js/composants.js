// Composants partagés entre les vues : éditeur de critères, cartes, abstention, comparaison.
import { api, etat, h, LANGUES } from "./outils.js";

const TYPES = {
  expertise: "Compétence souhaitée", langue: "Langue", zone: "Zone d'intervention",
  implantation: "Implantation du prestataire", texte_libre: "Compétence hors catalogue",
};
const PROVENANCE = {
  offre: "déclaré dans son offre", presentation: "mentionné dans sa présentation",
  langues: "langues du profil", zones_service: "zones d'intervention du profil",
  recherche: "ce qu'elle/il recherche", commune: "implantation du profil",
};

// ------------------------------------------------------------------ texte surligné
export function surligner(texte, besoin, provisoires = []) {
  const p = h("p", { class: "texte-surligne" });
  const plages = [];
  const ajouter = (ex, classe, titre) => {
    if (!ex) return;
    const i = texte.indexOf(ex);
    if (i >= 0 && !plages.some(([d, f]) => i < f && d < i + ex.length)) plages.push([i, i + ex.length, classe, titre]);
  };
  for (const c of [...(besoin?.criteres || []), ...provisoires]) ajouter(c.extrait, c.type, c.libelle || c.valeur);
  for (const e of besoin?.exclusions || []) ajouter(e.extrait, "exclusion", `Écarté : ${e.libelle}`);
  plages.sort((a, b) => a[0] - b[0]);
  let pos = 0;
  for (const [d, f, classe, titre] of plages) {
    p.append(texte.slice(pos, d), h("mark", { class: classe, title: titre }, texte.slice(d, f)));
    pos = f;
  }
  p.append(texte.slice(pos));
  return p;
}

// ------------------------------------------------------------------ éditeur de critères
/** Rend l'éditeur. `onChange()` est appelé après chaque modification (le besoin est muté en place). */
export function editeurCriteres(besoin, { onChange, lectureSeule = false, provisoires = [] } = {}) {
  const racine = h("div", { class: "editeur" });
  const rendre = () => {
    racine.replaceChildren();
    const principale = besoin.criteres.find((c) => (c.type === "expertise" || c.type === "texte_libre") && c.obligatoire);

    // Questions de clarification (termes ambigus)
    for (const a of besoin.ambiguites || []) {
      const suggestionIA = a.terme === "votre besoin";
      racine.append(h("div", { class: "question", role: "group", "aria-label": `Précision sur ${a.terme}` },
        h("p", {}, suggestionIA ? "Je n'ai pas reconnu la compétence. L'IA locale propose (à confirmer) :" : `« ${a.extrait} » : que voulez-vous dire ?`),
        h("div", { class: "choix" }, a.options.map((o) => h("button", {
          class: "pilule", type: "button", disabled: lectureSeule,
          onclick: () => {
            besoin.criteres.forEach((x) => { if (x.type === "expertise") x.obligatoire = false; });
            besoin.criteres = besoin.criteres.filter((x) => x.type !== "texte_libre");
            besoin.criteres.unshift({ type: "expertise", valeur: o.valeur, libelle: o.libelle, obligatoire: true, extrait: a.extrait, note: "précisé par vous" });
            besoin.ambiguites = besoin.ambiguites.filter((x) => x !== a);
            besoin.avertissements = [];
            rendre(); onChange?.();
          },
        }, o.libelle)),
          h("button", { class: "pilule", type: "button", disabled: lectureSeule, onclick: () => {
            besoin.ambiguites = besoin.ambiguites.filter((x) => x !== a); rendre(); onChange?.();
          } }, suggestionIA ? "Aucune : garder ma formulation" : "Aucune"))));
    }

    const ul = h("ul", { class: "criteres", "aria-label": "Critères de recherche" });
    besoin.criteres.forEach((c, i) => {
      const estPrincipale = c === principale;
      ul.append(h("li", { class: "critere" + (estPrincipale ? " principal" : ""), style: `animation-delay:${i * 50}ms` },
        h("span", { class: "type" }, estPrincipale ? "Besoin principal" : TYPES[c.type]),
        h("span", { class: "valeur" }, c.type === "texte_libre" ? `« ${c.valeur} »` : c.type === "langue" ? `Parle ${c.libelle}` : c.libelle),
        c.extrait ? h("span", { class: "source" }, `d'après « ${c.extrait} »`) : null,
        c.note ? h("span", { class: "note" }, c.note) : null,
        h("span", { class: "ligne" },
          estPrincipale ? h("span", { class: "bascule-oblig oblig", title: "Le besoin principal est toujours obligatoire." }, "Obligatoire")
            : h("button", {
              class: "bascule-oblig " + (c.obligatoire ? "oblig" : "souhait"), type: "button", "aria-pressed": String(!!c.obligatoire),
              disabled: lectureSeule, title: "Obligatoire : les profils qui ne le remplissent pas sont écartés. Souhaité : simple bonus.",
              onclick: () => { c.obligatoire = !c.obligatoire; rendre(); onChange?.(); },
            }, c.obligatoire ? "Obligatoire" : "Souhaité"),
          lectureSeule ? null : h("button", { class: "retirer", type: "button", "aria-label": `Retirer ${c.libelle}`,
            onclick: () => { besoin.criteres.splice(i, 1); rendre(); onChange?.(); } }, "×"))));
    });
    for (const p of provisoires) {
      ul.append(h("li", { class: "critere provisoire", "aria-busy": "true" },
        h("span", { class: "type" }, TYPES[p.type] || p.type),
        h("span", { class: "valeur" }, p.libelle || p.valeur),
        p.extrait ? h("span", { class: "source" }, `d'après « ${p.extrait} »`) : null));
    }
    for (const [i, e] of (besoin.exclusions || []).entries()) {
      ul.append(h("li", { class: "critere exclusion" },
        h("span", { class: "type" }, "Écarté par vous"),
        h("span", { class: "valeur" }, e.libelle),
        e.extrait ? h("span", { class: "source" }, `d'après « ${e.extrait} »`) : null,
        lectureSeule ? null : h("span", { class: "ligne" }, h("span"), h("button", { class: "retirer", type: "button", "aria-label": `Ne plus écarter ${e.libelle}`,
          onclick: () => { besoin.exclusions.splice(i, 1); rendre(); onChange?.(); } }, "×"))));
    }
    racine.append(ul);

    if (!lectureSeule) {
      const c = etat.config;
      const ajout = (libelle, options, creer) => {
        const sel = h("select", { "aria-label": libelle }, h("option", { value: "" }, libelle + "…"),
          options.map(([v, l]) => h("option", { value: v }, l)));
        sel.addEventListener("change", () => { if (sel.value) { creer(sel.value); rendre(); onChange?.(); } });
        return sel;
      };
      racine.append(h("div", { class: "ajouts" },
        ajout("Ajouter une compétence", c.concepts.map((k) => [k.valeur, k.libelle]), (v) => {
          if (besoin.criteres.some((x) => x.type === "expertise" && x.valeur === v)) return;
          const premier = !besoin.criteres.some((x) => x.type === "expertise" || x.type === "texte_libre");
          const k = c.concepts.find((x) => x.valeur === v);
          const crit = { type: "expertise", valeur: v, libelle: k.libelle, obligatoire: premier, extrait: null, note: "ajouté par vous" };
          if (premier) { besoin.criteres = besoin.criteres.filter((x) => x.type !== "texte_libre"); besoin.criteres.unshift(crit); besoin.avertissements = []; }
          else besoin.criteres.push(crit);
        }),
        ajout("Ajouter une zone d'intervention", c.zones.map((z) => [z, z]), (v) => {
          if (!besoin.criteres.some((x) => x.type === "zone" && x.valeur === v))
            besoin.criteres.push({ type: "zone", valeur: v, libelle: v, obligatoire: true, extrait: null, note: "ajouté par vous" });
        }),
        ajout("Ajouter une langue", c.langues.map((l) => [l.valeur, l.libelle]), (v) => {
          if (!besoin.criteres.some((x) => x.type === "langue" && x.valeur === v))
            besoin.criteres.push({ type: "langue", valeur: v, libelle: LANGUES[v] || v, obligatoire: false, extrait: null, note: "ajouté par vous" });
        })));
      racine.append(h("div", { class: "options" },
        h("label", { class: "bascule" }, h("input", { type: "checkbox", checked: !!besoin.exclure_concurrents,
          onchange: (e) => { besoin.exclure_concurrents = e.target.checked; onChange?.(); } }),
          h("span", {}, "Écarter mes concurrents", h("small", {}, "Membres du même secteur que vous"))),
        h("label", { class: "bascule" }, h("input", { type: "checkbox", checked: !!besoin.inclure_exposants,
          onchange: (e) => { besoin.inclure_exposants = e.target.checked; onChange?.(); } }),
          h("span", {}, "Inclure les exposants de la Foire", h("small", {}, "Entreprises exposantes non membres (hypothèse de conception)")))));
    }
    if (besoin.contexte?.length) racine.append(h("p", { class: "contexte" }, "Noté, mais non vérifiable dans les profils : " + besoin.contexte.join(" · ")));
    if (besoin.avertissements?.length) racine.append(h("ul", { class: "avertissements" }, besoin.avertissements.map((a) => h("li", {}, a))));
  };
  rendre();
  racine.rafraichir = rendre;
  return racine;
}

export function aUneCompetence(besoin) {
  return besoin.criteres.some((c) => c.type === "expertise" || c.type === "texte_libre");
}

/** Empreinte des critères : sert à détecter des résultats devenus obsolètes. */
export function empreinte(besoin) {
  return JSON.stringify([besoin.criteres.map((c) => [c.type, c.valeur, !!c.obligatoire]), (besoin.exclusions || []).map((e) => e.valeur),
    !!besoin.exclure_concurrents, !!besoin.inclure_exposants]);
}

// ------------------------------------------------------------------ cartes
export function lieux(p) {
  const z = p.zones_service?.length ? p.zones_service.join(", ") : "non renseignée";
  return `Implanté·e à ${p.commune} · intervient : ${z}`;
}

export function listePreuves(preuves) {
  return h("ul", { class: "pourquoi", "aria-label": "Pourquoi" }, preuves.map((pr) =>
    h("li", {}, h("span", { class: "coche", "aria-hidden": "true" }, "✓"),
      h("span", {},
        h("span", { class: "citation" }, pr.champ === "langues" ? `Parle ${LANGUES[pr.extrait] || pr.extrait}`
          : pr.champ === "zones_service" ? `Intervient en : ${pr.extrait}`
          : pr.champ === "commune" ? `Implanté·e à ${pr.extrait}` : `« ${pr.extrait} »`),
        h("span", { class: "provenance" }, ["langues", "zones_service", "commune"].includes(pr.champ)
          ? PROVENANCE[pr.champ] : `${pr.critere} · ${PROVENANCE[pr.champ]}` + (pr.nature === "textuel" ? " · correspondance par mots" : ""))))));
}

const STATUT = { verifie: ["✓", "Vérifié"], a_verifier: ["?", "À vérifier"], non_satisfait: ["✗", "Non satisfait"] };

// « Pourquoi cette personne ? » / « Pourquoi pas elle ? » : critère par critère, verdict calculé par le même
// moteur que la liste (le serveur ne divulgue jamais une raison liée au consentement ou à la disponibilité).
export async function explication(besoin, membreId) {
  const e = await api("/api/expliquer", { corps: { besoin, membre_id: membreId } });
  return h("div", { class: "explication " + e.verdict },
    h("p", { class: "resume" }, e.resume),
    e.lignes.length ? h("ul", { class: "criteres-verdict" }, e.lignes.map((l) =>
      h("li", { class: l.statut },
        h("span", { class: "pastille", "aria-label": STATUT[l.statut][1] }, STATUT[l.statut][0]),
        h("span", {}, h("strong", {}, l.critere.charAt(0).toUpperCase() + l.critere.slice(1) + (l.obligatoire ? "" : " (souhaité)")), " — ", l.detail,
          l.preuve && !["langues", "zones_service", "commune"].includes(l.preuve.champ)
            ? h("span", { class: "citation" }, ` « ${l.preuve.extrait} »`) : null)))) : null);
}

function pliExplication(besoin, membreId, libelle) {
  const zone = h("div", {});
  const d = h("details", { class: "pli pourquoi-detail" }, h("summary", {}, libelle), zone);
  d.addEventListener("toggle", async () => {
    if (!d.open || zone.childElementCount) return;
    zone.replaceChildren(h("span", { class: "chargement" }, "Vérification…"));
    try { zone.replaceChildren(await explication(besoin, membreId)); } catch (e) { zone.replaceChildren(h("p", {}, e.message)); }
  });
  return d;
}

export function blocPourquoiPas(besoin, res) {
  const proposes = new Set((res.suggestions || []).map((s) => s.profil.id));
  const choix = h("select", { "aria-label": "Membre" }, h("option", { value: "" }, "Choisir un membre…"));
  const zone = h("div", {});
  const d = h("details", { class: "pli" }, h("summary", {}, "Pourquoi pas quelqu'un d'autre ?"),
    h("p", { class: "aide" }, "Vous pensiez à un membre précis ? Le moteur explique, critère par critère, pourquoi il n'est pas proposé."),
    h("div", { class: "ligne-pourquoi-pas" }, choix,
      h("button", { class: "btn petit", type: "button", onclick: async () => {
        if (!choix.value) return;
        zone.replaceChildren(h("span", { class: "chargement" }, "Vérification…"));
        try { zone.replaceChildren(await explication(besoin, choix.value)); } catch (e) { zone.replaceChildren(h("p", {}, e.message)); }
      } }, "Expliquer")), zone);
  d.addEventListener("toggle", async () => {
    if (!d.open || choix.options.length > 1) return;
    try {
      const membres = await api("/api/membres");
      membres.filter((m) => !proposes.has(m.id)).sort((a, b) => a.nom.localeCompare(b.nom))
        .forEach((m) => choix.append(h("option", { value: m.id }, `${m.nom} · ${m.entreprise}`)));
    } catch (e) { zone.replaceChildren(h("p", {}, e.message)); }
  });
  return d;
}

export function carteCorrespondance(s, { piste = false, action = null, besoin = null } = {}) {
  const p = s.profil;
  const niveau = piste ? ["piste", "Piste plus large · non vérifiée"]
    : s.niveau === "forte" ? ["forte", "Correspondance forte"] : ["partielle", "Correspondance partielle · à vérifier"];
  return h("article", { class: "carte" + (s.niveau === "partielle" || piste ? " partielle" : "") },
    h("div", {},
      h("span", { class: "niveau " + niveau[0] }, niveau[1]),
      h("h3", { class: "qui" }, p.nom),
      h("p", { class: "ou" }, `${p.fonction} · ${p.entreprise}` + (p.type === "exposant" ? " · exposant" : "")),
      h("p", { class: "lieux" }, lieux(p)),
      p.alertes_contenu?.length ? h("p", { class: "alerte-contenu", title: p.alertes_contenu.join(" · ") },
        "Ce profil contient des formulations inhabituelles : seules ses offres déclarées comptent.") : null),
    action ? h("div", { class: "cta" }, action) : null,
    h("div", { class: "corps" },
      listePreuves(s.preuves),
      s.a_verifier?.length ? h("ul", { class: "averifier" }, s.a_verifier.map((a) => h("li", {}, a))) : null,
      s.reciprocite ? h("p", { class: "reciproque" }, `Réciprocité : cherche aussi « ${s.reciprocite.extrait} »`) : null,
      besoin ? pliExplication(besoin, p.id, "Pourquoi cette personne ? Critère par critère") : null));
}

export function blocResultats(res, { action, titre = true, besoin = null } = {}) {
  const frag = h("div", {});
  if (res.abstention) {
    frag.append(h("div", { class: "abstention" },
      h("p", { class: "grand" }, "Je préfère ne rien vous proposer plutôt qu'un mauvais contact."),
      h("p", {}, res.message),
      h("p", {}, "Assouplissez un critère obligatoire, reformulez, ou publiez le besoin dans la Bourse : un membre qui complète son profil pourra le voir."),
      res.pistes_elargies?.length ? h("div", { class: "pistes" },
        h("p", {}, h("strong", {}, "Pistes plus larges"), " : catégorie voisine, pas votre besoin précis."),
        res.pistes_elargies.map((s) => carteCorrespondance(s, { piste: true }))) : null));
  } else {
    if (titre) frag.append(h("p", { class: "sous" },
      `${res.suggestions.length} membre${res.suggestions.length > 1 ? "s" : ""} sur ${res.nb_profils_examines} examinés · ${Math.max(1, Math.round(res.duree_ms))} ms · chaque raison cite le profil mot pour mot.`));
    frag.append(h("div", { class: "cartes" }, res.suggestions.slice(0, 3).map((s) => carteCorrespondance(s, { action: action?.(s), besoin }))));
  }
  if (besoin) frag.append(blocPourquoiPas(besoin, res));
  const total = (res.ecartes || []).reduce((a, e) => a + e.nombre, 0);
  if (total) {
    frag.append(h("details", { class: "pli" },
      h("summary", {}, `${total} membre${total > 1 ? "s" : ""} pertinent${total > 1 ? "s" : ""} écarté${total > 1 ? "s" : ""} par vos critères ou par leur choix`),
      h("ul", {}, res.ecartes.map((e) => h("li", {}, `${e.nombre} × ${e.raison}`))),
      h("p", { class: "aide" }, "Les noms ne sont jamais affichés : refuser d'être sollicité·e reste discret.")));
  }
  return frag;
}

export function blocComparaison(besoin) {
  const zone = h("div", { class: "comparaison-contenu" });
  const d = h("details", { class: "pli" }, h("summary", {}, "Comparer avec une simple recherche par mots-clés"), zone);
  d.addEventListener("toggle", async () => {
    if (!d.open) return;
    zone.replaceChildren(h("span", { class: "chargement" }, "Comparaison…"));
    try {
      const r = await api("/api/comparer", { corps: { besoin } });
      const col = (titre, res, mots) => h("div", { class: "colonne" }, h("h4", {}, titre),
        res.suggestions.length ? h("ol", {}, res.suggestions.slice(0, 3).map((s) =>
          h("li", {}, `${s.profil.nom} · ${s.profil.entreprise}`, mots ? h("span", { class: "mots" }, s.preuves[0].extrait) : null)))
          : h("p", { class: "aide" }, "Aucun résultat (abstention)."));
      zone.replaceChildren(col("Le Fil du Club", r.moteur, false), col("Mots-clés + mêmes filtres", r.reference, true),
        h("p", { class: "note-honnete" }, "Mêmes filtres des deux côtés (consentement, zones, langue, concurrence) : seul le classement diffère. Données fictives : illustration, pas validation."));
    } catch (e) { zone.replaceChildren(h("p", {}, e.message)); }
  });
  return d;
}

export const ETAPES_FRISE = [["proposee", "Proposée"], ["acceptee", "Acceptée"], ["rencontre_planifiee", "Rencontre planifiée"],
  ["rencontre_faite", "Rencontre faite"], ["cloturee", "Résultat noté"]];
export const RESULTATS = { utile: "Utile", affaire_en_cours: "Affaire en cours", pas_pertinent: "Pas pertinent" };

export function frise(r) {
  const idx = ETAPES_FRISE.findIndex(([k]) => k === r.etat);
  const arret = ["declinee", "retiree", "annulee"].includes(r.etat);
  const atteint = arret ? Math.max(0, ...r.historique.map((e) => ETAPES_FRISE.findIndex(([k]) => k === ({ proposer: "proposee", accepter: "acceptee", planifier: "rencontre_planifiee", confirmer_rencontre: "rencontre_faite" })[e.action]))) : idx;
  return h("ol", { class: "frise", "aria-label": "Progression" }, ETAPES_FRISE.map(([, lib], j) =>
    h("li", { class: arret ? (j <= atteint ? "ok" : "stop") : j < idx ? "ok" : j === idx ? "courant" : "" }, lib)));
}
