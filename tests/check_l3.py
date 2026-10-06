#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificarea automată a sarcinii L3 (depozitul personal), DCTC.

Utilizare (din rădăcina depozitului): python3 tests/check_l3.py <test>   sau   python3 tests/check_l3.py all
    readme        README completat: „Despre mine” (min. 20 de cuvinte) și „Instrumente” (min. 3 elemente de listă)   2 p
    despre-mine   fișierul despre-mine.md există și are cel puțin 50 de cuvinte                                          1 p
    commits       cel puțin 3 commit-uri ale studentului (fără cele ale șablonului)                                        3 p
    messages      toate commit-urile studentului au mesaje de cel puțin 10 caractere și două cuvinte                      2 p
    hygiene       .gitignore prezent, niciun fișier peste 5 MB, niciun secret sau fișier .env / .pem / .key               2 p
    all           toate testele, cu tabelul punctelor (Markdown), pentru rezumatul din Actions                       10 p
Codul de ieșire 0 înseamnă test trecut (la `all`: toate testele trecute). Mesajele explică studentului ce lipsește.
Cu --json, `all` scrie rezultatul ca JSON (folosit de scriptul titularului).
"""
import re
import subprocess
import sys
from pathlib import Path

MB = 1024 * 1024
PLACEHOLDER = re.compile(r"<[^<>\n]{0,60}[A-Za-zăâîșțĂÂÎȘȚ][^<>\n]{0,300}>")
TIPARE_SECRETE = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9\-_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{30,}"),
    re.compile(r"(?i)\b(?:password|parola|passwd|api[_-]?key|secret[_-]?key|token)\b\s*[:=]\s*['\"][^'\"\s]{6,}['\"]"),
]


MESAJE = []


def esec(mesaj: str) -> int:
    MESAJE.append(mesaj)
    print("NU A TRECUT: " + mesaj)
    return 1


def ok(mesaj: str) -> int:
    MESAJE.append(mesaj)
    print("TRECUT: " + mesaj)
    return 0


def sectiune(text: str, titlu: str) -> str:
    """Conținutul de sub „## titlu” până la următorul „## ”."""
    m = re.search(r"^## +" + re.escape(titlu) + r"\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def de(n: int) -> str:
    """„20 de cuvinte”, dar „3 cuvinte” și „101 cuvinte” (regula numeralelor în română)."""
    return "de " if n % 100 >= 20 or (n and n % 100 == 0) else ""


def cuvinte(text: str) -> int:
    return len(re.findall(r"\w+", PLACEHOLDER.sub("", text)))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout.decode("utf-8", "replace")


def commituri_student():
    """(hash, subiect) pentru commit-urile studentului: fără commit-ul de creare din șablon și fără roboți."""
    linii = git("log", "--format=%H%x09%an%x09%ae%x09%s").splitlines()
    rezultat = []
    for l in linii:
        h, nume, email, subiect = (l.split("\t") + ["", "", ""])[:4]
        autor = (nume + " " + email).lower()
        if "[bot]" in autor:
            continue
        if subiect.strip().lower() in {"initial commit", "template", "sablon"}:
            continue
        rezultat.append((h, subiect))
    return rezultat


def test_readme() -> int:
    readme = Path("README.md")
    if not readme.is_file():
        return esec("README.md lipsește.")
    text = readme.read_text(encoding="utf-8", errors="replace")
    despre = sectiune(text, "Despre mine")
    if cuvinte(despre) < 20:
        return esec(f"secțiunea „## Despre mine” are {cuvinte(despre)} {de(cuvinte(despre))}cuvinte; sunt necesare cel puțin 20 (fără textul dintre <...>).")
    instrumente = sectiune(text, "Instrumente")
    elemente = [l for l in instrumente.splitlines() if re.match(r"^\s*[-*]\s+\S", l) and not PLACEHOLDER.search(l)]
    if len(elemente) < 3:
        return esec(f"secțiunea „## Instrumente” are {len(elemente)} elemente de listă completate; sunt necesare cel puțin 3.")
    ramase = PLACEHOLDER.findall(text)
    if ramase:
        return esec(f"README.md mai are {len(ramase)} câmpuri necompletate de forma <...>, de exemplu {ramase[0]}.")
    return ok("README.md este completat.")


def test_despre_mine() -> int:
    f = Path("despre-mine.md")
    if not f.is_file():
        return esec("fișierul despre-mine.md lipsește (atenție la numele exact, cu cratimă).")
    n = cuvinte(f.read_text(encoding="utf-8", errors="replace"))
    if n < 50:
        return esec(f"despre-mine.md are {n} {de(n)}cuvinte; sunt necesare cel puțin 50.")
    return ok(f"despre-mine.md are {n} {de(n)}cuvinte.")


def test_commits() -> int:
    c = commituri_student()
    if len(c) < 3:
        return esec(f"există {len(c)} {de(len(c))}commit-uri ale tale; sunt necesare cel puțin 3 (verifică și că user.name și user.email din Git sunt cele de pe GitHub).")
    return ok(f"{len(c)} {de(len(c))}commit-uri ale studentului.")


def test_messages() -> int:
    c = commituri_student()
    if not c:
        return esec("nu există commit-uri ale studentului.")
    slabe = [s for _, s in c if len(s.strip()) < 10 or len(s.split()) < 2]
    if slabe:
        return esec("mesaje de commit prea scurte sau dintr-un singur cuvânt: " + "; ".join(f"„{s}”" for s in slabe[:5]))
    return ok("toate mesajele de commit au cel puțin 10 caractere și două cuvinte.")


def test_hygiene() -> int:
    if not Path(".gitignore").is_file():
        return esec(".gitignore lipsește (nu îl șterge din depozit).")
    fisiere = [f for f in git("ls-files").splitlines() if f]
    for f in fisiere:
        if re.search(r"(^|/)\.env(\..*)?$|\.pem$|\.key$", f):
            return esec(f"fișier interzis în depozit: {f}")
        p = Path(f)
        if p.is_file() and p.stat().st_size > 5 * MB:
            return esec(f"fișierul {f} depășește 5 MB.")
    for f in fisiere:
        p = Path(f)
        if f.startswith("tests/") or not p.is_file() or p.stat().st_size > MB:
            continue
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if p.suffix.lower() == ".ipynb":  # imaginile din rezultate (base64) nu sunt text de verificat
            text = re.sub(r'"image/(?:png|jpeg)":\s*(?:"[^"]*"|\[[^\]]*\])', "", text)
        if any(t.search(text) for t in TIPARE_SECRETE):
            return esec(f"posibil secret (parolă, cheie, token) în {f}; șterge-l și schimbă cheia.")
    return ok("fără fișiere mari, secrete sau fișiere interzise.")


TESTE = {
    "readme": (test_readme, "README completat", 2),
    "despre-mine": (test_despre_mine, "Fișierul despre-mine.md", 1),
    "commits": (test_commits, "Cel puțin trei commit-uri proprii", 3),
    "messages": (test_messages, "Mesaje de commit clare", 2),
    "hygiene": (test_hygiene, "Igiena depozitului", 2),
}


def toate(ca_json: bool = False) -> int:
    import contextlib, io, json
    rezultate = []
    for cheie, (f, nume, puncte) in TESTE.items():
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                cod = f()
            except Exception as e:  # un depozit stricat nu oprește celelalte teste
                cod = esec(f"eroare la verificare: {e}")
        rezultate.append(dict(test=cheie, criteriu=nume, maxim=puncte, puncte=0 if cod else puncte, mesaj=MESAJE[-1] if MESAJE else ""))
    total = sum(r["puncte"] for r in rezultate)
    if ca_json:
        print(json.dumps(dict(total=total, rezultate=rezultate), ensure_ascii=False))
    else:
        print(f"## Verificarea L3: {total} din 10 puncte\n")
        print("| Criteriul | Puncte | Ce a găsit verificarea |")
        print("| --- | --- | --- |")
        for r in rezultate:
            print(f"| {r['criteriu']} | {r['puncte']} din {r['maxim']} | {r['mesaj'].replace('|', '/')} |")
        print("\nRezultatul final se stabilește la termen, din ultima versiune a depozitului.")
    return 0 if total == 10 else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args == ["all"]:
        sys.exit(toate("--json" in sys.argv))
    if len(args) != 1 or args[0] not in TESTE:
        print(__doc__)
        sys.exit(2)
    sys.exit(TESTE[args[0]][0]())
