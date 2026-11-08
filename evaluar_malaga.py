import sys
import subprocess
import time
from pathlib import Path

# Configurar salida UTF-8 para consola Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).parent))

from empresa_matcher import scrapear_ofertas_tecnoempleo, procesar_empresa_completa

import os
# Script opcional de notificación local (configurable por variable de entorno)
SUBIR_TAREA_PATH = Path(os.getenv("NOTIFICACION_SCRIPT", ""))

def main():
    inicio = time.time()
    print("=" * 60)
    print("   ESCANEO Y EVALUACION DE OFERTAS EN MALAGA (SCRAPLING + JEB)")
    print("=" * 60)

    # 1. Obtener todas las ofertas disponibles en Málaga (ID: 254)
    print("\n1. Scrapeando ofertas activas en la provincia de Malaga (ID: 254)...")
    ofertas = scrapear_ofertas_tecnoempleo("", provincia="malaga", modo_visible=False)
    print(f"Se han detectado {len(ofertas)} ofertas activas en Malaga.\n")

    # Filtrar aquellas relacionadas con desarrollo de software / TI
    keywords_interes = [
        "java", "flutter", "node", "developer", "programador", "backend",
        "fullstack", "software", "desarrollador", "ai", "sql", "react",
        "cloud", "qa", "ingeniero", "ios", "moodle", "data"
    ]
    
    ofertas_tecnologicas = []
    vistos = set()
    for o in ofertas:
        if o["link"] in vistos:
            continue
        vistos.add(o["link"])
        titulo_lower = o["titulo"].lower()
        if any(k in titulo_lower for k in keywords_interes):
            ofertas_tecnologicas.append(o)

    # Añadir Freepik si no está en las ofertas
    freepik_url = "https://www.freepikcompany.com/es/trabaja-con-nosotros"
    ofertas_tecnologicas.append({
        "titulo": "Desarrollo Software & Producto Digital",
        "empresa": "Freepik Company",
        "link": freepik_url,
        "descripcion": "Compañía tecnológica líder en diseño, stock multimedia e IA con sede central en Málaga.",
        "origen": "Web Corporativa"
    })

    print(f"Total: {len(ofertas_tecnologicas)} oportunidades seleccionadas para evaluar.\n")

    aprobadas = []
    descartadas = []

    # Evaluar las ofertas tecnológicas con Scrapling y Jeb (Ollama)
    for i, o in enumerate(ofertas_tecnologicas, 1):
        print(f"\n[{i}/{len(ofertas_tecnologicas)}] Analizando: {o['titulo']} ({o['empresa']})...")
        try:
            resultado = procesar_empresa_completa(
                o["link"],
                ciudad_manual="Malaga",
                auto_guardar=True,
                modo_visible=True
            )
            print(resultado)
            if "¡Ficha creada en Obsidian!" in resultado or "Ficha creada en Obsidian" in resultado:
                aprobadas.append(f"{o['empresa']} - {o['titulo']}")
            else:
                descartadas.append(f"{o['empresa']} - {o['titulo']}")
        except Exception as e:
            print(f"Error al procesar {o['empresa']}: {e}")
            descartadas.append(f"{o['empresa']} (Error)")

    duracion_seg = int(time.time() - inicio)
    minutos = duracion_seg // 60
    segundos = duracion_seg % 60
    duracion_str = f"{minutos}m {segundos}s"

    print("\n" + "=" * 60)
    print("   RESUMEN FINAL DEL ESCANEO EN MALAGA")
    print("=" * 60)
    print(f"APROBADAS Y GUARDADAS EN OBSIDIAN ({len(aprobadas)}):")
    for a in aprobadas:
        print(f"  * {a}")

    print(f"\nDESCARTADAS POR CRITERIO DE PERFIL ({len(descartadas)}):")
    for d in descartadas:
        print(f"  * {d}")

    # Ejecutar indexar.py para indexar en LanceDB
    print("\n2. Ejecutando indexar.py para indexar las nuevas fichas en LanceDB...")
    try:
        res_idx = subprocess.run([sys.executable, str(Path(__file__).parent / "indexar.py")], capture_output=True, text=True, encoding="utf-8")
        print("Salida indexar.py:")
        print(res_idx.stdout[-400:] if res_idx.stdout else "Indexado completado.")
    except Exception as e:
        print(f"Error al indexar: {e}")

    # Notificar a la app personal (Pixel 9a)
    print("\n3. Enviando notificación a la App Personal (Pixel 9a)...")
    if SUBIR_TAREA_PATH.exists():
        resumen_notif = f"Málaga escaneada: {len(aprobadas)} empresas aprobadas y guardadas en Obsidian ({', '.join([a.split(' - ')[0] for a in aprobadas[:5]])}...). Fichas e indexación LanceDB listas."
        try:
            cmd = [
                sys.executable,
                str(SUBIR_TAREA_PATH),
                "--titulo", "Escaneo Empresas Málaga (2º DAM)",
                "--resumen", resumen_notif[:450],
                "--duracion", duracion_str,
                "--estado", "terminado",
                "--errores", "Ninguno"
            ]
            sub_res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            print("Resultado notificación:", sub_res.stdout)
        except Exception as e:
            print(f"Error al notificar app: {e}")

if __name__ == "__main__":
    main()
