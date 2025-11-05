import keyboard
import tkinter as tk
from tkinter import font as tkfont
import threading
import re
import os
import xml.etree.ElementTree as ET
import configparser
import urllib.parse
from pathlib import Path
import psutil

# ============================================================
# 🔹 Utilidades VLC INI
# ============================================================
def decode_uri(uri: str) -> str:
    """Convierte file:///C:/...%20... a una ruta legible"""
    if uri.startswith("file:///"):
        uri = uri[8:]
    elif uri.startswith("file://"):
        uri = uri[7:]
    return urllib.parse.unquote(uri.strip('"').strip())

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

    # [General] → Último archivo abierto
    if config.has_option("General", "filedialog-path"):
        raw_path = config.get("General", "filedialog-path")
        match = re.search(r'file://[^)]+', raw_path)
        if match:
            last_file = decode_uri(match.group(0))

    # Si no está, buscar en [RecentsMRL]
    if not last_file and config.has_option("RecentsMRL", "list"):
        recent_raw = config.get("RecentsMRL", "list")
        uris = re.findall(r'"(file://[^"]+)"|(?<!")\b(file://[^,]+)', recent_raw)
        uris = [decode_uri(u[0] or u[1]) for u in uris if (u[0] or u[1])]
        if uris:
            last_file = uris[0]

    if not last_file:
        return "⚠️ No se detectó ninguna canción reciente."

    filename = Path(last_file).name
    return f"{filename.replace('.mp3', '')}"

