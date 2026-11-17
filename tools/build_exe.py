#!/usr/bin/env python3
"""Convierte BATling Rescue en una aplicación de escritorio (un solo archivo que se abre con doble clic).

Uso:  python tools/build_exe.py            (o doble clic en CONSTRUIR_EXE.bat en Windows)
Resultado:
  Windows  ->  dist/BatlingRescue.exe
  Linux    ->  dist/BatlingRescue
  macOS    ->  dist/BatlingRescue   (hay que construirlo en una Mac)

Cómo funciona:
1. Instala lo necesario si falta (PyInstaller para empaquetar y Pillow para el ícono).
2. Hace el ícono de la aplicación a partir del logo (assets/logo.png -> build/icon.ico).
3. Empaqueta con PyInstaller: Python, pygame, el código del juego y la carpeta assets/ (logo y música).
   Las pruebas y las herramientas no se incluyen.

Notas:
- La aplicación se construye para el sistema en el que se ejecuta este script (un .exe solo sale en Windows).
- Los récords de la aplicación se guardan en la carpeta del usuario (%APPDATA%\\BatlingRescue en Windows).
- Los sonidos se siguen generando por código al abrir el juego (tarda un par de segundos, como siempre).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
DIST = os.path.join(ROOT, 'dist')
NAME = 'BatlingRescue'


def ensure(module, package):
    """Instala un paquete si no está."""
    try:
        __import__(module)
    except ImportError:
        print(f'Instalando {package}...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])


def make_icon():
    """Ícono con varios tamaños a partir del logo del juego. Devuelve su ruta o None si no hay logo."""
    logo = os.path.join(ROOT, 'assets', 'logo.png')
    if not os.path.exists(logo):
        print('Aviso: no está assets/logo.png; la aplicación usará el ícono por defecto.')
        return None
    from PIL import Image
    os.makedirs(BUILD, exist_ok=True)
    img = Image.open(logo).convert('RGBA')
    side = max(img.size)                                   # cuadrado (el logo no lo es): se centra sobre transparente
    square = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    ico = os.path.join(BUILD, 'icon.ico')
    square.save(ico, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    return ico


def build():
    ensure('PyInstaller', 'pyinstaller')
    ensure('PIL', 'pillow')
    ensure('pygame', 'pygame')
    ico = make_icon()
    assets = os.path.join(ROOT, 'assets')
    cmd = [sys.executable, '-m', 'PyInstaller',
           '--noconfirm', '--clean',
           '--onefile',                                     # un solo archivo
           '--windowed',                                    # sin ventana negra de consola
           '--name', NAME,
           '--distpath', DIST,
           '--workpath', os.path.join(BUILD, 'pyinstaller'),
           '--specpath', BUILD,
           '--add-data', f'{assets}{os.pathsep}assets',     # logo y música
           '--exclude-module', 'tests',
           '--exclude-module', 'tkinter',
           # pygame usa pkg_resources solo si está (opcional); incluirlo rompe el arranque con algunas versiones
           # de setuptools ("The 'jaraco' package is required"), así que se deja fuera
           '--exclude-module', 'pkg_resources',
           '--exclude-module', 'setuptools']
    if ico:
        cmd += ['--icon', ico]
    cmd.append(os.path.join(ROOT, 'main.py'))
    print('Empaquetando con PyInstaller (tarda un par de minutos)...')
    subprocess.check_call(cmd, cwd=ROOT)
    exe = os.path.join(DIST, NAME + ('.exe' if sys.platform == 'win32' else ''))
    if not os.path.exists(exe):
        sys.exit('No se generó la aplicación; revisa los mensajes de arriba.')
    size = os.path.getsize(exe) / 1e6
    print(f'\nListo: {exe}  ({size:.0f} MB)')
    print('Para compartirlo basta con ese archivo: se abre con doble clic, sin instalar Python.')
    return exe


if __name__ == '__main__':
    if '--clean' in sys.argv:                               # borra lo que dejó una construcción anterior
        shutil.rmtree(os.path.join(BUILD, 'pyinstaller'), ignore_errors=True)
    build()
