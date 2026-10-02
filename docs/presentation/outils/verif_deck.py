import functools, http.server, socketserver, threading
from playwright.sync_api import sync_playwright
DECK = "/home/user/HackVS/docs/presentation/deck"
class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=DECK)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}/index.html"
R = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    # 1) réseau coupé : toute requête hors 127.0.0.1 est refusée
    ctx = b.new_context(viewport={"width": 1920, "height": 1080})
    bloque = []
    ctx.route("**/*", lambda r: (r.continue_() if r.request.url.startswith(f"http://127.0.0.1:{port}") or r.request.url.startswith("data:") else (bloque.append(r.request.url), r.abort())))
    pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base); pg.evaluate("window.pret"); pg.wait_for_timeout(2800)
    R["polices"] = pg.evaluate("document.fonts.check('800 100px \"Plus Jakarta Sans\"') && document.fonts.check('500 100px \"JetBrains Mono\"')")
    R["gel_lu"] = pg.evaluate("document.getElementById('chiffres').children.length")
    # 2) navigation clavier complète : avance jusqu'à la fin (flèche, espace, PageDown alternés), puis retour au début
    vus = []; touches = ["ArrowRight", " ", "PageDown"]
    for k in range(80):
        vus.append(pg.evaluate("location.hash")); pg.keyboard.press(touches[k % 3]); pg.wait_for_timeout(60)
    R["fin_atteinte"] = pg.evaluate("location.hash"); R["etats_parcourus"] = len(set(vus))
    for k in range(80): pg.keyboard.press(["ArrowLeft", "PageUp"][k % 2]); pg.wait_for_timeout(30)
    R["retour_debut"] = pg.evaluate("location.hash || '(début)'")
    # 3) N = noir
    pg.keyboard.press("n"); pg.wait_for_timeout(400); R["noir_on"] = pg.evaluate("getComputedStyle(document.getElementById('noir')).opacity")
    pg.keyboard.press("n"); pg.wait_for_timeout(400)
    # 4) R = répétition, points de contrôle
    pg.keyboard.press("r"); pg.wait_for_timeout(300)
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(400)
    R["repetition"] = pg.evaluate("document.getElementById('repet').innerText")
    pg.keyboard.press("r")
    # 5) 60 i/s pendant le moment signature de l'anneau (M4) et la pose de la carte (M6)
    for cible in ["10a", "18"]:
        pg.evaluate(f"allerA('{cible}', 0)"); pg.wait_for_timeout(300)
        if cible == "10a": pg.evaluate("allerA('9',0)"); 
        frames = pg.evaluate("""() => new Promise(res => { const t=[]; const f=n=>{t.push(n); if(t.length<60) requestAnimationFrame(f); else res(t);}; requestAnimationFrame(f);
           setTimeout(()=>window.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight'})),20); })""")
        d = [b2 - a for a, b2 in zip(frames, frames[1:])]
        R[f"fps_{cible}"] = f"max {max(d):.1f} ms, moyenne {sum(d)/len(d):.1f} ms ({len([x for x in d if x > 20])} images > 20 ms)"
    # 6) contraste AA : chaque élément texte visible, couleur texte vs fond effectif
    contr = pg.evaluate("""() => {
      const lum = c => { const v = c.match(/[\\d.]+/g).slice(0,3).map(Number).map(x => { x/=255; return x<=.03928? x/12.92 : Math.pow((x+.055)/1.055,2.4); }); return .2126*v[0]+.7152*v[1]+.0722*v[2]; };
      const fond = el => { while (el) { const b = getComputedStyle(el).backgroundColor; if (b && !b.startsWith('rgba(0, 0, 0, 0)') && b !== 'transparent') return b; el = el.parentElement; } return 'rgb(255,255,255)'; };
      const pire = []; for (const s of document.querySelectorAll('.slide')) { s.classList.add('active');
        for (const el of s.querySelectorAll('*')) { if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType===3 && n.textContent.trim())) continue;
          const c = getComputedStyle(el).color, f = fond(el); const L1 = lum(c), L2 = lum(f); const r = (Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05);
          const fs = parseFloat(getComputedStyle(el).fontSize); const seuil = fs >= 24 ? 3 : 4.5; if (r < seuil + 1.5) pire.push([s.dataset.id, el.textContent.trim().slice(0,40), r.toFixed(2), fs]); }
        s.classList.remove('active'); }
      return pire; }""")
    R["contrastes_limites (ratio < seuil AA + 1.5)"] = contr
    R["erreurs_js"] = errs; R["requetes_bloquees"] = bloque
    # 7) mouvement réduit : la carte se pose sans transformation
    ctx2 = b.new_context(viewport={"width": 1920, "height": 1080}, reduced_motion="reduce"); pg2 = ctx2.new_page(); pg2.goto(base); pg2.evaluate("window.pret")
    R["reduit_animation_carte"] = pg2.evaluate("getComputedStyle(document.getElementById('carte-1')).animationName")
    pg2.evaluate("allerA('13',1)"); pg2.wait_for_timeout(100); R["reduit_fragment_transform"] = pg2.evaluate("getComputedStyle(document.querySelector('[data-id=\"13\"] .fr')).transform")
    # 8) plan B du film (pas de film.mp4) et emplacement de capture si fichier absent
    pg2.evaluate("allerA('film',0)"); pg2.wait_for_timeout(200); R["film_planB"] = pg2.evaluate("document.querySelector('[data-id=\"film\"]').className")
    pg2.evaluate("document.querySelector('[data-id=\"10\"] img').src='assets/captures/absente.png'"); pg2.wait_for_timeout(300)
    R["emplacement_si_absente"] = pg2.evaluate("getComputedStyle(document.querySelector('[data-id=\"10\"] .emplacement')).display")
    b.close()
srv.shutdown()
for k, v in R.items(): print(f"{k}: {v}")
