"""
Build the project website (one self-contained HTML file with hash-routed pages).

    python simulator/build_sim.py      # first: refresh the gate engine
    python website/build_site.py

Pages: Overview, Start here (beginner chapters), Virtual lab, Architecture, Cadence flow,
Results, Netlists.

Output:
  website/index.html          open in a browser, or upload to any static host (GitHub Pages, Netlify)
  website/_artifact.html      same page without the <html>/<head> wrapper, for publishing as an Artifact
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


def main():
    lab = read("simulator", "src", "lab.html")
    lab_css = re.search(r"<style>(.*?)</style>", lab, re.S).group(1)
    lab_body = lab[lab.index('<div class="wrap">'):lab.index("<script>")]
    scripts = re.findall(r"<script>(.*?)</script>", lab, re.S)
    lab_js = scripts[1]
    assert "/*@@ENGINE@@*/" in scripts[0]
    engine = read("simulator", "alu_engine.js")

    files = {}
    for name in ["cells.scs", "alu8.scs", "tb_alu8.scs", "tb_alu8_noiso.scs", "alu8_check.ocn"]:
        files[name] = read("virtuoso", name)
    files["alu_gates.py"] = read("model", "alu_gates.py")
    files_json = json.dumps(files).replace("</", "<\\/")

    site = read("website", "src", "site.html")
    parts = {
        "/*@@LAB_CSS@@*/": lab_css,
        "/*@@LEARN_CSS@@*/": read("website", "src", "learn.css"),
        "<!--@@LEARN@@-->": read("website", "src", "learn.html"),
        "<!--@@LAB_BODY@@-->": lab_body,
        "/*@@ENGINE@@*/": engine,
        "/*@@LAB_JS@@*/": lab_js,
        "/*@@FILES@@*/ {}": files_json,
        "/*@@LEARN_JS@@*/": read("website", "src", "learn.js"),
    }
    for key, val in parts.items():
        assert site.count(key) == 1, key
        site = site.replace(key, val)

    with open(os.path.join(HERE, "_artifact.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(site)
    head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(head + site + "\n</html>\n")
    print(f"wrote website/index.html ({len(site) // 1024} KB) and website/_artifact.html")


if __name__ == "__main__":
    main()
