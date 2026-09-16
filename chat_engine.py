"""
chat_engine.py
==============
Motor de Chat Inteligente para el Dashboard de Control de Pesos (Camposol).
Analiza y extrae datos reales de muestreos (desde data_pesos.db) para responder
preguntas sobre calidad, líneas, turnos, formatos, sobrepeso (giveaway), Cpk y variabilidad.

Se conecta con la API de OpenCode Zen (https://opencode.ai/zen/v1) usando la API Key
del usuario, y cuenta con un generador analítico estadístico local en caso de saldo agotado.
"""

import sqlite3
import urllib.request
import json
import re
import numpy as np
import os
try:
    from openai import OpenAI, RateLimitError, APIError
    HAS_OPENAI_SDK = True
except ImportError:
    HAS_OPENAI_SDK = False

DB_PATH = os.path.join(os.path.dirname(__file__), 'data_pesos.db')

def _load_env_key(key_name, default=""):
    if os.environ.get(key_name):
        return os.environ[key_name].strip()
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key_name}="):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return default

OPENAI_API_KEY = _load_env_key("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
AGENTROUTER_API_KEY = _load_env_key("AGENTROUTER_API_KEY", "")
AGENTROUTER_BASE_URL = os.environ.get("AGENTROUTER_BASE_URL", "https://agentrouter.org/v1/chat/completions")
OPENCODE_API_KEY = _load_env_key("OPENCODE_API_KEY", "")
OPENCODE_BASE_URL = os.environ.get("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1/chat/completions")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_db_stats_context():
    """Extract key aggregated metrics to provide as context for the assistant."""
    conn = get_connection()
    cur = conn.cursor()

    # General totals
    cur.execute("""
        SELECT COUNT(*) as total_muestreos,
               ROUND(AVG(promedio_pesos), 2) as peso_promedio_general,
               ROUND(AVG(peso_minimo), 1) as min_promedio,
               ROUND(AVG(peso_maximo), 1) as max_promedio,
               MIN(fecha) as fecha_min,
               MAX(fecha) as fecha_max
        FROM muestreos
    """)
    gen = dict(cur.fetchone())

    # Lines summary
    cur.execute("""
        SELECT linea,
               COUNT(*) as muestreos,
               ROUND(AVG(promedio_pesos), 1) as peso_promedio,
               ROUND(AVG(peso_minimo), 1) as lsl,
               ROUND(AVG(peso_maximo), 1) as usl
        FROM muestreos
        WHERE linea IS NOT NULL AND linea != ''
        GROUP BY linea
        ORDER BY muestreos DESC
        LIMIT 12
    """)
    lines = [dict(r) for r in cur.fetchall()]

    # Formats summary
    cur.execute("""
        SELECT formato,
               COUNT(*) as muestreos,
               ROUND(AVG(promedio_pesos), 1) as peso_promedio,
               ROUND(AVG(peso_minimo), 1) as lsl,
               ROUND(AVG(peso_maximo), 1) as usl,
               ROUND(AVG(peso_nominal), 1) as nominal
        FROM muestreos
        WHERE formato IS NOT NULL AND formato != ''
        GROUP BY formato
        ORDER BY muestreos DESC
        LIMIT 8
    """)
    formatos = [dict(r) for r in cur.fetchall()]

    # Shifts summary
    cur.execute("""
        SELECT turno,
               COUNT(*) as muestreos,
               ROUND(AVG(promedio_pesos), 1) as peso_promedio
        FROM muestreos
        WHERE turno IS NOT NULL
        GROUP BY turno
    """)
    turnos = [dict(r) for r in cur.fetchall()]

    # Varieties top 5
    cur.execute("""
        SELECT variedad,
               COUNT(*) as muestreos,
               ROUND(AVG(promedio_pesos), 1) as peso_promedio
        FROM muestreos
        WHERE variedad IS NOT NULL AND variedad != ''
        GROUP BY variedad
        ORDER BY muestreos DESC
        LIMIT 6
    """)
    variedades = [dict(r) for r in cur.fetchall()]

    # Top clients
    cur.execute("""
        SELECT cliente,
               COUNT(*) as muestreos,
               ROUND(AVG(promedio_pesos), 1) as peso_promedio
        FROM muestreos
        WHERE cliente IS NOT NULL AND cliente != ''
        GROUP BY cliente
        ORDER BY muestreos DESC
        LIMIT 6
    """)
    clientes = [dict(r) for r in cur.fetchall()]

    # Packaging Technologies Summary (Sumas globales base 100: Venta, Min, Max, Real)
    cur.execute("""
        SELECT 
            m.tipo_tecnologia,
            COUNT(*) as muestreos,
            100.0 as pct_venta,
            ROUND((SUM(m.peso_minimo) / SUM(m.peso_nominal)) * 100.0, 1) as pct_minimo,
            ROUND((SUM(m.peso_maximo) / SUM(m.peso_nominal)) * 100.0, 1) as pct_maximo,
            ROUND((SUM(m.promedio_pesos) / SUM(m.peso_nominal)) * 100.0, 1) as pct_real
        FROM muestreos m
        WHERE m.tipo_tecnologia IS NOT NULL AND m.tipo_tecnologia != '' AND m.peso_nominal > 0
        GROUP BY m.tipo_tecnologia
        ORDER BY muestreos DESC
        LIMIT 8
    """)
    raw_tecs = [dict(r) for r in cur.fetchall()]
    tecnologias = []
    for t in raw_tecs:
        p_min = t['pct_minimo'] or 100.0
        p_max = t['pct_maximo'] or 100.0
        p_real = t['pct_real'] or 100.0
        if p_real < p_min - 0.01:
            st = f"Bajo Mínimo ({round(p_real - p_min, 1):+.1f}%)"
        elif p_real > p_max + 0.01:
            st = f"Sobre Máximo ({round(p_real - p_max, 1):+.1f}%)"
        else:
            st = "En Rango Conforme"
        t['estado'] = st
        tecnologias.append(t)

    conn.close()

    return {
        "general": gen,
        "lines": lines,
        "formatos": formatos,
        "turnos": turnos,
        "variedades": variedades,
        "clientes": clientes,
        "tecnologias": tecnologias
    }

def query_specific_data(user_message):
    """
    Search specific data according to the intent in user_message.
    Returns targeted data or insights.
    """
    msg_lower = user_message.lower()
    conn = get_connection()
    cur = conn.cursor()
    details = []

    # Check for specific line mention (e.g., 'línea 3', 'l3', 'linea 1', 'ulma', 'xl1')
    line_match = re.search(r'\b(l[0-9]{1,2}|l\s*[0-9]{1,2}|línea\s*[0-9]{1,2}|linea\s*[0-9]{1,2}|ulma|xl\s*[0-9]{1,2})\b', msg_lower)
    if line_match:
        raw_l = line_match.group(1).replace('línea', '').replace('linea', '').strip()
        if raw_l.startswith('l') and raw_l[1:].isdigit():
            search_line = f"%L{raw_l[1:].strip()}%"
        else:
            search_line = f"%{raw_l}%"

        cur.execute("""
            SELECT linea, COUNT(*) as total,
                   ROUND(AVG(promedio_pesos), 2) as media,
                   ROUND(MIN(promedio_pesos), 2) as min_peso,
                   ROUND(MAX(promedio_pesos), 2) as max_peso,
                   ROUND(AVG(peso_minimo), 1) as lsl,
                   ROUND(AVG(peso_maximo), 1) as usl
            FROM muestreos
            WHERE linea LIKE ?
            GROUP BY linea
        """, (search_line,))
        line_results = [dict(r) for r in cur.fetchall()]
        if line_results:
            details.append({"type": "line_detail", "data": line_results})

    # Check for format mention (e.g. '4.4', 'pinta', '6 onz', '18 oz', '1 lb')
    fmt_match = re.search(r'\b(4\.4|4,4|pinta|1 pinta|6 onz|11 oz|18 oz|1 lb|top seal)\b', msg_lower)
    if fmt_match:
        f_str = f"%{fmt_match.group(1).replace(',', '.')}%"
        cur.execute("""
            SELECT formato, COUNT(*) as total,
                   ROUND(AVG(promedio_pesos), 2) as media,
                   ROUND(AVG(peso_nominal), 1) as nominal,
                   ROUND(AVG(peso_minimo), 1) as lsl,
                   ROUND(AVG(peso_maximo), 1) as usl
            FROM muestreos
            WHERE formato LIKE ?
            GROUP BY formato
        """, (f_str,))
        fmt_results = [dict(r) for r in cur.fetchall()]
        if fmt_results:
            details.append({"type": "format_detail", "data": fmt_results})

    # Check for shift mention
    if 'turno' in msg_lower or 'día' in msg_lower or 'noche' in msg_lower:
        cur.execute("""
            SELECT turno, COUNT(*) as total,
                   ROUND(AVG(promedio_pesos), 2) as media,
                   ROUND(AVG(peso_minimo), 1) as lsl,
                   ROUND(AVG(peso_maximo), 1) as usl
            FROM muestreos
            WHERE turno IS NOT NULL
            GROUP BY turno
        """)
        details.append({"type": "shift_detail", "data": [dict(r) for r in cur.fetchall()]})

    # Check for date / fecha
    date_match = re.search(r'\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b', user_message)
    if date_match:
        d_val = date_match.group(1)
        cur.execute("""
            SELECT fecha, COUNT(*) as total,
                   ROUND(AVG(promedio_pesos), 2) as media,
                   COUNT(DISTINCT linea) as lineas_activas
            FROM muestreos
            WHERE fecha LIKE ?
            GROUP BY fecha
        """, (f"%{d_val}%",))
        d_res = [dict(r) for r in cur.fetchall()]
        if d_res:
            details.append({"type": "date_detail", "data": d_res})

    conn.close()
    return details

def call_openai_api(messages, model="gpt-4o-mini"):
    """
    Attempt calling official OpenAI API using the official OpenAI Python SDK.
    Returns (success: bool, reply_or_error: str, model_used: str, error_code: str).
    """
    if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith("sk-"):
        return False, "OpenAI API Key no configurada", model, "no_key"

    if HAS_OPENAI_SDK:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1200,
                temperature=0.2
            )
            if completion.choices and len(completion.choices) > 0:
                reply = completion.choices[0].message.content
                return True, reply, model, ""
            return False, "Respuesta vacía de OpenAI", model, "empty_response"
        except RateLimitError as e:
            code = getattr(e, 'code', '') or 'rate_limit'
            msg = getattr(e, 'message', str(e))
            return False, f"OpenAI RateLimitError ({code}): {msg}", model, code
        except APIError as e:
            code = getattr(e, 'code', '') or 'api_error'
            msg = getattr(e, 'message', str(e))
            return False, f"OpenAI APIError ({code}): {msg}", model, code
        except Exception as e:
            return False, f"Error OpenAI SDK: {str(e)}", model, "sdk_error"

    # Fallback to direct HTTP if SDK is unavailable
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1200,
        "temperature": 0.2
    }

    req = urllib.request.Request(
        OPENAI_BASE_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if "choices" in data and len(data["choices"]) > 0:
                reply = data["choices"][0]["message"]["content"]
                return True, reply, model, ""
            return False, "Respuesta vacía de OpenAI", model, "empty_response"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        err_code = ""
        err_msg = err_body
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("error", {}).get("message", err_body)
            err_code = err_json.get("error", {}).get("code", "")
        except Exception:
            pass
        return False, f"OpenAI HTTP {e.code}: {err_msg}", model, err_code
    except Exception as e:
        return False, f"Error de conexión con OpenAI: {str(e)}", model, "network_error"

def call_agentrouter_api(messages):
    """
    Attempt calling AgentRouter (https://agentrouter.org/v1) with Claude Opus / DeepSeek / GPT.
    Uses required authentication and user-agent headers.
    """
    headers = {
        "Authorization": f"Bearer {AGENTROUTER_API_KEY}",
        "x-api-key": AGENTROUTER_API_KEY,
        "User-Agent": "claude-cli/2.1.0 (external, cli)",
        "x-stainless-lang": "js",
        "x-stainless-package-version": "0.2.1",
        "x-stainless-os": "Windows",
        "x-stainless-arch": "x64",
        "Content-Type": "application/json"
    }

    models_to_try = ["claude-opus-4-8", "deepseek-v4-flash", "gpt-5.6-sol"]
    last_err = ""
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.2
        }
        req = urllib.request.Request(
            AGENTROUTER_BASE_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if "choices" in data and len(data["choices"]) > 0:
                    reply = data["choices"][0]["message"]["content"]
                    return True, reply, model
        except urllib.error.HTTPError as e:
            last_err = e.read().decode('utf-8', errors='ignore')
            if "Budget pool quota has been exhausted" in last_err or e.code == 402:
                return False, "Budget pool quota has been exhausted", model
            continue
        except Exception as e:
            last_err = str(e)
            continue

    return False, last_err, None

def call_opencode_api(messages):
    """Attempt calling OpenCode Zen API. Returns (success, response_or_error)."""
    payload = {
        "model": "claude-sonnet-4-6",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.2
    }
    req = urllib.request.Request(
        OPENCODE_BASE_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {OPENCODE_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "opencode"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            reply = data['choices'][0]['message']['content']
            return True, reply
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        return False, f"HTTPError {e.code}: {err_body}"
    except Exception as e:
        return False, str(e)

def generate_local_response(user_message, stats_ctx, specific_data):
    """
    Generate an intelligent, highly informative and beautifully formatted
    response using local data analytics if OpenCode API is unavailable or has no balance.
    """
    msg_lower = user_message.lower()
    gen = stats_ctx["general"]
    lines = stats_ctx["lines"]
    formatos = stats_ctx["formatos"]
    turnos = stats_ctx["turnos"]

    # 1. Best / worst line query
    if any(k in msg_lower for k in ["mejor línea", "peor línea", "cumplimiento por línea", "comparar línea", "líneas", "lineas"]):
        resp = "### 📊 Comparativa de Líneas de Empaque\n\n"
        resp += f"En la base de datos se tienen registrados **{gen['total_muestreos']:,} muestreos** a lo largo de las distintas líneas de empaque:\n\n"
        resp += "| Línea | Muestreos | Peso Promedio | Rango LSL-USL |\n"
        resp += "| :--- | :---: | :---: | :---: |\n"
        for l in lines[:7]:
            resp += f"| **{l['linea']}** | {l['muestreos']:,} | `{l['peso_promedio']} g` | [{l['lsl']}g - {l['usl']}g] |\n"
        
        resp += "\n**Conclusiones Clave:**\n"
        resp += "- Las líneas con mayor volumen de muestreo reflejan la producción principal de la planta.\n"
        resp += "- La variación entre líneas se debe principalmente al tipo de formato asignado y calibración de celdas de carga.\n"
        resp += "- Puedes ver la dispersión detallada de cada línea en el gráfico **Box Plot** del dashboard."
        return resp

    # 2. Formats / Giveaway / Sobrepeso
    if any(k in msg_lower for k in ["sobrepeso", "giveaway", "formato", "formatos", "peso nominal", "tolerancia"]):
        resp = "### 📦 Análisis por Formato y Sobrepeso (Giveaway)\n\n"
        resp += "El sobrepeso representa fruta regalada por encima del límite superior del cliente. Aquí el resumen de los principales formatos en el Excel:\n\n"
        resp += "| Formato | Muestreos | Peso Promedio | Nominal | Límites [Mín - Máx] |\n"
        resp += "| :--- | :---: | :---: | :---: | :---: |\n"
        for f in formatos[:6]:
            nom = f"{f['nominal']}g" if f['nominal'] else "N/A"
            resp += f"| **{f['formato']}** | {f['muestreos']:,} | **{f['peso_promedio']} g** | {nom} | [{f['lsl']}g - {f['usl']}g] |\n"
        
        resp += "\n**Observaciones SPC:**\n"
        resp += "- Cuando el peso promedio supera el límite superior (USL), el proceso genera **Giveaway económico**.\n"
        resp += "- En formatos pequeños (como 4.4 onz o 6 onz), desviaciones de apenas 2 a 3 gramos por clamshell representan toneladas de fruta al final de la campaña.\n"
        resp += "- Puedes ver la comparativa interactiva completa en el nuevo gráfico **% Desviación por Tipo de Tecnología** en el dashboard.\n"
        return resp

    # 2.5 Technology Deviations & Excess (3 Marks)
    if any(k in msg_lower for k in ["tecnologia", "tecnología", "tecnologías", "deshidratacion", "deshidratación", "macroperforada", "flow pack", "driscoll", "reducir porcentaje", "exceso por tecnologia"]):
        tecs = stats_ctx.get("tecnologias", [])
        resp = "### 🛡️ Análisis de Desviación & Exceso de Fruta por Tipo de Tecnología\n\n"
        resp += "Comparativa de las **3 marcas de control** para medir la deshidratación y sobrepeso de empaque:\n"
        resp += "1. **Peso Venta (Col I)**: Destino (Base 100%)\n"
        resp += "2. **Peso Tecnología (Col O)**: Límite máximo admitido con deshidratación prevista\n"
        resp += "3. **Peso Real (Col BQ)**: Promedio empacado real en planta\n\n"
        resp += "| Tipo Tecnología | Muestreos | Venta (g) | % Meta Tec | % Real Empacado | 🚨 Exceso a Reducir |\n"
        resp += "| :--- | :---: | :---: | :---: | :---: | :---: |\n"
        for t in tecs[:7]:
            exc_badge = f"**+{t['pct_exceso']}%**" if t['pct_exceso'] > 0 else f"`{t['pct_exceso']}%`"
            resp += f"| **{t['tipo_tecnologia']}** | {t['muestreos']:,} | {t['venta_g']}g | +{t['pct_tec']}% | +{t['pct_real']}% | {exc_badge} |\n"
        resp += "\n**Interpretación Económica:**\n"
        resp += "- **Exceso Positivo (+)**: Fruta regalada por encima de lo que requiere la tecnología para compensar el viaje. Se debe calibrar las balanzas a la baja en dicho porcentaje.\n"
        resp += "- **Exceso Negativo (-)**: Proceso ajustado con margen de seguridad respecto al límite máximo.\n"
        resp += "- Revisa el gráfico **% Desviación por Tipo de Tecnología** en el dashboard para alternar entre `% Desviación`, `% Base 100` y `Gramos`."
        return resp

    # 3. Shifts (Turno Día vs Noche)
    if any(k in msg_lower for k in ["turno", "turnos", "día", "dia", "noche"]):
        resp = "### ⏱️ Comparativa de Turnos (Turno 1 vs Turno 2)\n\n"
        resp += "| Turno | Muestreos Realizados | Peso Promedio General |\n"
        resp += "| :--- | :---: | :---: |\n"
        for t in turnos:
            nombre = "Turno 1 (Día)" if str(t['turno']) == '1' else ("Turno 2 (Noche)" if str(t['turno']) == '2' else f"Turno {t['turno']}")
            resp += f"| **{nombre}** | {t['muestreos']:,} muestreos | **{t['peso_promedio']} g** |\n"
        
        resp += "\n**Recomendación Operativa:**\n"
        resp += "- Compara la estabilidad de pesaje entre turnos en la **Carta de Control X̄** filtrando por Turno en el panel lateral."
        return resp

    # 4. Underweight / Bajo Peso / Riesgo de Calidad
    if any(k in msg_lower for k in ["bajo peso", "peso mínimo", "minimo", "rechazo", "riesgo", "fuera de norma"]):
        resp = "### ⚠️ Análisis de Bajo Peso y Cumplimiento Legal\n\n"
        resp += f"De un total de **{gen['total_muestreos']:,} muestreos** evaluados:\n"
        resp += f"- **Peso mínimo promedio de especificación:** `{gen['min_promedio']} g`.\n"
        resp += f"- **Peso promedio registrado:** `{gen['peso_promedio_general']} g`.\n\n"
        resp += "**Puntos Críticos de Calidad:**\n"
        resp += "1. Los clamshells por debajo del peso mínimo (< LSL) generan **rechazo directo de pallets en destino** e incumplimiento con retailers.\n"
        resp += "2. En el gráfico de campana de Gauss, estos corresponden al área a la izquierda de la línea discontinua de **Peso Mínimo**.\n"
        resp += "3. Puedes filtrar en la tabla inferior para identificar los viajes y horas exactas donde ocurrieron."
        return resp

    # 5. Cpk / Capacidad de Proceso
    if any(k in msg_lower for k in ["cpk", "cp", "capacidad", "gauss", "normal", "dispersión"]):
        resp = "### 📈 Capacidad de Proceso (Índices Cp y Cpk)\n\n"
        resp += "El índice **Cpk** mide tanto la dispersión como el centrado del proceso respecto a los límites de tolerancia:\n\n"
        resp += "- **Cpk ≥ 1.33:** Proceso Excelente (Capaz, virtualmente sin defectos).\n"
        resp += "- **1.00 ≤ Cpk < 1.33:** Proceso Aceptable (Requiere monitoreo).\n"
        resp += "- **Cpk < 1.00:** Proceso Incapaz (Genera producto fuera de especificación).\n\n"
        resp += f"Para el conjunto general de datos, el peso promedio es `{gen['peso_promedio_general']} g` con límites promedio de `[{gen['min_promedio']}g - {gen['max_promedio']}g]`.\n"
        resp += "💡 *Consejo:* Para evaluar el Cpk con máxima precisión matemática, selecciona un único formato en los filtros (por ejemplo **4.4 onz** o **1 pinta**), ya que mezclar formatos con distintos pesos nominales dispersa artificialmente la campana."
        return resp

    # 6. Specific line or format details found in query_specific_data
    if specific_data:
        for item in specific_data:
            if item["type"] == "line_detail":
                resp = f"### 🔍 Información de Línea de Empaque\n\n"
                for d in item["data"]:
                    resp += f"**Línea {d['linea']}:**\n"
                    resp += f"- **Muestreos:** {d['total']:,}\n"
                    resp += f"- **Peso Promedio:** `{d['media']} g`\n"
                    resp += f"- **Rango observado:** `{d['min_peso']} g` a `{d['max_peso']} g`\n"
                    resp += f"- **Tolerancia de referencia:** [{d['lsl']}g - {d['usl']}g]\n\n"
                return resp
            elif item["type"] == "format_detail":
                resp = f"### 🔍 Información del Formato\n\n"
                for d in item["data"]:
                    resp += f"**Formato {d['formato']}:**\n"
                    resp += f"- **Muestreos analizados:** {d['total']:,}\n"
                    resp += f"- **Peso Promedio:** `{d['media']} g`\n"
                    resp += f"- **Peso Nominal (Target):** `{d['nominal']} g`\n"
                    resp += f"- **Límites de tolerancia:** Mín `{d['lsl']} g` | Máx `{d['usl']} g`\n\n"
                return resp

    # Default general summary
    resp = f"### 🍇 Resumen del Control de Pesos de Clamshells\n\n"
    resp += f"He consultado el dataset del Excel (`Data pesos.xlsx`). Aquí están los datos consolidados:\n\n"
    resp += f"- **Total Muestreos:** {gen['total_muestreos']:,}\n"
    resp += f"- **Clamshells individuales:** Más de 1.3 millones de pesajes (T1 a T48)\n"
    resp += f"- **Rango de Fechas:** Del `{gen['fecha_min']}` al `{gen['fecha_max']}`\n"
    resp += f"- **Peso Promedio Global:** `{gen['peso_promedio_general']} g`\n"
    resp += f"- **Límites Promedio:** Mín `{gen['min_promedio']} g` | Máx `{gen['max_promedio']} g`\n\n"
    resp += "**Puedes preguntarme cosas como:**\n"
    resp += "- *¿Cuál es la línea con mayor cumplimiento?*\n"
    resp += "- *¿Qué formato genera mayor sobrepeso o giveaway?*\n"
    resp += "- *¿Cómo se comparan los turnos 1 y 2?*\n"
    resp += "- *¿Cuál es el promedio y tolerancia para el formato 4.4 onz?*\n"
    resp += "- *Detalles de la Línea L3 o ULMA.*"
    return resp

def process_chat_query(user_message, history=None):
    """
    Main entry point for processing a chat message from the user.
    Attempts OpenCode API first; falls back to comprehensive local analytics engine.
    """
    stats_ctx = get_db_stats_context()
    specific_data = query_specific_data(user_message)

    # Prepare context text for the AI
    data_context_text = f"""
INFORMACIÓN REAL EXTRAÍDA DE LA BASE DE DATOS (Excel 'Data pesos.xlsx'):
- Total Muestreos: {stats_ctx['general']['total_muestreos']}
- Fechas disponibles: {stats_ctx['general']['fecha_min']} a {stats_ctx['general']['fecha_max']}
- Peso promedio general: {stats_ctx['general']['peso_promedio_general']} g
- Peso mínimo promedio: {stats_ctx['general']['min_promedio']} g
- Peso máximo promedio: {stats_ctx['general']['max_promedio']} g

LÍNEAS DE EMPAQUE (Top):
{json.dumps(stats_ctx['lines'], ensure_ascii=False, indent=2)}

FORMATOS DE CLAMSHELL:
{json.dumps(stats_ctx['formatos'], ensure_ascii=False, indent=2)}

TURNOS:
{json.dumps(stats_ctx['turnos'], ensure_ascii=False, indent=2)}

VARIEDADES TOP:
{json.dumps(stats_ctx['variedades'], ensure_ascii=False, indent=2)}

DATOS ESPECÍFICOS CONSULTADOS PARA LA PREGUNTA:
{json.dumps(specific_data, ensure_ascii=False, indent=2) if specific_data else "Ninguno específico adicional"}
"""

    system_prompt = f"""Eres el Asistente Experto en Control Estadístico de Calidad y Pesos de Clamshell de Arándano en Camposol.
Tu labor es responder con máxima claridad, profesionalismo y precisión matemática a las preguntas del usuario basándote EXCLUSIVAMENTE en los datos reales del archivo Excel proporcionados a continuación.
{data_context_text}

Instrucciones:
1. Responde en español formal, técnico y conciso.
2. Usa tablas Markdown, negritas y viñetas para que la información sea fácil de leer.
3. Si el usuario pregunta por una línea, turno o formato, da las cifras exactas del contexto.
4. Si se consulta sobre SPC, Cpk o giveaway, explica la implicancia en calidad y costos agroindustriales.
"""

    messages = [{"role": "system", "content": system_prompt}]
    if history and isinstance(history, list):
        for h in history[-4:]: # include last few turns
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": user_message})

    # 1. Try calling official OpenAI API first (user's key: gpt-4o-mini)
    oa_success, oa_reply, oa_model, oa_err_code = call_openai_api(messages, model="gpt-4o-mini")
    if oa_success:
        return {
            "status": "success",
            "source": f"openai_{oa_model}",
            "reply": oa_reply
        }

    # 2. Try calling AgentRouter API (Claude Opus / DeepSeek / GPT)
    ar_success, ar_reply, ar_model = call_agentrouter_api(messages)
    if ar_success:
        return {
            "status": "success",
            "source": f"agentrouter_{ar_model}",
            "reply": ar_reply
        }

    # 3. Try calling OpenCode Zen API
    oc_success, oc_reply_or_err = call_opencode_api(messages)
    if oc_success:
        return {
            "status": "success",
            "source": "opencode_ai",
            "reply": oc_reply_or_err
        }

    # 4. Fallback to our local SPC statistical engine (100% grounded in the Excel data)
    local_reply = generate_local_response(user_message, stats_ctx, specific_data)

    if oa_err_code == "credit_balance_exhausted":
        note = (
            "\n\n---\n"
            "*ℹ️ Tu API Key de OpenAI está configurada e integrada en el sistema. "
            "Actualmente OpenAI reporta: **'You have no credits remaining'** (saldo agotado en la cuenta de OpenAI). "
            "Para que GPT-4o-mini responda directamente, añade créditos en tu cuenta en "
            "[platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing/). "
            "Mientras tanto, el chat opera automáticamente con el motor analítico local sobre los datos reales del Excel.*"
        )
    else:
        note = f"\n\n---\n*ℹ️ Consulta resuelta con el motor analítico de datos (Excel). (OpenAI status: {oa_reply})*"

    return {
        "status": "success",
        "source": "local_data_engine",
        "reply": local_reply + note
    }
