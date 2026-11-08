import argparse
import sys
from pathlib import Path

# Añadir directorio actual al path
sys.path.append(str(Path(__file__).parent))

from empresa_matcher import procesar_empresa_completa, scrapear_ofertas_tecnoempleo


def main():
    parser = argparse.ArgumentParser(description="Buscador y evaluador de empresas para 2º DAM con Scrapling (Modo Visible) y Jeb (Ollama)")
    parser.add_argument("--url", type=str, help="URL de la web corporativa o de la oferta para evaluar")
    parser.add_argument("--keyword", type=str, default="junior", help="Palabra clave para buscar ofertas (ej: flutter, java, junior, node)")
    parser.add_argument("--ciudad", type=str, default="jaen", help="Provincia o ciudad (jaen, granada, madrid, etc.)")
    parser.add_argument("--no-save", action="store_true", help="No guardar automáticamente en Obsidian aunque encaje")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en segundo plano sin abrir ventana del navegador")

    args = parser.parse_args()
    modo_visible = not args.headless

    if args.url:
        print(f"\n🔍 [MODO VISIBLE: {'Activado' if modo_visible else 'Desactivado'}] Analizando URL con Scrapling y evaluando con Jeb (Ollama)...")
        resultado = procesar_empresa_completa(
            args.url,
            ciudad_manual=args.ciudad.capitalize(),
            auto_guardar=not args.no_save,
            modo_visible=modo_visible,
        )
        print("\n" + resultado)
    else:
        print(f"\n🔎 [MODO VISIBLE: {'Activado' if modo_visible else 'Desactivado'}] Buscando ofertas en Tecnoempleo para '{args.keyword}' en '{args.ciudad}'...")
        ofertas = scrapear_ofertas_tecnoempleo(args.keyword, provincia=args.ciudad, modo_visible=modo_visible)
        if not ofertas:
            print("No se encontraron ofertas.")
            return

        print(f"\n✅ Se encontraron {len(ofertas)} ofertas. Evaluando las 3 primeras:\n")
        for i, o in enumerate(ofertas[:3], 1):
            print(f"[{i}/{min(3, len(ofertas))}] Abriendo navegador y evaluando: {o['titulo']} ({o['empresa']})...")
            res = procesar_empresa_completa(
                o['link'],
                ciudad_manual=args.ciudad.capitalize(),
                auto_guardar=not args.no_save,
                modo_visible=modo_visible,
            )
            print(res)
            print("-" * 50)


if __name__ == "__main__":
    main()
