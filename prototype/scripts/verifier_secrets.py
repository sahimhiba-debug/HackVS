"""Aucun secret dans le dépôt : parcourt les fichiers SUIVIS par git et échoue (code 1) sur toute forme de clé connue ou
toute variable sensible affectée d'une valeur. Lancé par `make quality-check` et par la CI.

Faux positifs : les valeurs de TEST sont reconnaissables (« test », « exemple », « faux ») et admises ; tout autre cas
doit être corrigé, pas ignoré."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
MOTIFS = {
    "clé Anthropic": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "clé de type OpenAI": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "jeton GitHub": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "clé AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "clé privée": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "variable sensible affectée": re.compile(
        # « = » suivi d'une valeur sur la MÊME ligne, ou « : » suivi d'une valeur entre guillemets (YAML, JSON) — jamais une
        # valeur vide, une phrase (« JETON : derrière… ») ni une expansion shell (« ${JETON:?…} »)
        r"\b(APERTUS_API_KEY|ANTHROPIC_API_KEY|HACKVS_SECRET|HACKVS_CONSOLE_JETON|HACKVS_MCP_JETON)"
        r"(?:[ \t]*=[ \t]*['\"]?([^\s'\"$<{?]{8,})|[ \t]*:[ \t]*['\"]?([^\s'\"$<{?]{8,})['\"]?[ \t]*$)", re.M),
}
ADMIS = re.compile(r"test|exemple|example|faux|fake|dummy|xxx|votre|your|\.\.\.|changeme", re.I)
IGNORES = (".png", ".jpg", ".jpeg", ".webm", ".mp4", ".pdf", ".ico", ".onnx", ".db", ".woff2", ".pptx")


def fichiers() -> list[Path]:
    sortie = subprocess.run(["git", "ls-files", "-z"], cwd=RACINE, capture_output=True, check=True).stdout
    return [RACINE / f for f in sortie.decode().split("\0") if f and not f.endswith(IGNORES)]


def analyser(texte: str) -> list[tuple[str, str]]:
    trouves = []
    for nom, motif in MOTIFS.items():
        for m in motif.finditer(texte):
            valeur = next((g for g in reversed(m.groups()) if g), m.group(0)) if m.groups() else m.group(0)
            if not ADMIS.search(valeur):
                trouves.append((nom, valeur[:6] + "…"))           # jamais la valeur entière, même dans ce rapport
    return trouves


def main() -> int:
    problemes = 0
    for f in fichiers():
        try:
            texte = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for nom, debut in analyser(texte):
            problemes += 1
            print(f"SECRET PROBABLE · {f.relative_to(RACINE)} · {nom} · {debut}")
    print("aucun secret trouvé" if not problemes else f"{problemes} secret(s) probable(s)")
    return 1 if problemes else 0


if __name__ == "__main__":
    sys.exit(main())
