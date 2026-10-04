/* Club Pulse · deck v3 — le fil visuel : les membres sont des points lumineux.
   Un seul canvas sous les slides. Chaque (slide, pas) décrit une SCÈNE : où vont les points, leur lumière, les liens.
   Un seul langage de mouvement : 240 / 480 / 720 (durées en ms) et l'easing cubic-bezier(0.22, 1, 0.36, 1).
   Un clic au milieu d'une animation la termine aussitôt (finir()). Sous 30 images/s : version allégée, toute seule.
   Mouvement coupé (touche M, ou « réduire les animations » du système) : les points se posent sans voyager.
   Tout est local : aucune ressource externe. */
(function () {
  "use strict";
  const W = 1920, H = 1080, N = 180;
  const T = { micro: 240, entree: 480, signature: 720 };
  const cv = document.getElementById("points"), cx = cv.getContext("2d", { alpha: false });

  // easing du design system : cubic-bezier(0.22, 1, 0.36, 1)
  function bezier(x1, y1, x2, y2) {
    const A = (a, b) => 1 - 3 * b + 3 * a, B = (a, b) => 3 * b - 6 * a, C = a => 3 * a;
    const f = (t, a, b) => ((A(a, b) * t + B(a, b)) * t + C(a)) * t, d = (t, a, b) => 3 * A(a, b) * t * t + 2 * B(a, b) * t + C(a);
    return x => { if (x <= 0) return 0; if (x >= 1) return 1; let t = x;
      for (let k = 0; k < 6; k++) { const e = f(t, x1, x2) - x, s = d(t, x1, x2); if (Math.abs(e) < 1e-4 || !s) break; t -= e / s; }
      return f(t, y1, y2); };
  }
  const ease = bezier(0.22, 1, 0.36, 1);

  // hasard déterministe (même dessin à chaque répétition)
  let graine = 2026; const rnd = () => (graine = (graine * 16807) % 2147483647) / 2147483647;

  // sprites lumineux pré-rendus (dessin rapide : drawImage)
  function sprite(coul, taille) {
    const c = document.createElement("canvas"); c.width = c.height = taille; const g = c.getContext("2d"), r = taille / 2;
    const gr = g.createRadialGradient(r, r, 0, r, r, r);
    gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.16, coul(1)); gr.addColorStop(0.42, coul(0.32)); gr.addColorStop(1, coul(0));
    g.fillStyle = gr; g.fillRect(0, 0, taille, taille); return c;
  }
  const HALO = (() => { const c = document.createElement("canvas"); c.width = W; c.height = H; const g = c.getContext("2d");
    const h = g.createRadialGradient(960, 620, 80, 960, 620, 980); h.addColorStop(0, "rgba(40,26,30,.55)"); h.addColorStop(1, "rgba(5,7,11,0)");
    g.fillStyle = h; g.fillRect(0, 0, W, H); return c; })();
  const CHAUD = sprite(a => `rgba(255,214,170,${a})`, 48), ROUGE = sprite(a => `rgba(205,33,40,${a})`, 48), VERT = sprite(a => `rgba(74,222,128,${a})`, 48);

  const P = Array.from({ length: N }, (_, k) => ({ k, x: rnd() * W, y: rnd() * H, x0: 0, y0: 0, tx: 0, ty: 0, a: 0, a0: 0, ta: 0,
    r: 1 + rnd() * 1.4, ph: rnd() * 6.283, sp: 0.4 + rnd() * 0.8, rouge: false, d: rnd() * 0.35 }));

  // ── les formes ─────────────────────────────────────────────────────────
  const carte = k => { const c = k % 18, l = Math.floor(k / 18) % 10, x = 450 + 60 + c * 54, y = 196 + 60 + l * 60, a = -3 * Math.PI / 180;
    const mx = 960, my = 526; return [mx + (x - mx) * Math.cos(a) - (y - my) * Math.sin(a), my + (x - mx) * Math.sin(a) + (y - my) * Math.cos(a)]; };
  const foule = (cxp, cyp, rx, ry) => k => { const t = rnd() * 6.283, u = Math.sqrt(rnd()); return [cxp + Math.cos(t) * rx * u, cyp + Math.sin(t) * ry * u]; };
  const bords = k => { const t = (k / N) * 6.283 + rnd() * 0.2, R = 1150 + rnd() * 120; return [960 + Math.cos(t) * R, 540 + Math.sin(t) * R * 0.62]; };
  const bordsVisibles = k => { const t = (k / N) * 6.283 + rnd() * 0.3, R = 0.9 + rnd() * 0.12;
    return [960 + Math.cos(t) * 980 * R, 540 + Math.sin(t) * 560 * R]; };
  const spirale = (cxp, cyp, R) => k => { const t = k * 2.39996, r = R * Math.sqrt((k + 0.5) / N); return [cxp + Math.cos(t) * r, cyp + Math.sin(t) * r]; };
  const grille145 = k => k < 145 ? [190 + (k % 29) * 53, 476 + Math.floor(k / 29) * 34] : bords(k);   // 29 × 5 = 145, une grille qui se compte

  // ── les scènes : (slide, pas) → cible ─────────────────────────────────
  // lumiere : multiplicateur global ; liens : « on s'appelle » ; bouge : dérive au repos ; n : points visibles
  const CACHE = {};
  function scene(id, pas) { const cle = sceneCle(id, pas); return CACHE[cle] || (CACHE[cle] = Object.assign(sceneBrute(id, pas), { cle })); }
  function sceneCle(id, pas) {
    if (id === "stat") return pas < 1 ? "stat-liens" : "dispersion";
    if (["2", "8", "ea3"].includes(id)) return "et-apres";
    if (["cinema", "film", "regardez", "18", "20"].includes(id)) return "noir";
    if (["salle", "constellation", "cote-club", "chiffres-club", "19", "1", "matin"].includes(id)) return id;
    return "fond";
  }
  function sceneBrute(id, pas) {
    switch (id) {
      case "1": return { forme: carte, alpha: 0, lumiere: 1, n: N };
      case "matin": return { forme: foule(1340, 820, 480, 200), alpha: 0.9, lumiere: 1, bouge: 1, liens: 1, n: N, depuis: "carte" };
      case "stat": return pas < 1 ? { forme: foule(1540, 800, 330, 110), alpha: 0.9, lumiere: 1, bouge: 1, liens: 1, n: N }
        : { forme: bordsVisibles, alpha: 0.32, lumiere: 0.55, bouge: 0.6, n: N };
      case "2": case "8": case "ea3": return { forme: bordsVisibles, alpha: 0.4, lumiere: 0.5, bouge: 0.5, n: N };
      case "cinema": case "film": case "regardez": case "18": case "20": return { forme: bords, alpha: 0, lumiere: 0, n: N };
      case "salle": return { forme: spirale(960, 560, 820), alpha: 0.3, lumiere: 0.6, bouge: 0.6, n: N };
      case "constellation": return { forme: spirale(1480, 600, 300), alpha: 0.85, lumiere: 1, bouge: 0.4, n: N, ecran: 1 };
      case "cote-club": return { forme: bords, alpha: 0, lumiere: 0.8, n: N, anneau: 1 };
      case "chiffres-club": return { forme: grille145, alpha: 0.95, lumiere: 1, n: 145, compte: 1, ordre: 1 };
      case "19": return { forme: bordsVisibles, alpha: 0.18, lumiere: 0.5, bouge: 0.4, n: N };
      default: return { forme: bordsVisibles, alpha: 0.14, lumiere: 0.45, bouge: 0.4, n: N };
    }
  }

  let courante = { id: "1", pas: 0 }, sc = scene("1", 0), debut = 0, duree = 0, lumiere = 1, lumiere0 = 1, liens = [];
  let mouvementCoupe = matchMedia("(prefers-reduced-motion: reduce)").matches, mouvementForce = null;
  const mouvement = () => !(mouvementForce === null ? mouvementCoupe : mouvementForce);
  let ecranT = -1, allege = false, ips = 60, cadres = [], sousSeuil = 0, actif = true, anneauT = -1;

  function viser(id, pas) {
    const avant = courante; courante = { id, pas }; const s = scene(id, pas);
    const meme = s.cle === sc.cle;
    sc = s; graine = 2026 + id.length * 31 + pas * 7;
    if (meme) return;
    const depuisCarte = s.depuis === "carte" && avant.id === "1";
    P.forEach((p, k) => {
      if (depuisCarte) { const [x, y] = carte(k); p.x = x; p.y = y; p.a = 1; }       // la carte se dissout en points
      const [tx, ty] = s.forme(k); p.dd = s.ordre ? Math.min(1, k / 145) * 0.6 : p.d; p.x0 = p.x; p.y0 = p.y; p.tx = tx; p.ty = ty; p.a0 = p.a; p.ta = k < s.n ? s.alpha : 0;
    });
    lumiere0 = lumiere; debut = performance.now(); duree = mouvement() ? (depuisCarte ? T.signature * 2 : T.signature) : 0;
    liens = []; anneauT = s.anneau ? performance.now() : -1;
    if (!mouvement()) finir();
  }
  function enCours() { return performance.now() - debut < duree * 1.35; }
  function finir() { P.forEach(p => { p.x = p.tx; p.y = p.ty; p.a = p.ta; p.x0 = p.tx; p.y0 = p.ty; p.a0 = p.ta; }); lumiere = sc.lumiere; lumiere0 = lumiere;
    duree = 0; if (anneauT >= 0) anneauT = performance.now() - 6000; }

  // ── l'anneau de l'acte 4 : la pièce manquante, un invité arrive du bord, l'anneau se ferme ─────────────
  function dessinerAnneau(t) {
    const cxp = 960, cyp = 860, R = 150, n = 9, vide = 6, e = t / 1000, ARR = 2.16, FER = 2.88;   // 2.16 s = 3 × 720 ms
    for (let k = 0; k < n; k++) {
      const a = -Math.PI / 2 + (k / n) * 6.283, x = cxp + Math.cos(a) * R, y = cyp + Math.sin(a) * R;
      const apparu = ease(Math.min(1, Math.max(0, (e - k * 0.06) / 0.48)));
      if (k === vide) {
        const arrivee = ease(Math.min(1, Math.max(0, (e - ARR) / 0.72)));
        cx.globalAlpha = apparu * (1 - arrivee) * (0.55 + 0.45 * Math.sin(e * 6.283 / 1.44));   // le point creux pulse
        cx.strokeStyle = "#CD2128"; cx.lineWidth = 6; cx.beginPath(); cx.arc(x, y, 24, 0, 6.283); cx.stroke();
        if (arrivee > 0) {                                                                         // l'invité, depuis le bord (Annecy)
          const gx = 2010 + (x - 2010) * arrivee, gy = 980 + (y - 980) * arrivee;
          cx.globalAlpha = 1; cx.drawImage(CHAUD, gx - 36, gy - 36, 72, 72);
          const eclat = Math.max(0, 1 - Math.abs(e - FER - 0.36) / 0.36);                         // un seul éclat rouge, à la fermeture
          if (eclat > 0) { cx.globalAlpha = eclat; cx.drawImage(ROUGE, x - 60, y - 60, 120, 120); }
        }
      } else { cx.globalAlpha = apparu; cx.drawImage(CHAUD, x - 32, y - 32, 64, 64); }
    }
    const ferme = ease(Math.min(1, Math.max(0, (e - FER) / 0.72)));
    cx.globalAlpha = 0.5 + 0.4 * ferme; cx.strokeStyle = "rgba(255,226,196,1)"; cx.lineWidth = 6; cx.lineCap = "round";
    cx.beginPath(); cx.arc(cxp, cyp, R, -Math.PI / 2, -Math.PI / 2 + 6.283 * (0.62 + 0.38 * ferme)); cx.stroke();
  }

  // ── la boucle ──────────────────────────────────────────────────────────
  let dernier = performance.now();
  function cadre(now) {
    requestAnimationFrame(cadre);
    const dt = now - dernier; dernier = now;
    if (!actif || document.body.classList.contains("jour")) return;
    cadres.push(dt); if (cadres.length > 30) cadres.shift();
    ips = 1000 / (cadres.reduce((a, b) => a + b, 0) / cadres.length);
    if (cadres.length >= 10 && ips < 30 && !document.hidden) { sousSeuil += dt; if (sousSeuil > 1500 && !allege) { allege = true; document.body.classList.add("allege"); } }
    else sousSeuil = 0;

    const u = duree ? Math.min(1, (now - debut) / duree) : 1;
    lumiere = lumiere0 + (sc.lumiere - lumiere0) * ease(u);
    cx.globalAlpha = 1; cx.fillStyle = "#05070B"; cx.fillRect(0, 0, W, H);
    if (!allege) { cx.globalAlpha = lumiere; cx.drawImage(HALO, 0, 0); }                       // une lumière qui baisse et remonte

    const ecranOn = sc.ecran && document.querySelector("#ecran-salle.on");
    if (ecranOn && ecranT < 0) ecranT = now; if (!ecranOn) ecranT = -1;
    const voile = ecranOn ? 1 - ease(Math.min(1, (now - ecranT) / T.signature)) : 1;
    const t = now / 1000, bouge = mouvement() && !allege ? (sc.bouge || 0) : 0;
    for (const p of P) {
      const dl = p.dd === undefined ? p.d : p.dd, v = ease(Math.max(0, Math.min(1, (u - dl * (duree ? 0.4 : 0)) / (duree ? 0.6 : 1))));
      p.x = p.x0 + (p.tx - p.x0) * v; p.y = p.y0 + (p.ty - p.y0) * v; p.a = p.a0 + (p.ta - p.a0) * v;
      const a = p.a * lumiere * voile; if (a < 0.01) continue;
      const x = p.x + Math.sin(t * p.sp + p.ph) * 6 * bouge, y = p.y + Math.cos(t * p.sp * 0.8 + p.ph) * 5 * bouge;
      cx.globalAlpha = a;
      if (allege) { cx.fillStyle = p.rouge ? "#CD2128" : "#FFD6AA"; cx.fillRect(x - 2, y - 2, 4, 4); }
      else { const s = (sc.ordre && p.k < 145 ? 30 : (p.rouge ? 30 : 22) * p.r); cx.drawImage(p.rouge ? ROUGE : CHAUD, x - s / 2, y - s / 2, s, s); }
    }
    // « On s'appelle » : des liens fugaces, qui naissent et s'effacent un à un
    if (sc.liens && !allege && u >= 0.6) {
      if (liens.length < 22 && Math.random() < 0.25) { const a = P[Math.floor(Math.random() * sc.n)], b = P[Math.floor(Math.random() * sc.n)];
        if (a !== b && Math.hypot(a.tx - b.tx, a.ty - b.ty) < 260) liens.push({ a, b, n: now }); }
      cx.lineWidth = 2; cx.strokeStyle = "rgba(255,214,170,1)";
      liens = liens.filter(l => { const age = (now - l.n) / (T.signature * 2); if (age > 1) return false;
        cx.globalAlpha = 0.5 * Math.sin(age * Math.PI) * lumiere; cx.beginPath(); cx.moveTo(l.a.x, l.a.y); cx.lineTo(l.b.x, l.b.y); cx.stroke(); return true; });
    }
    if (sc.anneau && anneauT >= 0) dessinerAnneau(now - anneauT);
    cx.globalAlpha = 1;
  }
  requestAnimationFrame(cadre);
  document.addEventListener("visibilitychange", () => { actif = !document.hidden; });

  window.points = {
    viser, finir, enCours: () => enCours() && mouvement(),
    vivant: () => cadres.length > 5 && performance.now() - dernier < 1000,
    mouvement, couper: (oui) => { mouvementForce = oui ? true : null; if (oui) finir(); },
    mesure: () => ({ ips: Math.round(ips), allege }),
  };
})();
