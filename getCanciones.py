import psutil
import os
import xml.etree.ElementTree as ET
import urllib.parse

def read_xspf_playlist(playlist_path):
    """Leer archivo de playlist XSPF directamente"""
    print(f"📖 Leyendo playlist: {playlist_path}")
    
    try:
        with open(playlist_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Parsear XML
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
                file_path = location.text or ""
                # Limpiar formato file:///
                if file_path.startswith('file:///'):
                    file_path = file_path[8:]
                elif file_path.startswith('file://'):
                    file_path = file_path[7:]
                
                # Decodificar caracteres como %20
                file_path = urllib.parse.unquote(file_path)
                
                print(f"{i:02d}. 🎶 {os.path.basename(file_path)}")
                if title is not None and title.text:
                    print(f"    🏷️  Título: {title.text}")
                if duration is not None and duration.text:
                    try:
                        print(f"    ⏱️  Duración: {int(duration.text) // 1000} segundos")
                    except:
                        pass
                print()
                
    except Exception as e:
        print(f"❌ Error al leer el archivo XSPF: {e}")

def find_vlc_process():
    """Encontrar proceso de VLC"""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and 'vlc' in proc.info['name'].lower():
            return proc.info['pid']
    return None

def get_vlc_info_dynamic():
    pid = find_vlc_process()
    if pid:
        print(f"✅ VLC encontrado (PID: {pid})")
        
        try:
            process = psutil.Process(pid)
            args = process.cmdline()
            
            print(f"📁 Directorio: {process.cwd()}")
            print(f"🎯 Ejecutable: {process.exe()}")
            print(f"🔧 Argumentos: {process.cmdline()}")
            print(f"🔧 Argumentos: {args}")
            
            # Buscar archivo XSPF
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

# Ejecutar escaneo
get_vlc_info_dynamic()
