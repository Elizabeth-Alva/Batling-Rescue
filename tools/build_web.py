#!/usr/bin/env python3
"""Compila Batling Rescue para el navegador (WebAssembly) con pygbag.

Uso:  python tools/build_web.py [--zip]
Requiere:  pip install -r requirements-web.txt

1. Copia solo el juego (sin tests ni herramientas) a web_build/batlingrescue/
2. Exporta los sonidos a .ogg dentro de esa carpeta (sounds/)
3. Ejecuta pygbag --build
4. Deja el sitio listo para publicar en web_build/site/ (con .nojekyll para GitHub Pages)
   --zip además genera web_build/batlingrescue.zip para subirlo a itch.io
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web_build")
APP = os.path.join(OUT, "batlingrescue")
SITE = os.path.join(OUT, "site")


def stage():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(os.path.join(APP, "scenes"))
    os.makedirs(os.path.join(APP, "assets"))
    for fn in os.listdir(ROOT):
        if fn.endswith(".py"):
            shutil.copy(os.path.join(ROOT, fn), APP)
    for fn in os.listdir(os.path.join(ROOT, "scenes")):
        if fn.endswith(".py"):
            shutil.copy(os.path.join(ROOT, "scenes", fn), os.path.join(APP, "scenes"))
    scenes_img = os.path.join(ROOT, "assets", "escenas")              # imágenes opcionales de las cinemáticas
    if os.path.isdir(scenes_img):
        dest = os.path.join(APP, "assets", "escenas")
        os.makedirs(dest, exist_ok=True)
        for fn in os.listdir(scenes_img):
            if fn.lower().endswith((".png", ".jpg", ".jpeg")):
                shutil.copy(os.path.join(scenes_img, fn), dest)
    music = os.path.join(ROOT, "assets", "music")                       # canciones (.ogg): el Can-Can de la victoria
    if os.path.isdir(music):
        shutil.copytree(music, os.path.join(APP, "assets", "music"),
                        ignore=shutil.ignore_patterns("*.txt", "*.md"))
    logo = os.path.join(ROOT, "assets", "logo.png")                   # logo oficial (portada) y favicon del sitio
    if os.path.exists(logo):
        shutil.copy(logo, os.path.join(APP, "assets"))
        icon = os.path.join(ROOT, "assets", "promo", "icono.png")
        shutil.copy(icon if os.path.exists(icon) else logo, os.path.join(APP, "favicon.png"))
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "export_sounds.py"), os.path.join(APP, "sounds")],
                   check=True)


VIEWPORT = ('<meta name="viewport" content="width=device-width, initial-scale=1.0, '
            'maximum-scale=1.0, user-scalable=no, viewport-fit=cover">')


def fix_page(path):
    """Arregla la página que genera pygbag para que en el celular no se vea aplastada.
    La plantilla trae DOS etiquetas viewport y la segunda (height=device-height) anula a la primera
    (width=device-width): el teléfono mide mal el ancho de la pantalla y el juego sale deformado.
    Se dejan en una sola, sin zoom con los dedos, y el fondo alrededor del juego en negro (no gris)."""
    with open(path, encoding="utf-8") as f:
        html = f.read()
    html = re.sub(r'\s*<meta name="viewport"[^>]*>', '', html)
    html = html.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n    ' + VIEWPORT, 1)
    html = html.replace('platform.document.body.style.background = "#7f7f7f"',
                        'platform.document.body.style.background = "#000000"')
    html = html.replace('background-color:powderblue;', 'background-color:#000000;')
    if html.count('name="viewport"') != 1:
        raise SystemExit("index.html: no se pudo arreglar la etiqueta viewport")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def build(make_zip):
    cmd = [sys.executable, "-m", "pygbag", "--build", "--no_opt", "--title", "BATling Rescue",
           "--app_name", "batlingrescue"]
    if make_zip:
        cmd.append("--archive")
    subprocess.run(cmd + [APP], check=True)
    shutil.copytree(os.path.join(APP, "build", "web"), SITE)
    fix_page(os.path.join(SITE, "index.html"))
    open(os.path.join(SITE, ".nojekyll"), "w").close()          # GitHub Pages: no procesar con Jekyll
    if make_zip and os.path.exists(os.path.join(APP, "build", "web.zip")):
        shutil.copy(os.path.join(APP, "build", "web.zip"), os.path.join(OUT, "batlingrescue.zip"))


if __name__ == "__main__":
    stage()
    build("--zip" in sys.argv)
    print(f"\nListo: {SITE}")
    print("Prueba local:  python -m pygbag web_build/batlingrescue   y abre http://localhost:8000")
