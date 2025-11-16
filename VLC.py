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
import win32gui
from urllib.parse import unquote
import win32gui
import win32con
import time
# Registra namespaces UNA vez al importar
ET.register_namespace('', 'http://xspf.org/ns/0/')
ET.register_namespace('vlc', 'http://www.videolan.org/vlc/playlist/ns/0/')


# ------------------------------------------------------------------
#  Utilidades XSPF
# ------------------------------------------------------------------
def build_rotated_xspf(original_path: str, idx: int) -> str:
    """
    Crea una playlist temporal rotada a partir de 'original_path'.
    El track que ocupe la posición 'idx' pasará a ser el primero.
    Devuelve la ruta del archivo temporal generado.
    """
    tmp_playlist = os.path.join(tempfile.gettempdir(), "vlc_rotada.xspf")

    tree = ET.parse(original_path)
    root = tree.getroot()

    # Extrae todas las pistas
    tracks = root.findall('.//{http://xspf.org/ns/0/}track')

    # Rota la lista
    rotated = tracks[idx:] + tracks[:idx]

    # Limpia el trackList actual
    tracklist = root.find('.//{http://xspf.org/ns/0/}trackList')
    tracklist.clear()

    # Re-numera vlc:id para mantener consistencia con VLC
    for new_idx, trk in enumerate(rotated):
        vlc_ext = trk.find('{http://xspf.org/ns/0/}extension')
        if vlc_ext is not None:
            vlc_id = vlc_ext.find('{http://www.videolan.org/vlc/playlist/ns/0/}id')
            if vlc_id is not None:
                vlc_id.text = str(new_idx)
                print(f'     |- vlc:id {vlc_id.text} -> {new_idx}')
            else:
                print('     |- vlc:id no encontrado')
        else:
            print('     |- extension no encontrada')

    # Vuelca las pistas rotadas
    for trk in rotated:
        tracklist.append(trk)

    # Guarda el XML temporal (usa prefijos ns0, vlc, etc.)
    tree.write(tmp_playlist, encoding='utf-8', xml_declaration=True)
    return tmp_playlist


# ------------------------------------------------------------------
#  Utilidades VLC
# ------------------------------------------------------------------
def find_vlc() -> str | None:
    """
    Devuelve la ruta completa a vlc.exe buscando en ubicaciones comunes
    y en el registro de Windows. None si no se encuentra.
    """
    common_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path

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
    """
    Convierte URIs tipo file:///C:/...%20... a ruta local legible.
    """
    uri = uri.strip('"').strip()
    if uri.startswith("file:///"):
        uri = uri[8:]
    elif uri.startswith("file://"):
        uri = uri[7:]
    return urllib.parse.unquote(uri)


def close_vlc():
    """
    Finaliza cualquier proceso cuyo nombre contenga 'vlc' (case-insensitive).
    """
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'vlc' in proc.info['name'].lower():
            proc.kill()


def get_current_song() -> str:
    """
    Lee vlc-qt-interface.ini para obtener la última pista reproducida.
    Devuelve solo el nombre del archivo sin extensión o un mensaje de error.
    """
    appdata = os.getenv("APPDATA")
    vlc_ini = Path(appdata) / "vlc" / "vlc-qt-interface.ini"
    if not vlc_ini.exists():
        return "[X] No se encontro la configuracion de VLC"

    config = configparser.RawConfigParser(strict=False)
    config.optionxform = str
    try:
        config.read(vlc_ini, encoding="utf-8")
    except Exception as e:
        return f"[X] Error leyendo el archivo: {e}"

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
        return "(!) No se detecto ninguna cancion reciente."

    return Path(last_file).stem


