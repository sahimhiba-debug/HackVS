"""Rend docs/presentation/motion/index.html image par image (horloge maîtresse = seek(t)) → MP4 H.264, 1080p, 30 i/s.

    python docs/presentation/motion/rendre.py <ffmpeg> <début_s> <fin_s> <sortie.mp4>

ffmpeg : n'importe quel binaire avec libx264 (par ex. `pip install imageio-ffmpeg`). Version complète : 0 → 610 s ;
plusieurs segments en parallèle se recollent avec `ffmpeg -f concat`. Le rendu ne dépend que du temps : deux rendus
du même fichier donnent les mêmes images."""
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright
FF = sys.argv[1]; t0 = float(sys.argv[2]); t1 = float(sys.argv[3]); out = sys.argv[4]; fps = 30
from pathlib import Path
URL = (Path(__file__).resolve().parent / "index.html").as_uri() + "?rendu=1"
n0, n1 = round(t0 * fps), round(t1 * fps)
ff = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-tune", "animation", out], stdin=subprocess.PIPE)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto(URL); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(800)
    d = time.time()
    for n in range(n0, n1):
        pg.evaluate(f"seek({n / fps})")
        ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
    b.close()
ff.stdin.close(); ff.wait()
print(out, n1 - n0, "images", round(time.time() - d, 1), "s")
