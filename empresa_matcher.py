import os
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from contextlib import redirect_stdout

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from scrapling.fetchers import StealthyFetcher, Fetcher
import ollama

# Ruta base del Vault o carpeta de datos local (configurable por variable de entorno)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "crm_data"
VAULT_ROOT = Path(os.getenv("OBSIDIAN_VAULT", DEFAULT_DATA_DIR))
EMPRESAS_DIR = VAULT_ROOT / "02_Personal" / "Empresas"
CRM_FILE = EMPRESAS_DIR / "README_CRM_Empresas.md"

OLLAMA_MODEL = "qwen2.5-coder:7b"

PERFIL_CANDIDATO = """
Candidato: Ángel Miranda Molina
Estudios: 2º de DAM (Desarrollo de Aplicaciones Multiplataforma)
Especialidad y tecnologías fuertes:
- Desarrollo Móvil y Frontend: Flutter (Dart) con layouts adaptativos y arquitectura limpia (su proyecto final es un gestor de tareas multiplataforma).
- Backend: Java (POO, MVC, DAO, Spring Boot en aprendizaje/desarrollo), Node.js con Express y TypeScript (APIs RESTful, enrutamiento, middlewares, CRUD).
- Bases de Datos: SQL avanzado (MySQL), consultas multitabla, triggers, persistencia.
- Otros: Git, Linux.
Objetivo: Prácticas de FCT (Empresa) y/o puesto Junior como desarrollador móvil (Flutter) o backend (Java / Node.js).
Ubicación preferente: Jaén, Granada, o Remoto / Híbrido.
"""


def _slug(texto: str) -> str:
    texto = re.sub(r"[^\w\-]+", "_", texto, flags=re.UNICODE).strip("_")
    return texto[:40] or "Empresa"


def extraer_datos_web(url: str, modo_visible: bool = False) -> dict:
    """Usa Scrapling StealthyFetcher para extraer el texto y datos limpios."""
    resp = None
    with redirect_stdout(sys.stderr):
        try:
            if modo_visible:
                resp = StealthyFetcher.fetch(
                    url,
                    headless=False,
                    timeout=25000,
                    wait=2500,
                    solve_cloudflare=True,
                )
            else:
                resp = StealthyFetcher.fetch(
                    url,
                    headless=True,
                    timeout=20000,
                    solve_cloudflare=True,
                )
        except Exception:
            pass

        if resp is None or getattr(resp, "status", None) != 200:
            try:
                resp = Fetcher.get(url, timeout=20, verify=False)
            except Exception as e:
                return {"error": f"Error al acceder a la URL: {e}"}

    if resp.status != 200:
        return {"error": f"Error al acceder a la URL: código HTTP {resp.status}"}

    titulo = (resp.css("title::text").get() or "").strip()

    # Extraer párrafos relevantes y textos de encabezados
    textos = resp.css("h1::text, h2::text, h3::text, p::text, li::text").getall()
    contenido_limpio = " ".join([t.strip() for t in textos if len(t.strip()) > 15])

    # Limitar tamaño para contexto de Ollama
    texto_contexto = contenido_limpio[:7000]

    return {
        "url": url,
        "titulo_web": titulo,
        "texto": texto_contexto,
    }


def evaluar_con_jeb_ollama(datos_empresa: dict) -> dict:
    """Evalúa la empresa o puesto frente al perfil de Ángel usando Ollama de forma 100% gratuita."""
    prompt = f"""Actúa como 'jeb', un evaluador y recomendador de oportunidades de empleo y empresas para estudiantes de informática.

PERFIL DEL CANDIDATO:
{PERFIL_CANDIDATO}

DATOS EXTRAÍDOS DE LA EMPRESA U OFERTA:
Título/Web: {datos_empresa.get('titulo_web', '')}
URL: {datos_empresa.get('url', '')}
Contenido: {datos_empresa.get('texto', '')}

INSTRUCCIONES:
Evalúa si esta empresa o puesto encaja con Ángel (2º DAM, Flutter/Java/Node/SQL, prácticas o junior).
Devuelve EXCLUSIVAMENTE un objeto JSON válido con los siguientes campos:
{{
  "empresa": "Nombre corto y limpio de la empresa",
  "puesto_o_sector": "Sector principal o título del puesto",
  "ciudad_detectada": "Jaen, Granada, Remoto u Otra",
  "score": 0 a 100 (puntuación de encaje con su perfil),
  "encaja": true o false (true si score >= 60),
  "modalidad": "Presencial / Híbrido / Remoto",
  "contacto_rrhh": "correo de contacto o info@... o [Pendiente]",
  "linkedin": "enlace de linkedin si aparece o [Pendiente]",
  "stack_tecnico": ["tecnología 1", "tecnología 2"],
  "puntos_clave_dam": [
    "punto de match 1 (ej: uso de Flutter)",
    "punto de match 2 (ej: backend Java o APIs Node)"
  ],
  "motivos_decision": [
    "por qué encaja o por qué se descarta"
  ],
  "carta_motivacion_personalizada": "Un correo breve, natural y profesional de Ángel presentándose para FCT o Junior enfocado a esta empresa concreta."
}}
"""
    with redirect_stdout(sys.stderr):
        respuesta = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.15},
        )

    try:
        resultado = json.loads(respuesta["message"]["content"])
        return resultado
    except Exception as e:
        return {
            "error": f"Error al parsear decisión de Ollama: {e}",
            "raw": respuesta["message"]["content"],
        }