# ============================================================
# 🎛️ Controlador principal VLC
# ============================================================
class VLCController:
    def __init__(self):
        self.tooltip_window = None
        self.tooltip_timer = None
        self.root = None

    # --- Interfaz Tk ---
    def init_tkinter(self):
        if self.root is None:
            self.root = tk.Tk()
            self.root.withdraw()
            self.root.attributes('-topmost', True)

    # --- Tooltip ---
    def show_custom_tooltip(self, text):
        """Crea y muestra un tooltip personalizado"""
        self.close_tooltip()

        if not text or text.strip() == "":
            return

        bg_color = "#101010"
        border_color = "#404040"
        font_color = "#F3F3F3"
        font_name = "Calibri"
        font_size = 10
        padding = 8

        if not self.root:
            self.init_tkinter()

        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.attributes('-topmost', True)
        self.tooltip_window.config(bg=border_color)

        custom_font = tkfont.Font(family=font_name, size=font_size, weight='bold')
        label = tk.Label(
            self.tooltip_window,
            text=text,
            font=custom_font,
            fg=font_color,
            bg=bg_color,
            justify=tk.LEFT,
            padx=padding,
            pady=padding
        )
        label.pack(padx=1, pady=1)

        self.tooltip_window.update_idletasks()
        screen_width = self.tooltip_window.winfo_screenwidth()
        screen_height = self.tooltip_window.winfo_screenheight()
        width = self.tooltip_window.winfo_reqwidth()
        height = self.tooltip_window.winfo_reqheight()

        pos_x = screen_width - width - 20
        pos_y = screen_height - height - 60
        self.tooltip_window.geometry(f'+{pos_x}+{pos_y}')
        self.tooltip_window.deiconify()
        self.tooltip_window.lift()

        # Auto-cerrar en 5 segundos
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

    # --- Función para shortcut ---
    def show_song_tooltip(self):
        """Muestra tooltip con la canción actual desde el archivo INI"""
        info = get_current_song()
        print(f"ℹ️ Tooltip info: {info}")
        if self.root:
            self.root.after(0, lambda: self.show_custom_tooltip(info))
    """Encuentra el proceso de VLC en ejecución"""
    
    # ============================================================
    # 🎶 Playlist actual (XSPF
    # ============================================================)

    def read_xspf_playlist(self, playlist_path):
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
    def find_vlc_process(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and 'vlc' in proc.info['name'].lower():
                return proc.info['pid']
        return None
    def get_vlc_playlist(self):
        """Detecta VLC y devuelve la playlist activa si existe."""
        playlist = []
        pid = self.find_vlc_process()

        if not pid:
            print("❌ VLC no está ejecutándose")
            return playlist

        print(f"✅ VLC encontrado (PID: {pid})")

        try:
            process = psutil.Process(pid)
            args = process.cmdline()
            print(f"🔧 Argumentos: {args}")

            for arg in args:
                if arg.lower().endswith('.xspf'):
                    playlist_path = arg
                    print(f"🎧 Playlist detectada: {playlist_path}")
                    try:
                        with open(playlist_path, 'r', encoding='utf-8') as file:
                            content = file.read()

                        root = ET.fromstring(content)
                        ns = {'ns': 'http://xspf.org/ns/0/'}
                        tracks = root.findall('.//ns:track', ns)

                        for track in tracks:
                            title = track.find('ns:title', ns)
                            location = track.find('ns:location', ns)
                            title_text = title.text if title is not None else "Desconocido"
                            location_text = decode_uri(location.text) if location is not None else ""
                            playlist.append({
                                "title": title_text,
                                "location": location_text
                            })

                        print(f"🎵 Playlist cargada con {len(playlist)} canciones.")
                        return playlist

                    except Exception as e:
                        print(f"❌ Error al leer la playlist: {e}")
                        return []

            print("⚠️ No se encontró ningún archivo XSPF en los argumentos de VLC.")
            return playlist

        except Exception as e:
            print(f"❌ Error al leer proceso: {e}")
            return []

    def show_playlist_selector(self):
        """Muestra una ventana con la playlist y permite seleccionar una canción."""
        playlist = self.get_vlc_playlist()
        if not playlist:
            print("No se encontró ninguna playlist para mostrar.")
            self.show_custom_tooltip("🎵 No se encontró ninguna playlist activa")
            return

        # Cerrar ventanas previas
        self.close_tooltip()
        if hasattr(self, "playlist_window") and self.playlist_window:
            try:
                self.playlist_window.destroy()
            except:
                pass
            self.playlist_window = None

        # Crear ventana de lista
        self.playlist_window = tk.Toplevel(self.root)
        self.playlist_window.title("VLC Playlist")
        self.playlist_window.overrideredirect(True)
        self.playlist_window.attributes('-topmost', True)
        self.playlist_window.configure(bg="#101010")

        # Configurar fuente
        try:
            custom_font = tkfont.Font(family="Calibri", size=10, weight="bold")
        except:
            custom_font = tkfont.Font(family="Arial", size=10, weight="bold")

        # Marco contenedor con borde
        frame = tk.Frame(self.playlist_window, bg="#404040", bd=1)
        frame.pack(padx=2, pady=2)

        # Scrollbar
        scrollbar = tk.Scrollbar(frame, bg="#202020")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Listbox
        listbox = tk.Listbox(
            frame,
            font=custom_font,
            bg="#101010",
            fg="#F3F3F3",
            selectbackground="#2E8B57",
            selectforeground="#FFFFFF",
            width=50,
            height=15,
            activestyle="none",
            yscrollcommand=scrollbar.set,
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH)
        scrollbar.config(command=listbox.yview)

        # Rellenar lista
        for i, track in enumerate(playlist, 1):
            title = track["title"]
            listbox.insert(tk.END, f"{i:02d}. {title}")

        # Función al hacer clic
        def on_select(event):
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                song = playlist[index]["title"]
                print(f"🎶 Seleccionaste: {song}")
                # Aquí luego haremos que se reproduzca la canción
                self.show_custom_tooltip(f"▶️ {song}")

        # Asociar clic y doble clic
        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Double-Button-1>", on_select)

        # Posicionar en esquina inferior derecha
        self.playlist_window.update_idletasks()
        screen_width = self.playlist_window.winfo_screenwidth()
        screen_height = self.playlist_window.winfo_screenheight()
        width = self.playlist_window.winfo_reqwidth()
        height = self.playlist_window.winfo_reqheight()

        pos_x = screen_width - width - 40
        pos_y = screen_height - height - 80

        self.playlist_window.geometry(f"+{pos_x}+{pos_y}")
        self.playlist_window.deiconify()
        self.playlist_window.lift()
        self.playlist_window.focus_force()

        # Cerrar al pulsar Escape
        self.playlist_window.bind("<Escape>", lambda e: self.playlist_window.destroy())

        print("🪄 Playlist selector abierto.")


# ============================================================
# 🚀 Ejecución principal
# ============================================================
def main():
    controller = VLCController()
    controller.init_tkinter()

    print("🎵 VLC Tooltip Ready")
    print("Atajos:")
    print("Alt+Num0 → Mostrar canción actual")
    print("Ctrl+Alt+X → Salir")

    keyboard.add_hotkey('alt+num 0', controller.show_song_tooltip)
    keyboard.add_hotkey('ctrl+alt+x', lambda: os._exit(0))
    keyboard.add_hotkey('alt+num enter', controller.show_playlist_selector)


    controller.root.mainloop()

if __name__ == "__main__":
    main()
