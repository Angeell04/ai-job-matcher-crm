import sys
from pathlib import Path

# Configurar salida UTF-8 para consola Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).parent))

from empresa_matcher import scrapear_ofertas_tecnoempleo, procesar_empresa_completa

def main():
    print("=" * 60)
    print("   ESCANEO Y EVALUACION DE OFERTAS EN JAEN CON SCRAPLING + JEB")
    print("=" * 60)

    # 1. Obtener todas las ofertas disponibles en Jaén
    print("\n1. Scrapeando ofertas activas en la provincia de Jaen...")
    ofertas = scrapear_ofertas_tecnoempleo("", provincia="jaen", modo_visible=False)
    print(f"Se han detectado {len(ofertas)} ofertas activas en Jaen.\n")

    # Filtrar aquellas relacionadas con desarrollo de software / TI
    keywords_interes = ["java", "flutter", "node", "developer", "programador", "backend", "fullstack", "software", "desarrollador", "ai", "sql"]
    ofertas_tecnologicas = []
    for o in ofertas:
        titulo_lower = o["titulo"].lower()
        if any(k in titulo_lower for k in keywords_interes):
            ofertas_tecnologicas.append(o)

    print(f"Total: {len(ofertas_tecnologicas)} ofertas coinciden con perfiles de desarrollo de software.\n")

    aprobadas = []
    descartadas = []

    # Evaluar las ofertas tecnológicas
    for i, o in enumerate(ofertas_tecnologicas, 1):
        print(f"\n[{i}/{len(ofertas_tecnologicas)}] Analizando: {o['titulo']} ({o['empresa']})...")
        resultado = procesar_empresa_completa(
            o["link"],
            ciudad_manual="Jaen",
            auto_guardar=True,
            modo_visible=True
        )
        print(resultado)
        if "¡Ficha creada en Obsidian!" in resultado or "Ficha creada en Obsidian" in resultado:
            aprobadas.append(f"{o['empresa']} - {o['titulo']}")
        else:
            descartadas.append(f"{o['empresa']} - {o['titulo']}")

    print("\n" + "=" * 60)
    print("   RESUMEN FINAL DEL ESCANEO EN JAEN")
    print("=" * 60)
    print(f"APROBADAS Y GUARDADAS EN OBSIDIAN ({len(aprobadas)}):")
    for a in aprobadas:
        print(f"  * {a}")

    print(f"\nDESCARTADAS POR CRITERIO DE PERFIL ({len(descartadas)}):")
    for d in descartadas:
        print(f"  * {d}")

if __name__ == "__main__":
    main()
