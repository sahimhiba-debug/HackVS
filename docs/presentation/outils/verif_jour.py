import functools, http.server, socketserver, threading
from playwright.sync_api import sync_playwright
DECK = "/home/user/HackVS/docs/presentation/deck"
class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=DECK)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
CONTR = """() => {
  const lum = c => { const v = c.match(/[\\d.]+/g).slice(0,3).map(Number).map(x => { x/=255; return x<=.03928? x/12.92 : Math.pow((x+.055)/1.055,2.4); }); return .2126*v[0]+.7152*v[1]+.0722*v[2]; };
  const fond = el => { while (el) { const b = getComputedStyle(el).backgroundColor; if (b && !b.startsWith('rgba(0, 0, 0, 0)') && b !== 'transparent') return b; el = el.parentElement; } return 'rgb(255,255,255)'; };
  const echecs = []; let n = 0; let min = 99;
  for (const s of document.querySelectorAll('.slide')) { s.classList.add('active'); if (s.dataset.film) s.classList.add('film-ko');
    for (const el of s.querySelectorAll('*')) { if (![...el.childNodes].some(x => x.nodeType===3 && x.textContent.trim())) continue;
      const L1 = lum(getComputedStyle(el).color), L2 = lum(fond(el)); const r = (Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05);
      const fs = parseFloat(getComputedStyle(el).fontSize); const seuil = fs >= 24 ? 3 : 4.5; n++; min = Math.min(min, r);
      if (r < seuil) echecs.push([s.dataset.id, el.textContent.trim().slice(0,30), r.toFixed(2)]); }
    s.classList.remove('active'); }
  return {textes: n, ratio_min: min.toFixed(2), echecs}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    for mode in ["nuit", "jour"]:
        pg = b.new_page(viewport={"width": 1920, "height": 1080}); pg.goto(f"http://127.0.0.1:{port}/index.html?mode={mode}"); pg.evaluate("window.pret"); pg.wait_for_timeout(2700)
        print(mode, "mode lu:", pg.evaluate("modeDeck()"), "| contraste AA:", pg.evaluate(CONTR)); pg.close()
    pg = b.new_page(viewport={"width": 1920, "height": 1080}); pg.goto(f"http://127.0.0.1:{port}/index.html"); pg.evaluate("window.pret")
    print("défaut:", pg.evaluate("modeDeck()"))
    pg.keyboard.press("j"); pg.wait_for_timeout(400)
    print("J →", pg.evaluate("modeDeck()"), "| annonce:", pg.evaluate("[document.getElementById('bascule').textContent, getComputedStyle(document.getElementById('bascule')).opacity]"))
    pg.wait_for_timeout(2400); print("annonce après 2,4 s, opacité:", pg.evaluate("getComputedStyle(document.getElementById('bascule')).opacity"))
    pg.keyboard.press("n"); pg.wait_for_timeout(400); print("N en jour, fond:", pg.evaluate("getComputedStyle(document.getElementById('noir')).backgroundColor"))
    pg.keyboard.press("n"); pg.reload(); pg.evaluate("window.pret"); print("après rechargement:", pg.evaluate("modeDeck()"))
    pg.keyboard.press("j"); pg.wait_for_timeout(300); pg.keyboard.press("n"); pg.wait_for_timeout(400); print("N en nuit, fond:", pg.evaluate("getComputedStyle(document.getElementById('noir')).backgroundColor"))
    b.close()
srv.shutdown()
