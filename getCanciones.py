import configparser
import re
import urllib.parse
from pathlib import Path
import os
import psutil
import xml.etree.ElementTree as ET

# ============================================================
# 🔹 Utilidades
# ============================================================
def decode_uri(uri: str) -> str:
    """Convierte file:///C:/...%20... a una ruta legible"""
    if uri.startswith("file:///"):
        uri = uri[8:]
    elif uri.startswith("file://"):
        uri = uri[7:]
    return urllib.parse.unquote(uri.strip('"').strip())

# ============================================================
# 🎵 Canción actual desde vlc-qt-interface.ini
# ============================================================
def get_current_song():
    """Devuelve la última canción reproducida en VLC"""
    appdata = os.getenv("APPDATA")
    vlc_ini = Path(appdata) / "vlc" / "vlc-qt-interface.ini"

    if not vlc_ini.exists():
        print(f"❌ No se encontró el archivo de configuración de VLC en:\n{vlc_ini}")
        return None

    config = configparser.RawConfigParser(strict=False)
    config.optionxform = str  # Mantiene mayúsculas/minúsculas

    try:
        config.read(vlc_ini, encoding="utf-8")
    except Exception as e:
        print(f"❌ Error leyendo el archivo: {e}")
        return None

    last_file = None

    # === [General] -> Último archivo abierto ===
    if config.has_option("General", "filedialog-path"):
        raw_path = config.get("General", "filedialog-path")
        match = re.search(r'file://[^)]+', raw_path)
        if match:
            last_file = decode_uri(match.group(0))

    # === Si no está en [General], buscar en [RecentsMRL] ===
    if not last_file and config.has_option("RecentsMRL", "list"):
        recent_raw = config.get("RecentsMRL", "list")

        # Captura la última URI, con o sin comillas
        uris = re.findall(r'"(file://[^"]+)"|(?<!")\b(file://[^,]+)', recent_raw)
        uris = [decode_uri(u[0] or u[1]) for u in uris if (u[0] or u[1])]
        if uris:
            last_file = uris[0]  # VLC guarda el más reciente al principio

    if last_file:
        print(f"🎧 Canción actual: {Path(last_file).name}")
        return Path(last_file).name
    else:
        print("⚠️ No se encontró ninguna canción actual en VLC.")
        return None

# ============================================================
# 🎶 Playlist actual (XSPF)
# ============================================================
def read_xspf_playlist(playlist_path):
    """Lee y muestra el contenido de una playlist XSPF"""
    print(f"📖 Leyendo playlist: {playlist_path}")
    try:
        with open(playlist_path, 'r', encoding='utf-8') as file:
            content = file.read()

        root = ET.fromstring(content)
        ns = {'ns': 'http://xspf.org/ns/0/'}
        tracks = root.findall('.//ns:track', ns)

        print(f"🎵 {len(tracks)} pistas encontradas:")
        print("-" * 80)

        for i, track in enumerate(tracks, 1):
            location = track.find('ns:location', ns)
            title = track.find('ns:title', ns)
            duration = track.find('ns:duration', ns)

            if location is not None:
                file_path = decode_uri(location.text or "")
                print(f"{i:02d}. 🎶 {os.path.basename(file_path)}")

                if title is not None and title.text:
                    print(f"    🏷️  Título: {title.text}")
                if duration is not None and duration.text:
                    try:
                        print(f"    ⏱️  Duración: {int(duration.text) // 1000} s")
                    except:
                        pass
                print()

    except Exception as e:
        print(f"❌ Error al leer el archivo XSPF: {e}")

def find_vlc_process():
    """Encuentra el proceso de VLC en ejecución"""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and 'vlc' in proc.info['name'].lower():
            return proc.info['pid']
    return None

def get_vlc_playlist():
    """Detecta VLC y muestra su playlist si existe"""
    pid = find_vlc_process()
    if pid:
        print(f"✅ VLC encontrado (PID: {pid})")
        try:
            process = psutil.Process(pid)
            args = process.cmdline()
            print(f"🔧 Argumentos: {args}")

            for arg in args:
                if arg.lower().endswith('.xspf'):
                    read_xspf_playlist(arg)
                    break
            else:
                print("⚠️ No se encontró ningún archivo XSPF en los argumentos de VLC.")
        except Exception as e:
            print(f"❌ Error al leer proceso: {e}")
    else:
        print("❌ VLC no está ejecutándose")

# ============================================================
# 🚀 Ejecución principal
# ============================================================
if __name__ == "__main__":
    current = get_current_song()
    print("\n────────────────────────────────────────────────────────")
    get_vlc_playlist()