# ------------------------------------------------------------------
#  Controlador principal
# ------------------------------------------------------------------
class VLCController:
    def __init__(self):
        self.tooltip_window = None
        self.tooltip_timer = None
        self.root = None
        self.playlist_window = None

    # --- Tkinter base (oculto) ---
    def init_tkinter(self):
        if self.root is None:
            self.root = tk.Tk()
            self.root.withdraw()
            self.root.attributes('-topmost', True)

    # --- Tooltip personalizado ---
    def show_custom_tooltip(self, text: str):
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
        self.tooltip_window.geometry(f'+{screen_width - width}+{screen_height - height - 40}')
        self.tooltip_window.deiconify()
        self.tooltip_window.lift()

        # Auto-cerrar tras 5 s
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
        pid = self.find_vlc_process()
        if not pid:
            print("[X] VLC no esta ejecutandose")
            return None
        info = get_current_song()
        print(f"[INFO] Tooltip info: {info}")
        if self.root:
            self.root.after(0, lambda: self.show_custom_tooltip(info))

    # --- Lectura de playlist ---
    def find_vlc_process(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and 'vlc' in proc.info['name'].lower():
                return proc.info['pid']
        return None

    def get_vlc_playlist_path(self):
        pid = self.find_vlc_process()
        if not pid:
            print("[X] VLC no esta ejecutandose")
            return None

        try:
            process = psutil.Process(pid)
            for arg in process.cmdline():
                if arg.lower().endswith('.xspf'):
                    return arg
            return None
        except Exception as e:
            print(f"[X] Error al leer proceso: {e}")
            return None

    def read_xspf_playlist(self, playlist_path: str) -> list[dict]:
        playlist = []
        try:
            tree = ET.parse(playlist_path)
            root = tree.getroot()
            ns = {'ns': 'http://xspf.org/ns/0/'}  # sin espacio final

            for track in root.findall('.//ns:track', ns):
                location = track.find('ns:location', ns)
                title_node = track.find('ns:title', ns)

                if title_node is not None and title_node.text:
                    title = title_node.text
                else:
                    title = Path(unquote(location.text)).stem if location is not None else "Desconocido"

                playlist.append({
                    "title": title,
                    "location": unquote(location.text) if location is not None else ""
                })
        except Exception as e:
            print(f"[X] Error al leer la playlist: {e}")
        return playlist

    # --- Cerrar VLC y reproducir carpeta MP3 ---
    def close_vlc_with_keyboard(self):
        print("[STOP] Cerrando VLC y reproduciendo MP3 de la carpeta...")
        close_vlc()

        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            hwnd = win32gui.GetForegroundWindow()
            for window in shell.Windows():
                if window.hwnd == hwnd:
                    folder = window.Document.Folder
                    folder_path = folder.Self.Path
                    mp3_files = sorted([f for f in os.listdir(folder_path)
                                        if f.lower().endswith('.mp3')])
                    if not mp3_files:
                        self.show_custom_tooltip("(!) Carpeta sin MP3")
                        return

                    vlc = find_vlc()
                    if not vlc:
                        self.show_custom_tooltip("[X] VLC no encontrado")
                        return

                    full_paths = [os.path.join(folder_path, f) for f in mp3_files]
                    subprocess.Popen([vlc] + full_paths,
                                     cwd=os.path.dirname(vlc))
                    self.show_custom_tooltip(f"> {len(mp3_files)} MP3 encolados")
                    return
        except Exception as e:
            print(f"[X] Error: {e}")
            self.show_custom_tooltip("[X] No se pudo leer la carpeta")

    # --- Selector gráfico de playlist ---
    def show_playlist_selector(self):
       playlist_path = self.get_vlc_playlist_path()
       if not playlist_path:
           self.show_custom_tooltip("[Mus] No se encontró playlist activa")
           return

       playlist = self.read_xspf_playlist(playlist_path)
       if not playlist:
           self.show_custom_tooltip("[Mus] Playlist vacía")
           return

       self.close_tooltip()
       if self.playlist_window:
           try:
               self.playlist_window.destroy()
           except:
               pass
           self.playlist_window = None

       # --- Crear ventana ---
       self.playlist_window = tk.Toplevel(self.root)
       w = self.playlist_window

       w.title("VLC Playlist")
       w.overrideredirect(True)
       w.attributes('-topmost', True)
       w.configure(bg="#101010")

       # --- Marco con borde suave ---
       outer = tk.Frame(w, bg="#2A2A2A", bd=1, relief="solid")
       outer.pack(padx=3, pady=3)

       # --- Header moderno (NO draggable) ---
       header = tk.Frame(outer, bg="#262626")
       header.pack(fill=tk.X)

       tk.Label(
           header,
           text=get_current_song(),
           fg="#EDEDED",
           bg="#262626",
           font=("Segoe UI", 10, "bold"),
           pady=6
       ).pack(side=tk.LEFT, padx=10)

       # --- Área de lista ---
       list_frame = tk.Frame(outer, bg="#1A1A1A", bd=0)
       list_frame.pack(padx=5, pady=5)

       scrollbar = tk.Scrollbar(list_frame, bg="#202020")
       scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

       listbox = tk.Listbox(
           list_frame,
           font=tkfont.Font(family="Calibri", size=10, weight="bold"),
           bg="#111111",
           fg="#F3F3F3",
           selectbackground="#2E8B57",
           selectforeground="#FFFFFF",
           width=50,
           height=15,
           activestyle="none",
           yscrollcommand=scrollbar.set,
           bd=0,
           highlightthickness=0
       )
       listbox.pack(side=tk.LEFT, fill=tk.BOTH)
       scrollbar.config(command=listbox.yview)

       # --- Items con estilo zebra ---
       for i, track in enumerate(playlist, 1):
           listbox.insert(tk.END, f"{i:02d}. {track['title']}")
           if i % 2 == 0:
               listbox.itemconfig(tk.END, bg="#151515")

       def on_select(event):
           sel = listbox.curselection()
           if not sel:
               return

           idx = sel[0]
           vlc_state = get_vlc_window_state()

           close_vlc()
           vlc = find_vlc()
           if not vlc:
               self.show_custom_tooltip("[X] VLC no encontrado")
               return

           rotated_path = build_rotated_xspf(playlist_path, idx)

           if vlc_state in ("minimized", "background"):
               subprocess.Popen([vlc, rotated_path, "--qt-start-minimized"],
                                cwd=os.path.dirname(vlc))
           else:
               subprocess.Popen([vlc, rotated_path], cwd=os.path.dirname(vlc))

           self.show_custom_tooltip(f"> {playlist[idx]['title']}")
           w.destroy()

       listbox.bind("<<ListboxSelect>>", on_select)

       # --- Posicionamiento inferior derecha ---
       w.update_idletasks()
       ww, hh = w.winfo_reqwidth(), w.winfo_reqheight()
       sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
       w.geometry(f"+{sw - ww}+{sh - hh - 30}")

       # --- Cierres existentes que quieres mantener ---
       w.deiconify()
       w.lift()
       w.focus_force()
       w.bind("<Escape>", lambda e: w.destroy())
       w.bind("<FocusOut>", lambda e: w.destroy())

       print("[GUI] Playlist selector abierto.")


import win32process


def get_vlc_window_state():
    """
    Devuelve el estado de la ventana de VLC:
    'minimized', 'maximized', 'normal', 'background'
    """
    vlc_pid = None
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and 'vlc.exe' in proc.info['name'].lower():
            vlc_pid = proc.info['pid']
            break

    if not vlc_pid:
        return "normal"

    foreground_hwnd = win32gui.GetForegroundWindow()
    vlc_hwnd = None

    def enum_windows_callback(hwnd, state):
        if win32gui.IsWindowVisible(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == vlc_pid:
                state.append(hwnd)
                return False  # detener búsqueda
        return True

    state = []
    win32gui.EnumWindows(enum_windows_callback, state)
    vlc_hwnd = state[0] if state else None

    if not vlc_hwnd:
        return "background"

    if win32gui.IsIconic(vlc_hwnd):
        return "minimized"

    placement = win32gui.GetWindowPlacement(vlc_hwnd)
    show_cmd = placement[1]

    if show_cmd == win32con.SW_SHOWMAXIMIZED:
        return "maximized"
    else:
        return "normal"

# ------------------------------------------------------------------
#  Punto de entrada
# ------------------------------------------------------------------
def main():
    controller = VLCController()
    controller.init_tkinter()
    print("VLC Tooltip Ready")
    print("Atajos:")
    print("Alt+Num0  -> Mostrar cancion actual")
    print("Ctrl+Alt+X -> Salir")
    print("Alt+NumEnter -> Selector de playlist")
    print("Alt+Decimal  -> Cerrar VLC y reproducir carpeta MP3")

    keyboard.add_hotkey('alt+num 0', controller.show_song_tooltip)
    keyboard.add_hotkey('ctrl+alt+x', lambda: os._exit(0))
    keyboard.add_hotkey('alt+num enter', controller.show_playlist_selector)
    keyboard.add_hotkey('alt+decimal', controller.close_vlc_with_keyboard)

    controller.root.mainloop()


if __name__ == "__main__":
    main()