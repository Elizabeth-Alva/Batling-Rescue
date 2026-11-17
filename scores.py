"""Récords de tiempo de la historia completa (los 3 niveles). Menos tiempo = mejor lugar.

Se guardan solos (sin nombre): en records.json (junto al juego, o en la carpeta del usuario si es el .exe)
o en el localStorage del navegador (web).
Cada marca: {"time": 812.55, "date": "09/11/2026 20:15"}.
"""
import json
import os
import sys
import time

from settings import IS_WEB

TOP_N = 10


def _records_path():
    """Dónde se guardan los récords en la computadora.
    · Jugando desde el código (python main.py / JUGAR.bat): records.json junto al juego, como siempre.
    · Como aplicación (.exe hecho con PyInstaller): en la carpeta del usuario (%APPDATA%\\BatlingRescue en Windows),
      porque la carpeta del .exe es temporal y se borra al cerrar el juego."""
    if not getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'records.json')
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    folder = os.path.join(base, 'BatlingRescue')
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        pass
    return os.path.join(folder, 'records.json')


_FILE = _records_path()
_WEB_KEY = 'batling_rescue_records'
_data = None


def fmt(t, cents=True):
    """123.456 -> '2:03.46' (o '2:03' sin centésimas)."""
    t = max(0.0, t)
    m, s = int(t // 60), t % 60
    if cents and round(s, 2) >= 60:                       # 59.999 no debe verse como 0:60.00
        m, s = m + 1, 0.0
    return f'{m}:{s:05.2f}' if cents else f'{m}:{int(s):02d}'


# ------------------------------------------------------------ almacenamiento
def _read():
    try:
        if IS_WEB:
            import platform
            raw = platform.window.localStorage.getItem(_WEB_KEY)
            return json.loads(str(raw)) if raw else {}
        if os.path.exists(_FILE):
            with open(_FILE, encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _write():
    try:
        raw = json.dumps(_data, ensure_ascii=False, indent=1)
        if IS_WEB:
            import platform
            platform.window.localStorage.setItem(_WEB_KEY, raw)
        else:
            with open(_FILE, 'w', encoding='utf-8') as f:
                f.write(raw)
    except Exception:
        pass                                  # sin permisos de escritura: el juego sigue igual


def _db():
    global _data
    if _data is None:
        _data = _read()
        if not isinstance(_data, dict):
            _data = {}
    return _data


def use_memory(data=None):
    """Para pruebas: trabaja en memoria sin tocar el disco."""
    global _data, _write
    _data = data if data is not None else {}
    _write = lambda: None                     # noqa: E731


# ------------------------------------------------------------ consultas
def top():
    rows = _db().get('historia', [])
    return sorted((r for r in rows if isinstance(r, dict) and isinstance(r.get('time'), (int, float))),
                  key=lambda r: r['time'])[:TOP_N]


def best():
    rows = top()
    return rows[0]['time'] if rows else None


def add(t):
    """Guarda el tiempo de una historia completa; devuelve su lugar (0 = primero) o None si no entró al TOP."""
    t = round(t, 2)
    row = {'time': t, 'date': time.strftime('%d/%m/%Y %H:%M')}
    rows = top() + [row]
    rows.sort(key=lambda r: r['time'])
    rows = rows[:TOP_N]
    _db()['historia'] = rows
    _write()
    for i, r in enumerate(rows):
        if r is row:
            return i
    return None
