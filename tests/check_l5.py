#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificarea automată a sarcinii L5 (notebook-ul individual din Colab), DCTC.

Notebook-ul se salvează din Colab în acest depozit, ca notebooks/l5.ipynb (File > Save a copy in GitHub).
Utilizare (din rădăcina depozitului): python3 tests/check_l5.py <test>   sau   python3 tests/check_l5.py all
    notebook   notebooks/l5.ipynb există și este un notebook valid, sub 5 MB                                     1 p
    rulare     rezultatele salvate sunt ale unei rulări complete: graficele există, nicio eroare, ordinea execuției   2 p
               (cu --executa, notebook-ul se rulează din nou de la zero, ca în Actions)
    parametri  cel puțin doi parametri ai temei schimbați față de șablon (unul: 1 p)                              2 p
    date       datele echipei: URL raw spre data/ din depozitul echipei (analiza) sau tema aleasă (explorare)    1 p
    grafic     o celulă de cod adăugată de tine, cu un grafic afișat (al treilea grafic din notebook)              2 p
    formula    o celulă de text adăugată de tine, cu o formulă LaTeX care nu este în șablon                         1 p
    png        cel puțin o figură PNG pusă în depozit (de exemplu în notebooks/)                            1 p
    all        toate testele, cu tabelul punctelor (Markdown), pentru rezumatul din Actions                      10 p
