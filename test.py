import re
import urllib.parse

def decode_uri(uri: str) -> str:
    """Convierte file:///C:/...%20... a ruta legible"""
    if uri.startswith("file:///"):
        uri = uri[8:]
    elif uri.startswith("file://"):
        uri = uri[7:]
    return urllib.parse.unquote(uri.strip('"').strip())

# Texto simulado (como en tu .ini)
recent_raw = '"file:///C:/Users/Marc/Downloads/Duki%20zevra%2025/Duki_%20Bzrp%20Music%20Sessions,%20Vol.%2050.mp3", file:///C:/Users/Marc/Downloads/Constelación.mp3, file:///C:/Users/Marc/Downloads/Barro.mp3'

# Nueva regex: captura rutas con o sin comillas, incluso si contienen comas
uris = re.findall(r'"(file://[^"]+)"|(?<!")\b(file://[^,]+)', recent_raw)

# Flatten y decodificar
uris = [decode_uri(u[0] or u[1]) for u in uris if (u[0] or u[1])]

print("🎧 URIs encontradas:")
for i, uri in enumerate(uris, 1):
    print(f"{i:02d}. {uri}")
