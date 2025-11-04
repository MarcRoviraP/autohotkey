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
                
                print(f"{i:2d}. {os.path.basename(file_path)}")
                if title is not None and title.text:
                    print(f"    Título: {title.text}")
                if duration is not None and duration.text:
                    mins = int(duration.text) // 60000
                    secs = (int(duration.text) % 60000) // 1000
                    print(f"    Duración: {mins}:{secs:02d}")
                print(f"    Ruta: {file_path}")
                print()
                
    except Exception as e:
        print(f"❌ Error al leer el archivo XSPF: {e}")

# Usar la ruta que encontramos en tu ejecución
playlist_path = r"C:\Users\Marc\Desktop\Playlist.xspf"
read_xspf_playlist(playlist_path)