Codul de ieșire 0 înseamnă test trecut (la `all`: toate testele trecute). Cu --json, `all` scrie rezultatul ca JSON.
"""
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

NOTEBOOK = Path("notebooks/l5.ipynb")
MB = 1024 * 1024

# Amprentele celulelor din șabloanele cursuri-inf/DCTC (generate de build_sabloane.py); nu se modifică.
# <AMPRENTE>
AMPRENTE = {
 "analiza-sablon": {
  "cod": [
   "19f52876e285",
   "2cf39c4f5d16",
   "3f0a1f07e28f",
   "3f80ab1055ce",
   "8756c2f2fb4c",
   "900c05803f27",
   "b92737032250",
   "b941b01f60cf"
  ],
  "text": [
   "0de70887364f",
   "3a19fe62e013",
   "584999c6aec0",
   "661a858c162b",
   "7295a7805d4d",
   "7d80be7f8dcf",
   "a4afe917ce43",
   "b6728d697984",
   "c65fa67a0684",
   "d07f8f7f9ac3"
  ],
  "formule": [
   "\\Delta=\\dfrac{x_{\\mathrm{final}}-x_{\\mathrm{inițial}}}{x_{\\mathrm{inițial}}}\\cdot100\\%",
   "\\bar{x}=\\frac{1}{n}\\sum_{i=1}^{n}x_i,\\qquads=\\sqrt{\\frac{1}{n-1}\\sum_{i=1}^{n}\\left(x_i-\\bar{x}\\right)^2},",
   "x_1,\\dots,x_n"
  ],
  "imagini": 2
 },
 "explorare-sablon": {
  "cod": [
   "1f028fda68c2",
   "48df8b0395a7",
   "6c8ca7e6b271",
   "7dd4795ad01c",
   "81124176b3f1",
   "a4e6df020e79",
   "e2444b5e122e",
   "fdc9323a99d2"
  ],
  "text": [
   "068354520841",
   "14ba46077d49",
   "21b9b0486cf6",
   "3d5d4e341e5f",
   "9279e59a443f",
   "b4c9324fc0e4",
   "c6287a5a6ab1",
   "df0daf402d73",
   "ec6deb1733a3",
   "ecb7fbd86de2",
   "f58ae0623d45"
  ],
  "formule": [
   "(b-a)/2^{k}",
   "1/\\sqrt{n}",
   "\\left|a(x)-\\pi(x)\\right|/\\pi(x)",
   "\\mathrm{Li}(x)=\\displaystyle\\int_2^x\\frac{dt}{\\lnt}",
   "\\pi(x)\\sim\\dfrac{x}{\\lnx}",
   "\\pi\\approx4\\,\\dfrac{k}{n}",
   "a(x)",
   "f",
   "f(n)=3n+1",
   "f(n)=n/2",
   "k",
   "n",
   "x",
   "x_{k+1}=x_k-\\dfrac{f(x_k)}{f'(x_k)}"
  ],
  "imagini": 2
 }
}
# </AMPRENTE>

IMPLICIT = {
    "analiza-sablon": {
        "SEPARATOR": ",", "COLOANA_TIMP": "an", "COLOANA_VALOARE": "valoare", "COLOANA_GRUP": "regiune",
        "GRUPURI": ["Regiunea A", "Regiunea B", "Regiunea C"], "PRINCIPAL": "Regiunea A",
        "TIMP_MIN": 2000, "TIMP_MAX": 2025,
    },
    "explorare-sablon": {"N": 100_000, "N_MIN": 1, "SAMANTA": 12345, "FUNCTIA": 3, "TOLERANTA": 1e-10},
}
RELEVANTI_EXPLORARE = {
    "collatz": ("N", "N_MIN"), "prime": ("N", "N_MIN"),
    "monte_carlo": ("N", "SAMANTA"), "newton_bisectie": ("FUNCTIA", "TOLERANTA"),
}
URL_EXEMPLU = "raw.githubusercontent.com/cursuri-inf/DCTC/"
DESEN = re.compile(r"\bplt\.|\.plot\(|\bax\.|\.hist\(|\.bar\(|\.scatter\(")

MESAJE = []


def esec(mesaj: str) -> int:
    MESAJE.append(mesaj)
    print("NU: " + mesaj)
    return 1


def ok(mesaj: str) -> int:
    MESAJE.append(mesaj)
    print("DA: " + mesaj)
    return 0


def sursa(celula) -> str:
    s = celula.get("source", "")
    return "".join(s) if isinstance(s, list) else s


def amprenta(text: str) -> str:
    linii = [l.strip() for l in text.splitlines()]
    return hashlib.sha1("\n".join(l for l in linii if l).encode("utf-8")).hexdigest()[:12]


def formule(text: str) -> set:
    return {re.sub(r"\s+", "", m) for m in re.findall(r"\$\$?([^$]+?)\$\$?", text)}


def citeste():
    """Notebook-ul ca dicționar, sau None (cu mesajul potrivit în MESAJE)."""
    if not NOTEBOOK.is_file():
        esec("notebooks/l5.ipynb lipsește. În Colab: File > Save a copy in GitHub, depozitul dctc-l3, "
             "ramura main, câmpul File path: notebooks/l5.ipynb.")
        return None
    try:
        nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        esec(f"notebooks/l5.ipynb nu este un notebook valid ({e}).")
        return None
    if not isinstance(nb, dict) or not isinstance(nb.get("cells"), list) or nb.get("nbformat") != 4:
        esec("notebooks/l5.ipynb nu are structura unui notebook Jupyter (nbformat 4).")
        return None
    return nb


def celule(nb, tip):
    return [c for c in nb["cells"] if c.get("cell_type") == tip]


def iesiri(nb):
    return [o for c in celule(nb, "code") for o in c.get("outputs", []) or []]


def numar_imagini(nb) -> int:
    return sum(1 for o in iesiri(nb) if "image/png" in (o.get("data") or {}))


def parametri(nb):
    """(șablonul, dicționarul parametrilor) din celula care atribuie URL_DATE sau TEMA."""
    for c in celule(nb, "code"):
        try:
            arbore = ast.parse(sursa(c))
        except SyntaxError:
            continue
        valori = {}
        for nod in arbore.body:
            if not isinstance(nod, ast.Assign) or len(nod.targets) != 1:
                continue
            tinta, valoare = nod.targets[0], nod.value
            perechi = []
            if isinstance(tinta, ast.Name):
                perechi = [(tinta.id, valoare)]
            elif isinstance(tinta, ast.Tuple) and isinstance(valoare, ast.Tuple) and len(tinta.elts) == len(valoare.elts):
                perechi = [(t.id, v) for t, v in zip(tinta.elts, valoare.elts) if isinstance(t, ast.Name)]
            for nume, v in perechi:
                try:
                    valori[nume] = ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    valori[nume] = ast.dump(v)
        if "URL_DATE" in valori:
            return "analiza-sablon", valori
        if "TEMA" in valori:
            return "explorare-sablon", valori
    return None, {}


def test_notebook() -> int:
    nb = citeste()
    if nb is None:
        return 1
    if NOTEBOOK.stat().st_size > 5 * MB:
        return esec("notebooks/l5.ipynb depășește 5 MB; graficele trebuie să fie PNG obișnuite, nu animații.")
    sablon, _ = parametri(nb)
    if sablon is None:
        return esec("nu găsesc celula de parametri a șablonului (URL_DATE sau TEMA); pornește de la un șablon din cursuri-inf/DCTC.")
    return ok(f"notebooks/l5.ipynb există, pornit din {sablon}.ipynb, {len(nb['cells'])} celule.")


def executa() -> str:
    """Rulează notebook-ul de la zero cu nbconvert; întoarce '' la succes sau mesajul de eroare."""
    r = subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                        str(NOTEBOOK), "--output", "l5-executat.ipynb", "--output-dir", "/tmp",
                        "--ExecutePreprocessor.timeout=600"], capture_output=True, text=True, timeout=900)
    if r.returncode == 0:
        return ""
    text = re.sub(r"\x1b\[[0-9;]*m", "", r.stderr)
    linii = [l.strip() for l in text.splitlines() if l.strip()]
    erori = [l for l in linii if re.match(r"^[A-Za-z_.]*(Error|Exception)\b.*:", l)]
    return (erori[-1] if erori else " / ".join(linii[-2:]))[:300] or "eroare necunoscută"


def test_rulare(cu_executie: bool = False) -> int:
    nb = citeste()
    if nb is None:
        return 1
    erori = [o for o in iesiri(nb) if o.get("output_type") == "error"]
    if erori:
        return esec(f"rezultatele salvate conțin o eroare ({erori[0].get('ename', '')}); rulează din nou "
                    "(Runtime > Restart session and run all) și salvează după ce trec toate celulele.")
    if numar_imagini(nb) < 2:
        return esec("nu găsesc graficele în rezultatele salvate; rulează tot notebook-ul înainte de salvare "
                    "și verifică Edit > Notebook settings: rezultatele nu trebuie omise.")
    ordine = [c.get("execution_count") for c in celule(nb, "code") if c.get("execution_count") is not None]
    if any(b <= a for a, b in zip(ordine, ordine[1:])):
        return esec("celulele au fost rulate în altă ordine decât cea din notebook; "
                    "Runtime > Restart session and run all, apoi salvează din nou.")
    if cu_executie:
        mesaj = executa()
        if mesaj:
            return esec(f"notebook-ul nu rulează de la zero, pe un calculator curat: {mesaj}")
        return ok("notebook-ul rulează de la zero, fără erori, și rezultatele salvate sunt complete.")
    return ok("rezultatele salvate sunt ale unei rulări complete, fără erori.")


def test_parametri() -> int:
    nb = citeste()
    if nb is None:
        return 1
    sablon, valori = parametri(nb)
    if sablon is None:
        return esec("nu găsesc celula de parametri a șablonului.")
    implicit = IMPLICIT[sablon]
    if sablon == "explorare-sablon":
        tema = valori.get("TEMA")
        if tema not in RELEVANTI_EXPLORARE:
            return esec(f"TEMA = {tema!r} nu este una dintre temele șablonului.")
        nume = RELEVANTI_EXPLORARE[tema]
    else:
        nume = tuple(implicit)
    schimbati = [n for n in nume if n in valori and valori[n] != implicit[n]]
    if len(schimbati) >= 2:
        return ok(f"parametrii schimbați față de șablon: {', '.join(schimbati)}.")
    if len(schimbati) == 1:
        esec(f"un singur parametru schimbat ({schimbati[0]}); sunt necesari doi, dintre: {', '.join(nume)}.")
        return 2
    return esec(f"niciun parametru schimbat față de șablon; schimbă doi, dintre: {', '.join(nume)}.")


def test_date() -> int:
    nb = citeste()
    if nb is None:
        return 1
    sablon, valori = parametri(nb)
    if sablon == "explorare-sablon":
        tema = valori.get("TEMA")
        if tema in RELEVANTI_EXPLORARE:
            return ok(f"tema echipei: {tema}; datele sunt generate în notebook.")
        return esec(f"TEMA = {tema!r} nu este una dintre temele șablonului.")
    url = str(valori.get("URL_DATE", ""))
    if URL_EXEMPLU in url:
        return esec("URL_DATE arată încă spre datele de exemplu ale șablonului; pune URL-ul raw al fișierului "
                    "din data/ al depozitului echipei.")
    m = re.match(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/(?:refs/heads/)?[^/]+/(.+)$", url)
    if not m:
        return esec(f"URL_DATE nu este un URL raw de pe GitHub (https://raw.githubusercontent.com/...): {url[:120]}")
    if not m.group(3).startswith("data/"):
        return esec(f"fișierul citit nu este în folderul data/ al depozitului echipei: {m.group(3)}")
    return ok(f"datele se citesc prin URL raw din {m.group(1)}/{m.group(2)}, {m.group(3)}.")


def test_grafic() -> int:
    nb = citeste()
    if nb is None:
        return 1
    sablon, _ = parametri(nb)
    cunoscute = set(AMPRENTE.get(sablon, {}).get("cod", []))
    noi = [c for c in celule(nb, "code") if amprenta(sursa(c)) not in cunoscute and DESEN.search(sursa(c))]
    imagini = numar_imagini(nb)
    minim = AMPRENTE.get(sablon, {}).get("imagini", 2) + 1
    if noi and imagini >= minim:
        return ok(f"graficul tău: {len(noi)} celule de cod noi sau modificate care desenează; {imagini} grafice în notebook.")
    if noi:
        esec(f"ai o celulă nouă care desenează, dar notebook-ul are doar {imagini} grafice salvate; "
             "rulează-l complet înainte de salvare.")
        return 2
    return esec("nu găsesc o celulă de cod adăugată de tine care să deseneze un grafic.")


def test_formula() -> int:
    nb = citeste()
    if nb is None:
        return 1
    sablon, _ = parametri(nb)
    stiute_text = set(AMPRENTE.get(sablon, {}).get("text", []))
    stiute_formule = set(AMPRENTE.get(sablon, {}).get("formule", []))
    for c in celule(nb, "markdown"):
        if amprenta(sursa(c)) in stiute_text:
            continue
        for f in formule(sursa(c)) - stiute_formule:
            if len(f) >= 3 and re.search(r"\\[A-Za-z]+|[\^_=]", f):
                return ok(f"formula ta, într-o celulă de text: ${f[:60]}$")
    return esec("nu găsesc o celulă de text adăugată de tine cu o formulă LaTeX nouă (între $...$).")


def test_png() -> int:
    try:
        fisiere = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        fisiere = [str(p) for p in Path(".").rglob("*.png")]
    png = [f for f in fisiere if f.lower().endswith(".png") and not f.startswith("tests/")]
    if png:
        return ok(f"figuri PNG în depozit: {', '.join(png[:3])}.")
    return esec("nu există nicio figură PNG în depozit; descarcă graficul tău din Colab și pune-l în notebooks/.")


TESTE = {
    "notebook": (test_notebook, "Notebook-ul în depozit", 1),
    "rulare": (test_rulare, "Rulare completă, fără erori", 2),
    "parametri": (test_parametri, "Doi parametri schimbați", 2),
    "date": (test_date, "Datele echipei", 1),
    "grafic": (test_grafic, "Un grafic adăugat de tine", 2),
    "formula": (test_formula, "O formulă LaTeX adăugată de tine", 1),
    "png": (test_png, "Figura PNG în depozit", 1),
}


def puncte(cod: int, maxim: int) -> int:
    """0 = trecut; 2 = jumătate (la testele de 2 puncte); altfel 0 puncte."""
    if cod == 0:
        return maxim
    return 1 if cod == 2 and maxim == 2 else 0


def toate(ca_json: bool = False, cu_executie: bool = False) -> int:
    import contextlib, io
    rezultate = []
    for cheie, (f, nume, maxim) in TESTE.items():
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                cod = f(cu_executie) if cheie == "rulare" else f()
            except Exception as e:  # un notebook stricat nu oprește celelalte teste
                cod = esec(f"eroare la verificare: {e}")
        rezultate.append(dict(test=cheie, criteriu=nume, maxim=maxim, puncte=puncte(cod, maxim),
                              mesaj=MESAJE[-1] if MESAJE else ""))
    total = sum(r["puncte"] for r in rezultate)
    if ca_json:
        print(json.dumps(dict(total=total, rezultate=rezultate), ensure_ascii=False))
    else:
        print(f"## Verificarea L5: {total} din 10 puncte\n")
        print("| Criteriul | Puncte | Ce a găsit verificarea |")
        print("| --- | --- | --- |")
        for r in rezultate:
            print(f"| {r['criteriu']} | {r['puncte']} din {r['maxim']} | {r['mesaj'].replace('|', '/')} |")
        print("\nRezultatul final se stabilește la termen, din ultima versiune a depozitului.")
    return 0 if total == 10 else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    executie = "--executa" in sys.argv
    if args == ["all"]:
        sys.exit(toate("--json" in sys.argv, executie))
    if len(args) != 1 or args[0] not in TESTE:
        print(__doc__)
        sys.exit(2)
    f = TESTE[args[0]][0]
    sys.exit(f(executie) if args[0] == "rulare" else f())
