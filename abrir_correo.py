import os
import sys
import re
import urllib.parse
import webbrowser

from pathlib import Path
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "crm_data"
VAULT_ROOT = Path(os.getenv("OBSIDIAN_VAULT", DEFAULT_DATA_DIR))
EMPRESAS_DIR = VAULT_ROOT / "02_Personal" / "empresas"

def encontrar_archivo(nombre_empresa):
    nombre_limpio = nombre_empresa.lower().replace(" ", "").replace("_", "")
    for root, dirs, files in os.walk(EMPRESAS_DIR):
        for file in files:
            if file.endswith(".md") and not file.startswith("README"):
                file_limpio = os.path.splitext(file)[0].lower().replace(" ", "").replace("_", "")
                if nombre_limpio in file_limpio or file_limpio in nombre_limpio:
                    return os.path.join(root, file)
    return None

def extraer_datos_correo(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Buscar correo destinatario
    match_contacto = re.search(r"\*\*Contacto / RRHH:\*\*\s*([^\n]+)", contenido)
    destinatario = ""
    if match_contacto:
        emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", match_contacto.group(1))
        if emails:
            destinatario = emails[0]

    # Buscar asunto
    match_asunto = re.search(r"\*\*Asunto:\*\*\s*([^\n]+)", contenido)
    asunto = match_asunto.group(1).strip() if match_asunto else "Solicitud Prácticas FCT (2º DAM) - Ángel Miranda Molina"

    # Buscar cuerpo de correo en bloque text o entre comillas triples
    match_cuerpo = re.search(r"```text\s*\n(.*?)\n```", contenido, re.DOTALL)
    if match_cuerpo:
        cuerpo = match_cuerpo.group(1).strip()
    else:
        cuerpo = "Hola, me pongo en contacto para solicitar prácticas de FCT."

    return destinatario, asunto, cuerpo

def generar_gmail_url(destinatario, asunto, cuerpo):
    params = {
        'view': 'cm',
        'fs': '1',
        'to': destinatario,
        'su': asunto,
        'body': cuerpo
    }
    return "https://mail.google.com/mail/?authuser=0&" + urllib.parse.urlencode(params)

def abrir_en_navegador(nombre_empresa):
    archivo = encontrar_archivo(nombre_empresa)
    if not archivo:
        print(f"Error: No se encontró la ficha de '{nombre_empresa}' en {EMPRESAS_DIR}")
        return False
    dest, asunto, cuerpo = extraer_datos_correo(archivo)
    url = generar_gmail_url(dest, asunto, cuerpo)
    print(f"Abriendo Gmail para {os.path.basename(archivo)}...")
    webbrowser.open(url)
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        empresa = " ".join(sys.argv[1:])
        abrir_en_navegador(empresa)
    else:
        print("Uso: python abrir_correo.py <nombre_empresa>")