def generar_nota_obsidian(evaluacion: dict, url_origen: str) -> Path:
    """Genera la ficha en Markdown dentro de 02_Personal/Empresas siguiendo el formato oficial."""
    ciudad = evaluacion.get("ciudad_detectada", "Jaen").capitalize()
    if "Granada" in ciudad:
        carpeta_ciudad = EMPRESAS_DIR / "Granada"
    elif "Jaen" in ciudad or "Jaén" in ciudad:
        carpeta_ciudad = EMPRESAS_DIR / "Jaen"
    elif "Malaga" in ciudad or "Málaga" in ciudad:
        carpeta_ciudad = EMPRESAS_DIR / "Malaga"
    else:
        carpeta_ciudad = EMPRESAS_DIR / ciudad

    carpeta_ciudad.mkdir(parents=True, exist_ok=True)

    nombre_empresa = evaluacion.get("empresa", "Empresa_Nueva")
    slug_empresa = _slug(nombre_empresa)
    archivo_nota = carpeta_ciudad / f"{slug_empresa}.md"

    contacto = evaluacion.get("contacto_rrhh", "rrhh@empresa.com")
    sector = evaluacion.get("puesto_o_sector", "Desarrollo de Software")
    modalidad = evaluacion.get("modalidad", "Híbrido / Presencial")
    linkedin = evaluacion.get("linkedin", "[Pendiente]")

    stack_md = "\n".join([f"- {s}" for s in evaluacion.get("stack_tecnico", [])])
    puntos_dam_md = "\n".join([f"- {p}" for p in evaluacion.get("puntos_clave_dam", [])])

    carta = evaluacion.get("carta_motivacion_personalizada", "")
    asunto = f"Prácticas FCT (2º DAM) | Candidatura Desarrollo Móvil (Flutter) & Backend - Ángel Miranda Molina"

    params_gmail = {
        "authuser": "0",
        "view": "cm",
        "fs": "1",
        "to": contacto if "@" in contacto else "",
        "su": asunto,
        "body": carta,
    }
    url_gmail = f"https://mail.google.com/mail/?{urllib.parse.urlencode(params_gmail)}"

    contenido_md = f"""# 🏢 Empresa: {nombre_empresa}

- **Ubicación:** {ciudad}
- **Tipo de empresa / Sector:** {sector}
- **Modalidad:** {modalidad}
- **Score Compatibilidad:** {evaluacion.get('score', 0)}% (Aprobada por Jeb)
- **Estado:** ⏳ Pendiente de contacto
- **Fecha contacto:** [Pendiente]
- **Contacto / RRHH:** {contacto}
- **LinkedIn:** {linkedin}
- **Fuente original:** [{url_origen}]({url_origen})

---

### 🎯 Stack Técnico y Enfoque Relevante
{stack_md if stack_md else "- Desarrollo de aplicaciones móviles y soluciones backend."}

### 💡 Puntos Clave para mi Candidatura (2º DAM)
{puntos_dam_md if puntos_dam_md else "- Alto encaje con Flutter y backend con Java/Node."}

---

### ✉️ Plantilla de Correo de Candidatura
**Asunto:** {asunto}

```text
{carta}
```

---

> 🚀 **Acción Rápida:** [📩 **Abrir y Redactar en Gmail**]({url_gmail})

---

### 📝 Bitácora de Seguimiento
- [ ] Enviar correo inicial o solicitud en portal.
- [ ] Conectar en LinkedIn con responsables técnicos.
- [ ] Seguimiento tras 7-10 días.
- [ ] Notas de entrevistas o llamadas:
"""

    archivo_nota.write_text(contenido_md, encoding="utf-8")
    actualizar_dashboard_crm(nombre_empresa, sector, ciudad, slug_empresa)
    return archivo_nota


