import xml.etree.ElementTree as ET
import os

def read_xspf_playlist(playlist_path):
    """Leer archivo de playlist XSPF directamente"""
    print(f"📖 Leyendo playlist: {playlist_path}")
    
    try:
        with open(playlist_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Parsear XML
        root = ET.fromstring(content)
        
        # Namespace para XSPF
        ns = {'ns': 'http://xspf.org/ns/0/'}
        
        # Encontrar todos los tracks
        tracks = root.findall('.//ns:track', ns)
        print(f"🎵 Encontradas {len(tracks)} pistas en la playlist:")
        print("-" * 80)
        
        for i, track in enumerate(tracks, 1):
            location = track.find('ns:location', ns)
            title = track.find('ns:title', ns)
            duration = track.find('ns:duration', ns)
            
            if location is not None:
                file_path = location.text
                # Limpiar formato file:///
                if file_path.startswith('file:///'):
                    file_path = file_path[8:]
                
                print(f" {os.path.basename(file_path)}")
                if title is not None and title.text:
                    print(f"    Título: {title.text}")
                
                
    except Exception as e:
        print(f"❌ Error al leer el archivo XSPF: {e}")

# Usar la ruta que encontramos en tu ejecución
playlist_path = r"C:\Users\Marc\Desktop\Playlist.xspf"
read_xspf_playlist(playlist_path)

import psutil
import os
import glob

def find_vlc_process():
    """Encontrar proceso de VLC"""
    for proc in psutil.process_iter(['pid', 'name']):
        if 'vlc' in proc.info['name'].lower():
            return proc.info['pid']
    return None

def scan_vlc_temp_files():
    """Buscar archivos temporales de VLC"""
    temp_locations = [
        os.environ.get('TEMP', ''),
        os.environ.get('TMP', ''),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Roaming', 'vlc')
    ]
    
    vlc_files = []
    for location in temp_locations:
        if os.path.exists(location):
            # Buscar archivos que puedan contener info de playlist
            patterns = [
                os.path.join(location, '*vlc*'),
                os.path.join(location, '*playlist*'),
                os.path.join(location, 'vlc-*')
            ]
            for pattern in patterns:
                vlc_files.extend(glob.glob(pattern))
    
    return vlc_files

def get_vlc_info_dynamic():
    pid = find_vlc_process()
    if pid:
        print(f"✅ VLC encontrado (PID: {pid})")
        
        # Intentar leer información del proceso
        try:
            process = psutil.Process(pid)
            print(f"🔧 Argumentos: {process.cmdline()}")
            linea = process.cmdline()
            return linea
            # Archivos abiertos por VLC
            open_files = []
            try:
                open_files = process.open_files()
                print("\n📂 Archivos abiertos:")
                for file in open_files[:10]:  # Mostrar solo los primeros 10
                    if any(ext in file.path.lower() for ext in ['.mp3', '.mp4', '.avi', '.mkv', '.m4a']):
                        print(f"   🎵 {os.path.basename(file.path)}")
            except psutil.AccessDenied:
                print("   ⚠️  No se pueden leer archivos abiertos (permisos)")
                
        except Exception as e:
            print(f"❌ Error al leer proceso: {e}")
    else:
        print("❌ VLC no está ejecutándose")

# Ejecutar escaneo
get_vlc_info_dynamic()