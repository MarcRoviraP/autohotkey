import subprocess
import os
import winreg
import keyboard
import tkinter as tk
from tkinter import font as tkfont
import threading
import re
import xml.etree.ElementTree as ET
import configparser
import urllib.parse
from pathlib import Path
import psutil
import tempfile
import shutil
import tempfile, os, xml.etree.ElementTree as ET
from pathlib import Path

# ---------- registra namespaces UNA vez ----------
import os, tempfile, xml.etree.ElementTree as ET

# registra los namespaces (una sola vez al importar)
ET.register_namespace('', 'http://xspf.org/ns/0/')
ET.register_namespace('vlc', 'http://www.videolan.org/vlc/playlist/ns/0/')

def build_rotated_xspf(original_path: str, idx: int) -> str:
    tmp_playlist = os.path.join(tempfile.gettempdir(), "vlc_rotada.xspf")

    tree = ET.parse(original_path)
    root = tree.getroot()

    # extrae pistas (con URI completa)
    tracks = root.findall('.//{http://xspf.org/ns/0/}track')

    # rotar
    rotated = tracks[idx:] + tracks[:idx]

    # limpiar trackList
    tracklist = root.find('.//{http://xspf.org/ns/0/}trackList')
    tracklist.clear()

# 4. re-numerar <vlc:id> de cada track
    for new_idx, trk in enumerate(rotated):
        vlc_ext = trk.find('{http://xspf.org/ns/0/}extension')
        if vlc_ext is not None:
            vlc_id = vlc_ext.find('{http://www.videolan.org/vlc/playlist/ns/0/}id')
            if vlc_id is not None:
                vlc_id.text = str(new_idx)
                print(f'     └─ vlc:id {vlc_id.text} → {new_idx}')
            else:
                print('     └─ vlc:id no encontrado')
        else:
            print('     └─ extension no encontrada')
        # volcar rotadas
    for trk in rotated:
        tracklist.append(trk)

    # guardar SIN default_namespace → usa prefijos ns0, vlc, etc.
    tree.write(tmp_playlist, encoding='utf-8', xml_declaration=True)
    return tmp_playlist

# ============================================================
# 🔹 Utilidades VLC
# ============================================================

def find_vlc():
    """Busca la ruta de VLC en Windows dinámicamente."""
    common_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path

    # Registro de Windows
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC")
        vlc_dir, _ = winreg.QueryValueEx(key, "InstallDir")
        vlc_exe = os.path.join(vlc_dir, "vlc.exe")
        if os.path.isfile(vlc_exe):
            return vlc_exe
    except FileNotFoundError:
        pass

    return None

def decode_uri(uri: str) -> str:
    """Convierte file:///C:/...%20... a una ruta legible"""
    uri = uri.strip('"').strip()
    if uri.startswith("file:///"):
        uri = uri[8:]
    elif uri.startswith("file://"):
        uri = uri[7:]
    return urllib.parse.unquote(uri)