def actualizar_dashboard_crm(nombre: str, sector: str, ciudad: str, slug: str) -> None:
    """Añade la nueva empresa a la tabla correspondiente de README_CRM_Empresas.md si no existe ya."""
    if not CRM_FILE.exists():
        return

    texto_crm = CRM_FILE.read_text(encoding="utf-8")
    if "Granada" in ciudad:
        subcarpeta = "Granada"
        marcador = "## 📍 Granada"
    elif "Malaga" in ciudad or "Málaga" in ciudad:
        subcarpeta = "Malaga"
        marcador = "## 📍 Málaga" if "## 📍 Málaga" in texto_crm else "## 📍 Malaga"
    else:
        subcarpeta = "Jaen"
        marcador = "## 📍 Jaén Capital y Provincia" if "## 📍 Jaén Capital y Provincia" in texto_crm else "## 📍 Jaen"

    ficha_link = f"02_Personal/empresas/{subcarpeta}/{slug}"
    if ficha_link in texto_crm:
        return

    fila_nueva = f"| **{nombre}** | {sector} | ⏳ Pendiente | [[02_Personal/empresas/{subcarpeta}/{slug}\\|Ficha {nombre}]] |\n"
    if marcador in texto_crm:
        partes = texto_crm.split(marcador, 1)
        resto = partes[1]
        lineas = resto.split("\n")
        insertado = False
        nuevas_lineas = []
        for linea in lineas:
            nuevas_lineas.append(linea)
            if linea.strip() == "---" and not insertado:
                nuevas_lineas.insert(len(nuevas_lineas) - 1, fila_nueva.strip())
                insertado = True
        CRM_FILE.write_text(partes[0] + marcador + "\n".join(nuevas_lineas), encoding="utf-8")


PROVINCIAS_MAP = {
    "granada": "253",
    "jaen": "257",
    "jaén": "257",
    "madrid": "231",
    "malaga": "254",
    "málaga": "254",
    "sevilla": "252",
    "barcelona": "230",
}


def scrapear_ofertas_tecnoempleo(keyword: str, provincia: str = "granada", modo_visible: bool = True) -> list[dict]:
    """Scrapea ofertas de empleo de Tecnoempleo usando Scrapling en modo visible o invisible."""
    pr_id = PROVINCIAS_MAP.get(provincia.lower().strip(), provincia) if provincia else ""
    provincia_param = f"&pr={pr_id}" if pr_id else ""
    url = f"https://www.tecnoempleo.com/ofertas-trabajo/?te={urllib.parse.quote(keyword)}{provincia_param}"

    with redirect_stdout(sys.stderr):
        try:
            if modo_visible:
                resp = StealthyFetcher.fetch(url, headless=False, timeout=25000, wait=2000)
            else:
                resp = Fetcher.get(url, timeout=20)
        except Exception:
            resp = Fetcher.get(url, timeout=20)

    if resp.status != 200:
        return []

    ofertas = []
    cards = resp.css("div.p-3")
    for card in cards:
        link = card.css("h3 a::attr(href)").get()
        titulo = card.css("h3 a::text").get()
        empresa = card.css("a.text-primary::text").get()
        desc = card.css("p::text").get() or ""

        if link and titulo:
            ofertas.append({
                "titulo": titulo.strip(),
                "empresa": empresa.strip() if empresa else "Empresa Confidencial",
                "link": link.strip(),
                "descripcion": desc.strip(),
                "origen": "Tecnoempleo"
            })
    return ofertas


def procesar_empresa_completa(url: str, ciudad_manual: str = "Jaen", auto_guardar: bool = True, modo_visible: bool = True) -> str:
    """Función principal: Extrae con Scrapling (modo visible activo), evalúa con Ollama ('jeb') y guarda en Obsidian."""
    datos_web = extraer_datos_web(url, modo_visible=modo_visible)
    if "error" in datos_web:
        return f"❌ {datos_web['error']}"

    evaluacion = evaluar_con_jeb_ollama(datos_web)
    if "error" in evaluacion:
        return f"❌ {evaluacion['error']}"

    if ciudad_manual:
        evaluacion["ciudad_detectada"] = ciudad_manual

    score = evaluacion.get("score", 0)
    encaja = evaluacion.get("encaja", False)
    nombre = evaluacion.get("empresa", "Empresa")

    resumen = (
        f"📊 **Evaluación 'jeb' para {nombre}:**\n"
        f"• **Score de Compatibilidad:** {score}%\n"
        f"• **¿Encaja con tu perfil de 2º DAM?:** {'✅ SÍ' if encaja else '❌ NO'}\n"
        f"• **Stack Detectado:** {', '.join(evaluacion.get('stack_tecnico', []))}\n"
        f"• **Motivos:**\n" + "\n".join([f"  - {m}" for m in evaluacion.get("motivos_decision", [])])
    )

    if encaja and auto_guardar:
        ruta = generar_nota_obsidian(evaluacion, url)
        resumen += f"\n\n📁 **¡Ficha creada en Obsidian!**\n`{ruta.resolve()}`\n(Se ha actualizado también tu `README_CRM_Empresas.md`)."
    elif not encaja:
        resumen += f"\n\nℹ️ **No se ha guardado en Obsidian** porque la puntuación no alcanza el umbral mínimo (60%)."

    return resumen
