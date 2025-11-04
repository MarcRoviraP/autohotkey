import win32gui
import win32con
import win32process
import win32api
import psutil
import keyboard
import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import re
import os
import xml.etree.ElementTree as ET
import glob

class VLCController:
    def __init__(self):
        self.tooltip_window = None
        self.tooltip_timer = None
        self.root = None
        
    def init_tkinter(self):
        """Inicializa tkinter en el thread principal"""
        if self.root is None:
            self.root = tk.Tk()
            self.root.withdraw()
            self.root.attributes('-topmost', True)
        
    def is_vlc_running(self):
        """Verifica si VLC está en ejecución"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'vlc.exe':
                return True
        return False
    
    def get_vlc_windows(self):
        """Obtiene todas las ventanas de VLC"""
        vlc_windows = []
        
        def enum_callback(hwnd, results):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                if process.name() == 'vlc.exe':
                    results.append(hwnd)
            except:
                pass
        
        win32gui.EnumWindows(enum_callback, vlc_windows)
        return vlc_windows
    
    def get_main_vlc_window(self):
        """Encuentra la ventana principal de VLC"""
        windows = self.get_vlc_windows()
        
        for hwnd in windows:
            title = win32gui.GetWindowText(hwnd)
            if title and title != "VLC media player":
                return hwnd
        
        return windows[0] if windows else None
    
    def toggle_vlc_visibility(self):
        """Alterna la visibilidad de VLC (Ctrl+Alt+V)"""
        if not self.is_vlc_running():
            self.show_message_box("VLC no está en ejecución.")
            return
        
        vlc_hwnd = self.get_main_vlc_window()
        if not vlc_hwnd:
            return
        
        is_visible = win32gui.IsWindowVisible(vlc_hwnd)
        
        if is_visible:
            # Ocultar VLC
            win32gui.ShowWindow(vlc_hwnd, win32con.SW_HIDE)
            style = win32gui.GetWindowLong(vlc_hwnd, win32con.GWL_STYLE)
            win32gui.SetWindowLong(vlc_hwnd, win32con.GWL_STYLE, 
                                  style & ~win32con.WS_VISIBLE)
            
            ex_style = win32gui.GetWindowLong(vlc_hwnd, win32con.GWL_EXSTYLE)
            ex_style &= ~win32con.WS_EX_APPWINDOW
            ex_style |= win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
            win32gui.SetWindowLong(vlc_hwnd, win32con.GWL_EXSTYLE, ex_style)
        else:
            # Mostrar VLC
            style = win32gui.GetWindowLong(vlc_hwnd, win32con.GWL_STYLE)
            win32gui.SetWindowLong(vlc_hwnd, win32con.GWL_STYLE, 
                                  style | win32con.WS_VISIBLE)
            
            ex_style = win32gui.GetWindowLong(vlc_hwnd, win32con.GWL_EXSTYLE)
            ex_style &= ~(win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE)
            ex_style |= win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(vlc_hwnd, win32con.GWL_EXSTYLE, ex_style)
            
            win32gui.ShowWindow(vlc_hwnd, win32con.SW_SHOW)
            try:
                win32gui.SetForegroundWindow(vlc_hwnd)
            except:
                win32gui.ShowWindow(vlc_hwnd, win32con.SW_RESTORE)
                win32api.keybd_event(0x12, 0, 0, 0)
                win32gui.SetForegroundWindow(vlc_hwnd)
                win32api.keybd_event(0x12, 0, 2, 0)
    
    def get_current_vlc_playlist(self):
        """Obtiene la playlist actual cargada en VLC leyendo todas las ventanas"""
        if not self.is_vlc_running():
            return []
        
        playlist = []
        windows = self.get_vlc_windows()
        
        print(f"Encontradas {len(windows)} ventanas de VLC")
        
        for hwnd in windows:
            try:
                title = win32gui.GetWindowText(hwnd)
                if title and title != "VLC media player" and title != "":
                    clean = self.clean_vlc_title(title)
                    if clean and clean not in playlist:
                        playlist.append(clean)
                        print(f"  - {clean}")
            except:
                pass
        
        return playlist
    
    def find_vlc_playlist_file(self):
        """Busca el archivo de playlist de VLC dinámicamente"""
        # Rutas posibles
        vlc_paths = [
            os.path.expanduser('~\\AppData\\Roaming\\vlc'),
            os.path.expanduser('~\\AppData\\Local\\vlc'),
            'C:\\Program Files\\VideoLAN\\VLC',
            'C:\\Program Files (x86)\\VideoLAN\\VLC'
        ]
        
        # Nombres de archivo posibles
        playlist_files = ['ml.xspf', 'playlist.xspf', '*.xspf']
        
        for path in vlc_paths:
            if os.path.exists(path):
                for filename in playlist_files:
                    full_pattern = os.path.join(path, filename)
                    files = glob.glob(full_pattern)
                    if files:
                        # Devolver el más reciente
                        newest = max(files, key=os.path.getmtime)
                        print(f"Playlist encontrada: {newest}")
                        return newest
        
        print("No se encontró archivo de playlist")
        return None
    
    def get_vlc_playlist_from_file(self):
        """Lee la playlist desde el archivo de VLC"""
        playlist_file = self.find_vlc_playlist_file()
        
        if not playlist_file:
            return []
        
        try:
            tree = ET.parse(playlist_file)
            root = tree.getroot()
            
            # XSPF usa namespaces
            ns = {'xspf': 'http://xspf.org/ns/0/'}
            
            playlist = []
            for track in root.findall('.//xspf:track', ns):
                title = track.find('xspf:title', ns)
                location = track.find('xspf:location', ns)
                
                if title is not None:
                    title_text = title.text
                    location_text = location.text if location is not None else ''
                    
                    # Limpiar ubicación
                    if location_text.startswith('file:///'):
                        location_text = location_text[8:]
                    
                    playlist.append({
                        'title': title_text,
                        'location': location_text
                    })
            
            print(f"Playlist cargada: {len(playlist)} canciones")
            return playlist
            
        except Exception as e:
            print(f"Error leyendo playlist: {e}")
            import traceback
            traceback.print_exc()
        
        return []
    
    def get_vlc_title(self):
        """Obtiene el título de VLC"""
        if not self.is_vlc_running():
            return "VLC no está en ejecución"
        
        vlc_hwnd = self.get_main_vlc_window()
        if not vlc_hwnd:
            return "VLC en ejecución (sin medios activos)"
        
        # Hacer visible momentáneamente para leer el título
        was_visible = win32gui.IsWindowVisible(vlc_hwnd)
        
        if not was_visible:
            style = win32gui.GetWindowLong(vlc_hwnd, win32con.GWL_STYLE)
            win32gui.SetWindowLong(vlc_hwnd, win32con.GWL_STYLE, 
                                  style | win32con.WS_VISIBLE)
            win32gui.ShowWindow(vlc_hwnd, win32con.SW_SHOW)
            time.sleep(0.01)
        
        title = win32gui.GetWindowText(vlc_hwnd)
        clean_title = self.clean_vlc_title(title)
        
        if not was_visible:
            win32gui.ShowWindow(vlc_hwnd, win32con.SW_HIDE)
        
        return clean_title if clean_title else "VLC en ejecución (sin medios activos)"
    
    def clean_vlc_title(self, title):
        """Limpia el título de VLC"""
        clean = re.sub(r'\s*-\s*(VLC|Reproductor multimedia VLC|VLC media player).*$', 
                      '', title, flags=re.IGNORECASE)
        
        if clean == title and ' - ' in title:
            parts = title.split(' - ')
            if len(parts) > 1:
                clean = ' - '.join(parts[:-1])
        
        clean = clean.strip()
        clean = clean.replace('.mp3', '').strip()
        
        if self.is_only_vlc(clean) or len(clean) < 2:
            return ""
        
        return clean
    
    def is_only_vlc(self, text):
        """Verifica si el texto es solo "VLC" o variantes"""
        text = text.strip()
        vlc_patterns = ["VLC", "Reproductor multimedia", "Media Player", "Multimedia Player"]
        
        for pattern in vlc_patterns:
            if re.match(rf'^\s*{pattern}\s*$', text, re.IGNORECASE):
                return True
        return False
    
    def show_song_tooltip(self):
        """Muestra tooltip con información de la canción"""
        song_name = self.get_vlc_title()
        print(f"Canción: {song_name}")
        if self.root:
            self.root.after(0, lambda: self.show_custom_tooltip(song_name))
    
    def show_custom_tooltip(self, text):
        """Crea y muestra un tooltip personalizado"""
        print(f"=== MOSTRANDO TOOLTIP ===")
        
        # Cerrar tooltip anterior
        self.close_tooltip()
        
        # Si texto vacío, no mostrar
        if not text or text == "VLC en ejecución (sin medios activos)":
            print("Sin contenido para mostrar")
            return
        
        # Configuración
        bg_color = "#101010"
        border_color = "#404040"
        font_color = "#F3F3F3"
        font_name = "Calibri"
        font_size = 10
        padding = 8
        
        try:
            if not self.root:
                self.init_tkinter()
            
            # Crear tooltip con borde
            self.tooltip_window = tk.Toplevel(self.root)
            self.tooltip_window.overrideredirect(True)
            self.tooltip_window.attributes('-topmost', True)
            self.tooltip_window.config(bg=border_color)
            
            # Configurar fuente
            try:
                custom_font = tkfont.Font(family=font_name, size=font_size, weight='bold')
            except:
                custom_font = tkfont.Font(family="Arial", size=font_size, weight='bold')
            
            # Label con borde
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
            
            # Actualizar geometría
            self.tooltip_window.update_idletasks()
            
            # Calcular posición
            screen_width = self.tooltip_window.winfo_screenwidth()
            screen_height = self.tooltip_window.winfo_screenheight()
            width = self.tooltip_window.winfo_reqwidth()
            height = self.tooltip_window.winfo_reqheight()
            
            taskbar_height = 60
            pos_x = screen_width - width - 20
            pos_y = screen_height - height - taskbar_height
            
            print(f"Posición: {pos_x}, {pos_y} | Tamaño: {width}x{height}")
            
            self.tooltip_window.geometry(f'+{pos_x}+{pos_y}')
            self.tooltip_window.deiconify()
            self.tooltip_window.lift()
            self.tooltip_window.update()
            
            print("✓ Tooltip visible")
            
            # Auto-cerrar en 5 segundos
            if self.tooltip_timer:
                self.tooltip_timer.cancel()
            self.tooltip_timer = threading.Timer(5.0, self.close_tooltip)
            self.tooltip_timer.start()
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def close_tooltip(self):
        """Cierra el tooltip"""
        if self.tooltip_timer:
            self.tooltip_timer.cancel()
            self.tooltip_timer = None
        
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None
    
    def show_message_box(self, message):
        """Muestra un mensaje simple"""
        root = tk.Tk()
        root.withdraw()
        from tkinter import messagebox
        messagebox.showinfo("VLC Controller", message)
        root.destroy()

def main():
    controller = VLCController()
    controller.init_tkinter()
    
    print("VLC Controller - Python")
    print("=======================")
    print("Ctrl+Alt+V: Mostrar/Ocultar VLC")
    print("Alt+Num0: Mostrar canción actual")
    print("Ctrl+Alt+P: Mostrar playlist")
    print("Ctrl+Alt+X: Salir")
    print("\nEsperando comandos...")
    
    def show_playlist():
        print("Obteniendo playlist actual de VLC...")
        
        # Primero intentar leer de las ventanas actuales
        playlist = controller.get_current_vlc_playlist()
        
        # Si no hay nada, intentar el archivo
        if not playlist:
            print("No hay playlist en ventanas, buscando archivo...")
            file_playlist = controller.get_vlc_playlist_from_file()
            if file_playlist:
                playlist = [track['title'] for track in file_playlist]
        
        if playlist:
            message = f"Playlist Actual ({len(playlist)} canciones):\n\n"
            for i, title in enumerate(playlist[:20], 1):
                message += f"{i}. {title}\n"
            if len(playlist) > 20:
                message += f"\n...y {len(playlist) - 20} más"
        else:
            message = "No se pudo obtener la playlist actual"
        
        print(f"Mostrando: {message[:100]}...")
        
        if controller.root:
            controller.root.after(0, lambda: controller.show_custom_tooltip(message))
    
    # Atajos
    keyboard.add_hotkey('ctrl+alt+v', controller.toggle_vlc_visibility)
    keyboard.add_hotkey('alt+num 0', controller.show_song_tooltip)
    keyboard.add_hotkey('ctrl+alt+p', show_playlist)
    keyboard.add_hotkey('ctrl+alt+x', lambda: os._exit(0))
    
    # Loop de tkinter
    def check_keyboard():
        controller.root.after(100, check_keyboard)
    
    check_keyboard()
    controller.root.mainloop()

if __name__ == "__main__":
    main()