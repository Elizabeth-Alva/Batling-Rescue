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
    for fn in os.listdir(ROOT):
        if fn.endswith(".py"):
            shutil.copy(os.path.join(ROOT, fn), APP)
    for fn in os.listdir(os.path.join(ROOT, "scenes")):
        if fn.endswith(".py"):
            shutil.copy(os.path.join(ROOT, "scenes", fn), os.path.join(APP, "scenes"))
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "export_sounds.py"), os.path.join(APP, "sounds")],
                   check=True)


def build(make_zip):
    cmd = [sys.executable, "-m", "pygbag", "--build", "--no_opt", "--title", "Batling Rescue",
           "--app_name", "batlingrescue"]
    if make_zip:
        cmd.append("--archive")
    subprocess.run(cmd + [APP], check=True)
    shutil.copytree(os.path.join(APP, "build", "web"), SITE)
    open(os.path.join(SITE, ".nojekyll"), "w").close()          # GitHub Pages: no procesar con Jekyll
    if make_zip and os.path.exists(os.path.join(APP, "build", "web.zip")):
        shutil.copy(os.path.join(APP, "build", "web.zip"), os.path.join(OUT, "batlingrescue.zip"))


if __name__ == "__main__":
    stage()
    build("--zip" in sys.argv)
    print(f"\nListo: {SITE}")
    print("Prueba local:  python -m pygbag web_build/batlingrescue   y abre http://localhost:8000")