def close_vlc():
    """Cierra cualquier instancia de VLC en ejecución"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'vlc' in proc.info['name'].lower():
            proc.kill()

def get_current_song():
    """Obtiene la última canción reproducida en VLC desde vlc-qt-interface.ini"""
    appdata = os.getenv("APPDATA")
    vlc_ini = Path(appdata) / "vlc" / "vlc-qt-interface.ini"
    if not vlc_ini.exists():
        return "❌ No se encontró la configuración de VLC"

    config = configparser.RawConfigParser(strict=False)
    config.optionxform = str
    try:
        config.read(vlc_ini, encoding="utf-8")
    except Exception as e:
        return f"❌ Error leyendo el archivo: {e}"

    last_file = None
    if config.has_option("General", "filedialog-path"):
        raw_path = config.get("General", "filedialog-path")
        match = re.search(r'file://[^)]+', raw_path)
        if match:
            last_file = decode_uri(match.group(0))

    if not last_file and config.has_option("RecentsMRL", "list"):
        recent_raw = config.get("RecentsMRL", "list")
        uris = re.findall(r'"(file://[^"]+)"|(?<!")\b(file://[^,]+)', recent_raw)
        uris = [decode_uri(u[0] or u[1]) for u in uris if (u[0] or u[1])]
        if uris:
            last_file = uris[0]

    if not last_file:
        return "⚠️ No se detectó ninguna canción reciente."

    return Path(last_file).stem

# ============================================================
# 🎛️ Controlador principal VLC
# ============================================================
class VLCController:
    def __init__(self):
        self.tooltip_window = None
        self.tooltip_timer = None
        self.root = None
        self.playlist_window = None

    # --- Interfaz Tk ---
    def init_tkinter(self):
        if self.root is None:
            self.root = tk.Tk()
            self.root.withdraw()
            self.root.attributes('-topmost', True)

    # --- Tooltip ---
    def show_custom_tooltip(self, text):
        self.close_tooltip()
        if not text.strip():
            return

        if not self.root:
            self.init_tkinter()

        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.attributes('-topmost', True)
        self.tooltip_window.config(bg="#404040")

        label = tk.Label(
            self.tooltip_window, text=text,
            font=tkfont.Font(family="Calibri", size=10, weight='bold'),
            fg="#F3F3F3", bg="#101010", justify=tk.LEFT,
            padx=8, pady=8
        )
        label.pack(padx=1, pady=1)

        self.tooltip_window.update_idletasks()
        width, height = self.tooltip_window.winfo_reqwidth(), self.tooltip_window.winfo_reqheight()
        screen_width, screen_height = self.tooltip_window.winfo_screenwidth(), self.tooltip_window.winfo_screenheight()
        self.tooltip_window.geometry(f'+{screen_width - width - 20}+{screen_height - height - 60}')
        self.tooltip_window.deiconify()
        self.tooltip_window.lift()

        # Auto-cerrar
        if self.tooltip_timer:
            self.tooltip_timer.cancel()
        self.tooltip_timer = threading.Timer(5.0, self.close_tooltip)
        self.tooltip_timer.start()

    def close_tooltip(self):
        if self.tooltip_timer:
            self.tooltip_timer.cancel()
            self.tooltip_timer = None
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None

    def show_song_tooltip(self):
        info = get_current_song()
        print(f"ℹ️ Tooltip info: {info}")
        if self.root:
            self.root.after(0, lambda: self.show_custom_tooltip(info))

    # --- Playlist ---
    def find_vlc_process(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and 'vlc' in proc.info['name'].lower():
                return proc.info['pid']
        return None

    def get_vlc_playlist_path(self):
        pid = self.find_vlc_process()
        if not pid:
            print("❌ VLC no está ejecutándose")
            return None

        try:
            process = psutil.Process(pid)
            for arg in process.cmdline():
                if arg.lower().endswith('.xspf'):
                    return arg
            return None
        except Exception as e:
            print(f"❌ Error al leer proceso: {e}")
            return None

    def read_xspf_playlist(self, playlist_path):
        playlist = []
        try:
            tree = ET.parse(playlist_path)
            root = tree.getroot()
            ns = {'ns': 'http://xspf.org/ns/0/'}
            for track in root.findall('.//ns:track', ns):
                title = track.find('ns:title', ns)
                location = track.find('ns:location', ns)
                playlist.append({
                    "title": title.text if title is not None else "Desconocido",
                    "location": decode_uri(location.text) if location is not None else ""
                })
        except Exception as e:
            print(f"❌ Error al leer la playlist: {e}")
        return playlist

    def show_playlist_selector(self):
        playlist_path = self.get_vlc_playlist_path()
        if not playlist_path:
            self.show_custom_tooltip("🎵 No se encontró playlist activa")
            return

        playlist = self.read_xspf_playlist(playlist_path)
        if not playlist:
            self.show_custom_tooltip("🎵 Playlist vacía")
            return

        self.close_tooltip()
        if self.playlist_window:
            try:
                self.playlist_window.destroy()
            except: pass
            self.playlist_window = None

        # Ventana
        self.playlist_window = tk.Toplevel(self.root)
        self.playlist_window.title("VLC Playlist")
        self.playlist_window.overrideredirect(True)
        self.playlist_window.attributes('-topmost', True)
        self.playlist_window.configure(bg="#101010")

        frame = tk.Frame(self.playlist_window, bg="#404040", bd=1)
        frame.pack(padx=2, pady=2)

        scrollbar = tk.Scrollbar(frame, bg="#202020")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            frame, font=tkfont.Font(family="Calibri", size=10, weight="bold"),
            bg="#101010", fg="#F3F3F3", selectbackground="#2E8B57",
            selectforeground="#FFFFFF", width=50, height=15,
            activestyle="none", yscrollcommand=scrollbar.set
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH)
        scrollbar.config(command=listbox.yview)

        for i, track in enumerate(playlist, 1):
            listbox.insert(tk.END, f"{i:02d}. {track['title']}")

        def on_select(event, lst=listbox, pl=playlist, self=self):
            sel = lst.curselection()
            if not sel:
                return
            idx = sel[0]
        
            close_vlc()
            vlc = find_vlc()
            if not vlc:
                self.show_custom_tooltip("❌ VLC no encontrado")
                return
        
            # 1. Crear lista rotada
            rotated_path = build_rotated_xspf(playlist_path, idx)
        
            # 2. Lanzar VLC limpio
            subprocess.Popen([vlc, rotated_path],
                                cwd=os.path.dirname(vlc))
        
            self.show_custom_tooltip(f"▶️ {pl[idx]['title']}")

        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Double-Button-1>", on_select)

        # Posicionar ventana
        self.playlist_window.update_idletasks()
        w, h = self.playlist_window.winfo_reqwidth(), self.playlist_window.winfo_reqheight()
        sw, sh = self.playlist_window.winfo_screenwidth(), self.playlist_window.winfo_screenheight()
        self.playlist_window.geometry(f"+{sw - w - 40}+{sh - h - 80}")
        self.playlist_window.deiconify()
        self.playlist_window.lift()
        self.playlist_window.focus_force()
        self.playlist_window.bind("<Escape>", lambda e: self.playlist_window.destroy())
        print("🪄 Playlist selector abierto.")

# ============================================================
# 🚀 Ejecución principal
# ============================================================
def main():
    controller = VLCController()
    controller.init_tkinter()
    print("🎵 VLC Tooltip Ready\nAtajos:\nAlt+Num0 → Mostrar canción actual\nCtrl+Alt+X → Salir")

    keyboard.add_hotkey('alt+num 0', controller.show_song_tooltip)
    keyboard.add_hotkey('ctrl+alt+x', lambda: os._exit(0))
    keyboard.add_hotkey('alt+num enter', controller.show_playlist_selector)

    controller.root.mainloop()

if __name__ == "__main__":
    main()
