# ======================================================
# SISTEMA OROEXPRESS UNIFICADO - DASHBOARD INTEGRAL
# ======================================================
from dash import Dash, html, dcc, Input, Output, State
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import requests, re, os
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import investpy
import base64
from pathlib import Path
import json

print("🚀 INICIANDO SISTEMA OROEXPRESS UNIFICADO...")

# 🥇 Sustituimos InvestPy (que fallaba) por nuestro módulo nuevo
from data.kitco_gold import get_gold_previous_day as obtener_oro_dia_anterior

# ======================================================
# CONFIGURACIÓN INICIAL
# ======================================================
from pathlib import Path

# 📁 Ruta base dinámica (carpeta donde está app.py)
BASE_DIR = Path(__file__).resolve().parent

# ======================================================
# AUTENTICACIÓN DE USUARIOS
# ======================================================
from werkzeug.security import check_password_hash

# 📁 Archivo con usuarios y contraseñas (hash)
USERS_FILE = BASE_DIR / "usuarios.json"

print(f"🧭 Archivo de usuarios: {USERS_FILE.resolve()}")
print(f"🗂 Existe?: {USERS_FILE.exists()}")


def cargar_usuarios():
    """Carga los usuarios desde usuarios.json. Devuelve {} si no existe."""
    try:
        if USERS_FILE.exists():
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            print("⚠️ No existe usuarios.json, se usará un dict vacío.")
            return {}
    except Exception as e:
        print(f"❌ Error cargando usuarios.json: {e}")
        return {}

# Estado de autenticación simple en memoria (válido para 1 proceso)
usuario_autenticado = {"activo": False, "nombre": None}


# ✅ Definición de rutas relativas y portables
CERT_PATH = BASE_DIR / "certificados" / "Pbit.bancodebogota.crt"
HIST_PATH = BASE_DIR / "data" / "historial_precios.csv"
LOGO_PATH = BASE_DIR / "assets" / "logo.png"

# ======================================================
# INICIALIZAR APP (evita error de IDs fuera del layout activo)
# ======================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "OroExpress - Lingotes"
server = app.server

# ======================================================
# PERSISTENCIA EN DISCO (JSON)
# ======================================================
class PersistenceManager:
    def __init__(self):
        self.data_dir = Path("storage")
        self.data_dir.mkdir(exist_ok=True)
        self.percentages_file = self.data_dir / "calculator_percentages.json"
        print(f"📁 Persistencia en disco: {self.data_dir.absolute()}")

    def save_percentages(self, compra: float, venta: float, venta_directa: float) -> bool:
        try:
            data = {
                'compra': compra,
                'venta': venta,
                'venta_directa': venta_directa,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.percentages_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Guardado: Compra={compra}%, Venta={venta}%, Venta Directa={venta_directa}%")
            return True
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            return False

    def load_percentages(self) -> dict:
        try:
            if self.percentages_file.exists():
                with open(self.percentages_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"📂 Cargado desde disco: {data}")
                return data
            else:
                print("📂 Creando archivo con valores por defecto")
                self.save_percentages(0.0, 0.0, 0.0)
                return self.get_default()
        except Exception as e:
            print(f"❌ Error cargando: {e}")
            return self.get_default()

    def get_default(self) -> dict:
        return {
            'compra': 0.0,
            'venta': 0.0,
            'venta_directa': 0.0,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

persistence_manager = PersistenceManager()
percentages_data = persistence_manager.load_percentages()

# ======================================================
# CSS EMBEBIDO UNIFICADO
# ======================================================
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --primary-gold: #FFD700;
                --dark-bg: #171c26;
                --card-bg-yellow: rgba(255, 196, 12, 0.85);
                --card-bg-white: rgba(248, 249, 250, 0.85);
                --text-dark: #171c26;
                --text-light: #ecf0f1;
                --accent-blue: #2c3e50;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }

            body, html {
                height: 100%;
                background: linear-gradient(135deg, var(--dark-bg) 0%, #2c3e50 100%) !important;
                background-attachment: fixed;
                background-size: cover;
            }
            body {
                background-color: var(--dark-bg) !important;
                font-family: "Arial", "Helvetica", sans-serif;
                line-height: 1.6;
                overflow-x: hidden;
            }

            .container-wide { max-width: 1280px; margin: 0 auto; padding: 0 1rem; }
            .header-container {
                height: 85px;
                display: flex; align-items: center;
                margin-bottom: 5px; justify-content: space-between;
                position: relative;
            }
            .logo-img { max-height: 75px; max-width: 330px; object-fit: contain; }

            /* ====== TIRILLA BANCO ====== */
            .tirilla-container { flex: 1; overflow: hidden; position: relative; background: transparent !important; margin-left: 20px; height: 30px; display: flex; align-items: center; justify-content: flex-end; }
            .tirilla-wrapper { width: 100%; overflow: hidden; position: relative; height: 30px; display: flex; align-items: center; }
            .tirilla-marquee {
                display: inline-block; white-space: nowrap; animation: marquee 20s linear infinite;
                color: #00FF00; font-size: 14px; font-weight: bold; font-family: "Calibri", "Arial", sans-serif;
                padding: 6px 0; position: absolute; left: 100%;
            }
            .tirilla-marquee:hover { animation-play-state: paused; }
            @keyframes marquee { 0% { left: 100%; } 100% { left: -100%; } }
            .tirilla-time { color: #00FF00; font-weight: bold; }
            .tirilla-venta, .tirilla-compra { color: #FFFFFF; font-weight: bold; }

            .divider {
                border: none; height: 2px;
                background: linear-gradient(90deg, transparent, var(--primary-gold), transparent);
                margin: 8px 0;
            }

            /* ====== ICON BUTTONS (gear & back) ====== */
            .icon-btn {
                position: absolute; top: 55px; right: 10px;
                width: 38px; height: 38px; border-radius: 50%;
                border: 2px solid var(--primary-gold);
                background: rgba(255, 215, 0, 0.12);
                color: var(--primary-gold); font-weight: 900; font-size: 18px;
                display: flex; align-items: center; justify-content: center;
                cursor: pointer;
                transition: transform .2s ease, box-shadow .2s ease, background .2s ease;
            }
            .icon-btn:hover { transform: scale(1.07); box-shadow: 0 6px 16px rgba(255,215,0,.25); background: rgba(255,215,0,0.18); }
            .icon-btn:focus { outline: none; }

            /* ====== CARDS ====== */
            .price-block { padding: 15px; border-radius: 10px; min-height: 240px; margin-bottom: 15px; box-shadow: 0 3px 10px rgba(0,0,0,0.15); backdrop-filter: blur(5px); }
            .price-block-anterior { background: var(--card-bg-yellow); color: var(--text-dark); border: 2px solid #e0b000; }
            .price-block-vivo { background: var(--card-bg-white); color: var(--text-dark); border: 2px solid #dee2e6; }
            .price-block-anterior *, .price-block-vivo * { opacity: 1 !important; color: inherit !important; }

            .block-title { text-align: center; margin-bottom: 15px; font-size: 1.2em; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
            .price-table { width: 100%; border-collapse: collapse; font-size: 0.95em; }
            .price-table th { padding: 10px 8px; text-align: left; border-bottom: 2px solid var(--text-dark); font-weight: 700; background-color: rgba(23, 28, 38, 0.1); }
            .price-table td { padding: 8px; text-align: left; border-bottom: 1px solid rgba(23, 28, 38, 0.2); font-weight: 600; }
            .refresh-indicator { text-align: right; font-size: 0.75em; color: #6c757d; margin-top: 12px; font-style: italic; }

            /* ====== CALCULADORA ====== */
            .calculator-horizontal { background: rgba(44, 62, 80, 0.85); border: 2px solid var(--primary-gold); border-radius: 10px; padding: 15px; margin-top: 15px; }
            .section-title { color: var(--text-light); font-size: 1.2em; font-weight: 700; margin-bottom: 15px; text-align: center; text-transform: uppercase; letter-spacing: 0.5px; }
            .calc-item { text-align: center; padding: 12px; }
            .calc-header { color: var(--primary-gold); font-weight: 700; margin-bottom: 8px; font-size: 0.95em; text-transform: uppercase; }
            .calc-label { color: #bdc3c7; font-size: 0.8em; margin: 6px 0 3px 0; font-weight: 500; }
            .calc-result { font-size: 1.3em; font-weight: bold; color: var(--primary-gold); margin: 8px 0; padding: 10px; border: 2px solid var(--primary-gold); border-radius: 6px; background: rgba(255, 215, 0, 0.1); }
            .dash-input { width: 100%; padding: 6px 10px; border: 1px solid var(--primary-gold); border-radius: 5px; background: #f8f9fa; color: var(--text-dark); font-weight: 600; text-align: center; font-size: 0.9em; }
            .dash-button { background: linear-gradient(135deg, var(--primary-gold), #e6c200); color: var(--text-dark); border: none; border-radius: 5px; padding: 8px 12px; font-weight: 700; width: 100%; margin-top: 6px; cursor: pointer; font-size: 0.9em; text-transform: uppercase; }

            /* ====== LINGOTES VIEW ====== */
            .lingotes-container { min-height: 100vh; background: linear-gradient(135deg, var(--dark-bg) 0%, #2c3e50 100%); padding: 2rem 0; }
            .lingotes-card { background: rgba(255, 215, 0, 0.1); border: 2px solid var(--primary-gold); border-radius: 15px; padding: 2rem; margin: 1rem 0; backdrop-filter: blur(10px); transition: transform 0.3s ease, box-shadow 0.3s ease; }
            .lingotes-card:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(255, 215, 0, 0.2); }
            .lingotes-title { color: var(--primary-gold); font-size: 2.5rem; font-weight: bold; text-align: center; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 2px; }
            .card-title { color: var(--primary-gold); font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 1rem; text-transform: uppercase; }
            .card-value { color: #ffffff; font-size: 2rem; font-weight: bold; text-align: center; margin: 1rem 0; }
            .card-percentage { display: none !important;}

            /* ✨ RESALTADO SOLO PARA EL CARD "VENTA" (antes COMPRA) */
            @keyframes pulse-gold {
    0% { box-shadow: 0 0 18px rgba(255, 215, 0, 0.35); transform: scale(1.02); }
    50% { box-shadow: 0 0 40px rgba(255, 215, 0, 0.70); transform: scale(1.045); }
    100% { box-shadow: 0 0 18px rgba(255, 215, 0, 0.35); transform: scale(1.02); }
}

.lingotes-card-venta {
    border: 3px solid #FFD700 !important;
    background: radial-gradient(ellipse at top, rgba(255, 215, 0, 0.20), rgba(255, 215, 0, 0.06) 60%) !important;
    animation: pulse-gold 2.8s ease-in-out infinite;
}

/* 🎨 ESTILO BLANCO TRANSLÚCIDO PARA COMPRA Y CONTRATACIÓN */
.lingotes-card-blanca {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 2px solid rgba(255, 255, 255, 0.7) !important;
    color: #ffffff !important;
}
            #hora-actualizacion-lingotes {
    display: none !important;
            }

        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ======================================================
# EXTRACCIÓN DE DATOS (fuentes externas)
# ======================================================
def obtener_dolar_bogota():
    try:
        print("🔄 Extrayendo datos Banco Bogotá...")
        CERTIFICADO_BB = Path(CERT_PATH)
        URL_BB = "https://pbit.bancodebogota.com/Indicadores/Tirilla.aspx"
        response = requests.get(URL_BB, verify=CERTIFICADO_BB if CERTIFICADO_BB.exists() else True,
                                timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        marquee = soup.find("marquee", {"id": "ctl00_MarPrinc"})
        if marquee:
            texto = marquee.get_text(" ", strip=True)
            match = re.search(r"Dolar\s+Venta:\s*([\d.,]+)\s+Dolar\s+Compra:\s*([\d.,]+)", texto, re.I)
            if match:
                venta = float(match.group(1).replace(",", "."))
                compra = float(match.group(2).replace(",", "."))
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"✅ Banco Bogotá - Compra: {compra}, Venta: {venta}")
                return compra, venta, timestamp
        return 3900.0, 3950.0, datetime.now().strftime("%H:%M:%S")
    except Exception as e:
        print(f"❌ Error Banco Bogotá: {e}")
        return 3900.0, 3950.0, datetime.now().strftime("%H:%M:%S")

def obtener_precio_oro_kitco():
    try:
        url = "https://www.kitco.com/charts/livegold.html"
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        s = BeautifulSoup(r.text, "html.parser")
        h3 = s.find("h3", class_="font-mulish")
        if h3:
            valor = h3.text.strip().replace(",", "")
            return float(valor)
        return 1950.00
    except Exception as e:
        print(f"❌ Error Kitco: {e}")
        return 1950.00

def obtener_trm_banrep():
    """
    Devuelve la TRM oficial del día anterior o una TRM manual si está configurada.
    Permite sobreescribir el valor desde un archivo local (trm_manual.json).
    """
    try:
        manual_file = Path("storage/trm_manual.json")
        if manual_file.exists():
            with open(manual_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                trm_manual = float(data.get("trm", 0))
                fecha_manual = data.get("fecha", "manual")
                if trm_manual > 0:
                    print(f"📘 Usando TRM manual ({fecha_manual}): ${trm_manual:,.0f} COP")
                    return trm_manual, fecha_manual

        hoy = date.today().isoformat()
        url = "https://www.datos.gov.co/resource/32sa-8pi3.json?$limit=5&$order=vigenciadesde%20desc"
        r = requests.get(url, timeout=10)
        data = r.json()
        for item in data:
            fecha = item.get("vigenciadesde", "")[:10]
            if fecha < hoy:
                trm = float(item["valor"])
                print(f"📅 TRM del día anterior ({fecha}): ${trm:,.0f} COP")
                return trm, fecha

        ultima = data[0]
        trm = float(ultima["valor"])
        fecha = ultima["vigenciadesde"][:10]
        print(f"⚠️ Fallback TRM última publicada ({fecha}): ${trm:,.0f} COP")
        return trm, fecha
    except Exception as e:
        print(f"❌ Error al obtener TRM: {e}")
        return 3950.0, "Error"
    
def formato_colombiano(valor):
    """Formatea números en estilo colombiano SIN decimales."""
    try:
        return f"{int(round(float(valor))):,}".replace(",", ".")
    except:
        return str(valor)
def calcular_precios_tiempo_real():
    try:
        dolar_compra, dolar_venta, timestamp = obtener_dolar_bogota()
        oro_usd = obtener_precio_oro_kitco()
        full_cop = (oro_usd / 31.10347) * dolar_compra
        return {
            'dolar_compra': dolar_compra,
            'dolar_venta': dolar_venta,
            'oro_usd': oro_usd,
            'full_cop': full_cop,
            'actualizado': timestamp
        }
    except Exception as e:
        print(f"💥 Error cálculo precios: {e}")
        return {
            'dolar_compra': 3900.0,
            'dolar_venta': 3950.0,
            'oro_usd': 1950.0,
            'full_cop': 245000.0,
            'actualizado': f"Error - {datetime.now().strftime('%H:%M:%S')}"
        }

# ======================================================
# COMPONENTES / WIDGETS
# ======================================================
def crear_logo():
    try:
        with open(LOGO_PATH, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
        return html.Img(src=f"data:image/png;base64,{logo_data}", className="logo-img", style={'marginLeft': '10px'})
    except Exception as e:
        print(f"⚠️ Error cargando logo: {e}")
        return html.H2("🏦 OroExpress", style={'margin': '0','color': 'white','fontSize': '26px','fontWeight': 'bold','marginLeft': '10px'})

def crear_tirilla_estilo_banco(precios):
    try:
        venta = precios['dolar_venta']
        compra = precios['dolar_compra']
        timestamp = precios['actualizado']
        contenido_tirilla = html.Div([
            html.Span(f"{timestamp} ", className="tirilla-time"),
            html.Span("Dolar Venta: ", className="tirilla-venta"),
            html.Span(f"{formato_colombiano(venta).replace(',0', '')} ", className="tirilla-venta"),
            html.Span("Dolar Compra: ", className="tirilla-compra"),
            html.Span(f"{formato_colombiano(compra).replace(',0', '')}", className="tirilla-compra")
        ], className="tirilla-marquee")
        return html.Div(html.Div(contenido_tirilla, className="tirilla-wrapper"), className="tirilla-container")
    except Exception as e:
        print(f"⚠️ Error en tirilla: {e}")
        return html.Div("Cargando...", className="tirilla-container")

# ======================================================
# LAYOUT LINGOTES
# ======================================================
def layout_lingotes():
    header = html.Div([
        dbc.Row([
            dbc.Col([crear_logo()], width=3),
            dbc.Col([], width=9)
        ], className="header-container"),
        html.Button("👤", id="open-login-modal", className="icon-btn", n_clicks=0)
    ], style={"position": "relative"})

    # ======================================================
    # MODAL UNIFICADO: LOGIN + ACTUALIZAR USUARIO/CONTRASEÑA
    # ======================================================
    modal = dbc.Modal([
        dbc.ModalHeader("Acceso Administrativo"),
        dbc.ModalBody([
            # --- LOGIN NORMAL ---
            html.Div(id="login-section", children=[
                dbc.Input(id="login-username", placeholder="Usuario", type="text", className="mb-2"),
                dbc.Input(id="login-password", placeholder="Contraseña", type="password", className="mb-3"),
                html.Div(id="login-message", className="text-danger mb-2 text-center"),
                dbc.Button("Ingresar", id="login-submit", color="primary", className="w-100 mb-3"),
                html.Div([
                    html.A("🔄 Actualizar usuario o contraseña", id="show-update-form", href="#",
                           style={"color": "#FFD700", "textDecoration": "none", "fontSize": "0.9em"})
                ], className="text-center")
            ]),

            # --- VERIFICACIÓN DE CONTRASEÑA ACTUAL ---
            html.Div(id="verify-section", style={"display": "none"}, children=[
                html.H6("Verificación de seguridad", className="mb-3"),
                dbc.Input(id="old-password", placeholder="Contraseña actual", type="password", className="mb-2"),
                dbc.Button("Verificar", id="verify-password-btn", color="primary", className="w-100 mb-2"),
                html.Div(id="verify-message", className="text-danger text-center mt-2"),
                html.A("⬅ Volver al inicio de sesión", id="back-to-login-1", href="#",
                       style={"color": "#FFD700", "fontSize": "0.9em"})
            ]),

            # --- ACTUALIZACIÓN DE CREDENCIALES ---
            html.Div(id="update-section", style={"display": "none"}, children=[
                html.H6("Actualizar Credenciales", className="mb-3"),
                dbc.Input(id="new-username", placeholder="Nuevo usuario", type="text", className="mb-2"),
                dbc.Input(id="new-password", placeholder="Nueva contraseña", type="password", className="mb-2"),
                dbc.Input(id="confirm-password", placeholder="Confirmar contraseña", type="password", className="mb-3"),
                dbc.Button("Actualizar", id="update-btn", color="success", className="w-100"),
                html.Div(id="update-message", className="text-success text-center mt-3"),
                html.A("⬅ Volver al inicio de sesión", id="back-to-login-2", href="#",
                       style={"color": "#FFD700", "fontSize": "0.9em"})
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Cerrar", id="login-cancel", color="secondary")
        ])
    ], id="modal-login", is_open=False, centered=True)


    return html.Div([
        dcc.Interval(id='interval-lingotes', interval=30*1000, n_intervals=0),
        dcc.Store(id='store-porcentajes-lingotes', data=percentages_data),
        html.Div(id="nav-sentinel"),

        html.Div([
            header,
            html.Hr(className="divider"),

            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H1("LINGOTES", className="lingotes-title"),
                    ], className="text-center")
                ], width=12)
            ]),

            dbc.Row([
                # PRIMER CARD — VENTA (resaltada)
                dbc.Col([
                    html.Div([
                        html.H3("VENTA", className="card-title"),
                        html.Div(id="valor-compra-lingotes", className="card-value"),
                        html.Div(id="porcentaje-compra-lingotes", className="card-percentage"),
                    ], id="card-venta", className="lingotes-card lingotes-card-venta")
                ], md=4),

                # SEGUNDO CARD — COMPRA (blanca translúcida)
                dbc.Col([
                    html.Div([
                        html.H3("COMPRA", className="card-title"),
                        html.Div(id="valor-venta-lingotes", className="card-value"),
                        html.Div(id="porcentaje-venta-lingotes", className="card-percentage"),
                    ], className="lingotes-card lingotes-card-blanca")
                ], md=4),

                # TERCER CARD — CONTRATACIÓN (blanca translúcida)
                dbc.Col([
                    html.Div([
                        html.H3("CONTRATACIÓN", className="card-title"),
                        html.Div(id="valor-venta-directa-lingotes", className="card-value"),
                        html.Div(id="porcentaje-venta-directa-lingotes", className="card-percentage"),
                    ], className="lingotes-card lingotes-card-blanca")
                ], md=4),
            ], className="mb-4"),

            html.Div([
                html.P(id="hora-actualizacion-lingotes", className="text-center text-muted mt-4"),
            ]),

            modal
        ], className="container-wide lingotes-container")
    ])


# ======================================================
# LAYOUT DASHBOARD
# ======================================================
def create_dashboard_layout():
    header = html.Div([
        dbc.Row([
            dbc.Col([crear_logo()], width=3),
            dbc.Col([html.Div(id='tirilla-content', className="tirilla-container")], width=9),
        ], className="header-container"),
        html.A("⬅", href="/", className="icon-btn", id="go-back-btn")
    ], style={"position": "relative"})
        # ======================================================
    # MODAL UNIFICADO: LOGIN + ACTUALIZAR USUARIO/CONTRASEÑA
    # ======================================================
    modal = dbc.Modal([
        dbc.ModalHeader("Acceso Administrativo"),
        dbc.ModalBody([
            # --- LOGIN NORMAL ---
            html.Div(id="login-section", children=[
                dbc.Input(id="login-username", placeholder="Usuario", type="text", className="mb-2"),
                dbc.Input(id="login-password", placeholder="Contraseña", type="password", className="mb-3"),
                html.Div(id="login-message", className="text-danger mb-2 text-center"),
                dbc.Button("Ingresar", id="login-submit", color="primary", className="w-100 mb-3"),
                html.Div([
                    html.A("🔄 Actualizar usuario o contraseña", id="show-update-form", href="#",
                           style={"color": "#FFD700", "textDecoration": "none", "fontSize": "0.9em"})
                ], className="text-center")
            ]),

            # --- VERIFICACIÓN DE CONTRASEÑA ACTUAL ---
            html.Div(id="verify-section", style={"display": "none"}, children=[
                html.H6("Verificación de seguridad", className="mb-3"),
                dbc.Input(id="old-password", placeholder="Contraseña actual", type="password", className="mb-2"),
                dbc.Button("Verificar", id="verify-password-btn", color="primary", className="w-100 mb-2"),
                html.Div(id="verify-message", className="text-danger text-center mt-2"),
                html.A("⬅ Volver al inicio de sesión", id="back-to-login-1", href="#",
                       style={"color": "#FFD700", "fontSize": "0.9em"})
            ]),

            # --- ACTUALIZACIÓN DE CREDENCIALES ---
            html.Div(id="update-section", style={"display": "none"}, children=[
                html.H6("Actualizar Credenciales", className="mb-3"),
                dbc.Input(id="new-username", placeholder="Nuevo usuario", type="text", className="mb-2"),
                dbc.Input(id="new-password", placeholder="Nueva contraseña", type="password", className="mb-2"),
                dbc.Input(id="confirm-password", placeholder="Confirmar contraseña", type="password", className="mb-3"),
                dbc.Button("Actualizar", id="update-btn", color="success", className="w-100"),
                html.Div(id="update-message", className="text-success text-center mt-3"),
                html.A("⬅ Volver al inicio de sesión", id="back-to-login-2", href="#",
                       style={"color": "#FFD700", "fontSize": "0.9em"})
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Cerrar", id="login-cancel", color="secondary")
        ])
    ], id="modal-login", is_open=False, centered=True)


    return html.Div([
        dcc.Interval(id='interval-precios-vivo', interval=15000, n_intervals=0),
        dcc.Interval(id='interval-dia-anterior', interval=21600000, n_intervals=0),

        dcc.Store(id='store-precios', data={}),
        dcc.Store(id='store-datos-anteriores', data={}),

        html.Div([
            header,
            html.Hr(className="divider"),

            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("PRECIOS DÍA ANTERIOR", className="block-title"),
                        html.Table([
                            html.Tr([html.Th("CONCEPTO"), html.Th("VALOR")]),
                            html.Tr([
    html.Td([
        "TRM (BanRep)",
        html.Button("✏️", id="editar-trm-btn", n_clicks=0,
                    style={
                        "marginLeft": "8px",
                        "border": "none",
                        "background": "transparent",
                        "cursor": "pointer",
                        "fontSize": "16px"
                    })
    ]),
    html.Td(id="trm-anterior")
]),

                            html.Tr([html.Td("ONZA (INV)"), html.Td(id="oro-anterior")]),
                            html.Tr([html.Td("PRECIO FULL"), html.Td(id="full-anterior")]),
                        ], className="price-table"),
                        html.Div(id="trm-editor", style={"display": "none", "marginTop": "10px"}, children=[
                        dcc.Input(id="input-trm-manual", type="number", placeholder="Ingrese TRM manual", 
                        style={"width": "60%", "marginRight": "8px"}),
                        html.Button("Guardar", id="guardar-trm-btn", n_clicks=0,
                        style={"backgroundColor": "#FFD700", "border": "none", 
                       "padding": "5px 10px", "fontWeight": "bold"})
]),

                        html.Div(id='hora-anterior', className="refresh-indicator")
                    ], className="price-block price-block-anterior")
                ], width=6),

                dbc.Col([
                    html.Div(id='bloque-vivo', className="price-block price-block-vivo")
                ], width=6),
            ]),

            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("CALCULADORA DE PRECIOS", className="section-title"),
                        dbc.Row([
                            # Primer bloque: VENTA
                            dbc.Col([
                                html.Div([
                                    html.Div("VENTA", className="calc-header"),
                                    dbc.Row([
                                        dbc.Col([
                                            dcc.Input(id='input-compra', value=f"{percentages_data['compra']:.1f}",
                                                      type='text', className='dash-input', placeholder='% venta')
                                        ], width=8),
                                        dbc.Col([
                                            html.Button("APLICAR", id='btn-compra', n_clicks=0, className='dash-button')
                                        ], width=4)
                                    ]),
                                    html.Div(id='label-compra', className="calc-label"),
                                    html.Div(id='resultado-compra', className="calc-result")
                                ], className="calc-item")
                            ], width=4),

                            # Segundo bloque: COMPRA
                            dbc.Col([
                                html.Div([
                                    html.Div("COMPRA", className="calc-header"),
                                    dbc.Row([
                                        dbc.Col([
                                            dcc.Input(id='input-venta', value=f"{percentages_data['venta']:.1f}",
                                                      type='text', className='dash-input', placeholder='% compra')
                                        ], width=8),
                                        dbc.Col([
                                            html.Button("APLICAR", id='btn-venta', n_clicks=0, className='dash-button')
                                        ], width=4)
                                    ]),
                                    html.Div(id='label-venta', className="calc-label"),
                                    html.Div(id='resultado-venta', className="calc-result")
                                ], className="calc-item")
                            ], width=4),

                            # Tercer bloque: CONTRATACIÓN
                            dbc.Col([
                                html.Div([
                                    html.Div("CONTRATACIÓN", className="calc-header"),
                                    dbc.Row([
                                        dbc.Col([
                                            dcc.Input(id='input-venta-directa', value=f"{percentages_data['venta_directa']:.1f}",
                                                      type='text', className='dash-input', placeholder='% contratación')
                                        ], width=8),
                                        dbc.Col([
                                            html.Button("APLICAR", id='btn-venta-directa', n_clicks=0, className='dash-button')
                                        ], width=4)
                                    ]),
                                    html.Div(id='label-venta-directa', className="calc-label"),
                                    html.Div(id='resultado-venta-directa', className="calc-result")
                                ], className="calc-item")
                            ], width=4),
                        ])
                    ], className="calculator-horizontal")
                ], width=12),
            ]),
        ], className="container-wide")
    ])


# ======================================================
# LAYOUT RAÍZ + NAVEGACIÓN
# ======================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/dashboard':
        if not usuario_autenticado["activo"]:
            print("⛔ Acceso denegado: usuario no autenticado.")
            return layout_lingotes()
        return create_dashboard_layout()
    return layout_lingotes()


# ======================================================
# CALLBACKS LINGOTES
# ======================================================
@app.callback(
    [Output('valor-compra-lingotes', 'children'),
     Output('porcentaje-compra-lingotes', 'children'),
     Output('valor-venta-lingotes', 'children'),
     Output('porcentaje-venta-lingotes', 'children'),
     Output('valor-venta-directa-lingotes', 'children'),
     Output('porcentaje-venta-directa-lingotes', 'children'),
     Output('hora-actualizacion-lingotes', 'children')],
    [Input('interval-lingotes', 'n_intervals')]
)
def actualizar_lingotes(n):
    """
    Calcula los valores de los tres cuadros en la vista LINGOTES
    usando la misma TRM (manual o automática) y el mismo oro del día anterior.
    """
    try:
        # 🟡 1. Cargar los porcentajes guardados
        data = persistence_manager.load_percentages()

        # 🟡 2. Obtener TRM (manual si existe)
        trm, _ = obtener_trm_banrep()

        # 🟡 3. Obtener el oro del día anterior
        oro_anterior = obtener_oro_dia_anterior()
        if isinstance(oro_anterior, tuple):
            oro_anterior = oro_anterior[0]  # En caso de que devuelva tupla

        # 🟡 4. Calcular el precio base unificado
        precio_base = (oro_anterior / 31.10347) * trm

        # 🟡 5. Calcular precios finales según porcentajes
        precio_venta = precio_base * (1 + data['compra'] / 100.0)  # VENTA (resaltada)
        precio_compra = precio_base * (1 + data['venta'] / 100.0)  # COMPRA
        precio_directa = precio_base * (1 + data['venta_directa'] / 100.0)  # CONTRATACIÓN

        # 🟡 6. Formatear resultados visuales
        valor_venta = f"${formato_colombiano(precio_venta)}"
        porcentaje_venta = f"+{data['compra']:.1f}%" if data['compra'] != 0.0 else "0.0%"

        valor_compra = f"${formato_colombiano(precio_compra)}"
        porcentaje_compra = f"+{data['venta']:.1f}%" if data['venta'] != 0.0 else "0.0%"

        valor_directa = f"${formato_colombiano(precio_directa)}"
        porcentaje_directa = f"+{data['venta_directa']:.1f}%" if data['venta_directa'] != 0.0 else "0.0%"

        hora_actualizacion = f"Actualizado: {datetime.now().strftime('%H:%M:%S')}"

        return (valor_venta, porcentaje_venta,
                valor_compra, porcentaje_compra,
                valor_directa, porcentaje_directa,
                hora_actualizacion)
    except Exception as e:
        print(f"❌ Error actualizando LINGOTES: {e}")
        return ("Error", "0.0%", "Error", "0.0%", "Error", "0.0%", f"Error: {e}")

# ======================================================
# LOGIN + CAMBIO DE CREDENCIALES (en el mismo modal)
# ======================================================
from werkzeug.security import generate_password_hash
# 🔍 Test de validación de hash
test_hash = "pbkdf2:sha256:600000$3C4mkOu2RNRVG28Z$a2b7f47a27a7b64e4f67c527bcb5b514183fd9d2e17d556e31da4f48e5678e40"
print("🧪 Prueba de hash local (contraseña 'admin'):", check_password_hash(test_hash, "admin"))


@app.callback(
    [
        Output("modal-login", "is_open"),
        Output("login-section", "style"),
        Output("verify-section", "style"),
        Output("update-section", "style"),
        Output("login-message", "children"),
        Output("verify-message", "children"),
        Output("update-message", "children"),
        Output("nav-sentinel", "children")
    ],
    [
        Input("open-login-modal", "n_clicks"),
        Input("login-cancel", "n_clicks"),
        Input("login-submit", "n_clicks"),
        Input("show-update-form", "n_clicks"),
        Input("verify-password-btn", "n_clicks"),
        Input("update-btn", "n_clicks"),
        Input("back-to-login-1", "n_clicks"),
        Input("back-to-login-2", "n_clicks")
    ],
    [
        State("modal-login", "is_open"),
        State("login-username", "value"),
        State("login-password", "value"),
        State("old-password", "value"),
        State("new-username", "value"),
        State("new-password", "value"),
        State("confirm-password", "value")
    ]
)
def manejar_modal_login(open_click, cancel_click, login_click, show_update_click,
                        verify_click, update_click, back1, back2,
                        is_open, username, password, old_pass, new_user, new_pass, confirm_pass):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, {"display": "block"}, {"display": "none"}, {"display": "none"}, "", "", "", ""

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    usuarios = cargar_usuarios()

    # --- Abrir modal ---
    if button_id == "open-login-modal":
        return True, {"display": "block"}, {"display": "none"}, {"display": "none"}, "", "", "", ""

    # --- Cerrar modal ---
    if button_id == "login-cancel":
        return False, {"display": "block"}, {"display": "none"}, {"display": "none"}, "", "", "", ""

    # --- LOGIN NORMAL ---
    if button_id == "login-submit":
        if not username or not password:
            return True, {"display": "block"}, {"display": "none"}, {"display": "none"}, "⚠️ Ingresa usuario y contraseña", "", "", ""
        if username not in usuarios:
            return True, {"display": "block"}, {"display": "none"}, {"display": "none"}, "⚠️ Usuario no registrado", "", "", ""
        stored_hash = usuarios[username].get("password", "")
        if check_password_hash(stored_hash, password):
            usuario_autenticado["activo"] = True
            usuario_autenticado["nombre"] = username
            return False, {"display": "block"}, {"display": "none"}, {"display": "none"}, "", "", "", dcc.Location(pathname="/dashboard", id="redir-login")
        else:
            return True, {"display": "block"}, {"display": "none"}, {"display": "none"}, "❌ Contraseña incorrecta", "", "", ""

    # --- Mostrar pantalla de verificación ---
    if button_id == "show-update-form":
        return True, {"display": "none"}, {"display": "block"}, {"display": "none"}, "", "", "", ""

    # --- Verificar contraseña actual ---
    if button_id == "verify-password-btn":
        if "admin" not in usuarios:
            return True, {"display": "none"}, {"display": "block"}, {"display": "none"}, "", "❌ No existe usuario admin", "", ""
        stored_hash = usuarios["admin"]["password"]
        if check_password_hash(stored_hash, old_pass or ""):
            return True, {"display": "none"}, {"display": "none"}, {"display": "block"}, "", "", "", ""
        else:
            return True, {"display": "none"}, {"display": "block"}, {"display": "none"}, "", "⚠️ Contraseña incorrecta", "", ""

    # --- Actualizar credenciales ---
    if button_id == "update-btn":
        if not new_user or not new_pass or not confirm_pass:
            return True, {"display": "none"}, {"display": "none"}, {"display": "block"}, "", "", "⚠️ Completa todos los campos", ""
        if new_pass != confirm_pass:
            return True, {"display": "none"}, {"display": "none"}, {"display": "block"}, "", "", "⚠️ Las contraseñas no coinciden", ""

        hashed = generate_password_hash(new_pass)
        usuarios = {
            new_user: {
                "password": hashed,
                "role": "superadmin",
                "email": f"{new_user}@oroexpress.com",
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, indent=2, ensure_ascii=False)
        return True, {"display": "none"}, {"display": "none"}, {"display": "block"}, "", "", "✅ Credenciales actualizadas. Reinicia e inicia sesión.", ""

    # --- Volver al login ---
    if button_id in ["back-to-login-1", "back-to-login-2"]:
        return True, {"display": "block"}, {"display": "none"}, {"display": "none"}, "", "", "", ""

    return is_open, {"display": "block"}, {"display": "none"}, {"display": "none"}, "", "", "", ""



# ======================================================
# CALLBACKS PRINCIPALES DEL DASHBOARD
# ======================================================
@app.callback(
    [Output('store-precios', 'data'),
     Output('tirilla-content', 'children'),
     Output('bloque-vivo', 'children'),
     Output('store-datos-anteriores', 'data')],
    [Input('interval-precios-vivo', 'n_intervals')]
)
def actualizar_datos(n_intervals):
    print(f"🔄 Actualizando... {datetime.now().strftime('%H:%M:%S')}")
    precios = calcular_precios_tiempo_real()
    hora_actualizacion = datetime.now().strftime("%H:%M:%S")

    try:
        trm, fecha_trm = obtener_trm_banrep()
        oro_anterior = obtener_oro_dia_anterior()
        fecha_oro = datetime.now().strftime("%Y-%m-%d")
        full_anterior = (oro_anterior / 31.10347) * trm

        datos_anteriores = {
            'trm': trm,
            'oro_usd': oro_anterior,
            'full_cop': full_anterior,
            'fecha_actualizacion': hora_actualizacion,
            'fecha_trm': fecha_trm,
            'fecha_oro': fecha_oro
        }
    except Exception as e:
        print(f"❌ Error datos anteriores: {e}")
        datos_anteriores = {
            'trm': 3950.0,
            'oro_usd': 1950.0,
            'full_cop': 245000.0,
            'fecha_actualizacion': hora_actualizacion,
            'fecha_trm': "Error",
            'fecha_oro': "Error"
        }

    tirilla = crear_tirilla_estilo_banco(precios)

    bloque_vivo = html.Div([
        html.H3("PRECIOS EN TIEMPO REAL", className="block-title"),
        html.Table([
            html.Tr([html.Th("CONCEPTO"), html.Th("VALOR")]),
            html.Tr([html.Td("DOLAR"), html.Td(f"${formato_colombiano(precios['dolar_compra'])} COP")]),
            html.Tr([html.Td("ONZA (KITCO)"), html.Td(f"${formato_colombiano(precios['oro_usd'])} USD")]),
            html.Tr([html.Td("PRECIO FULL"), html.Td(f"${formato_colombiano(precios['full_cop'])} COP")]),
        ], className="price-table"),
        html.Div(f"Actualizado: {precios['actualizado']}", className="refresh-indicator")
    ])

    return precios, tirilla, bloque_vivo, datos_anteriores

@app.callback(
    [Output('trm-anterior', 'children'),
     Output('oro-anterior', 'children'),
     Output('full-anterior', 'children'),
     Output('hora-anterior', 'children')],
    [Input('interval-dia-anterior', 'n_intervals')]
)
def actualizar_tabla_anterior(n):
    try:
        trm, fecha_trm = obtener_trm_banrep()
        oro_anterior = obtener_oro_dia_anterior()
        fecha_oro = datetime.now().strftime("%Y-%m-%d")
        full_anterior = (oro_anterior / 31.10347) * trm
        hora_actual = datetime.now().strftime("%H:%M:%S")

        trm_str = f"${formato_colombiano(trm)} COP"
        oro_str = f"${formato_colombiano(oro_anterior)} USD"
        full_str = f"${formato_colombiano(full_anterior)} COP"
        hora_str = f"Actualizado: {hora_actual}"
        return trm_str, oro_str, full_str, hora_str
    except Exception as e:
        print(f"❌ Error actualizando tabla del día anterior: {e}")
        return "Error", "Error", "Error", f"Error: {e}"


# ======================================================
# CÁLCULOS / PERSISTENCIA - DASHBOARD
# ======================================================
@app.callback(
    [Output('resultado-compra', 'children'),
     Output('label-compra', 'children'),
     Output('resultado-venta', 'children'),
     Output('label-venta', 'children'),
     Output('resultado-venta-directa', 'children'),
     Output('label-venta-directa', 'children'),
     Output('store-datos-anteriores', 'data', allow_duplicate=True)],  # 👈 añadimos este Output
    [Input('btn-compra', 'n_clicks'),
     Input('btn-venta', 'n_clicks'),
     Input('btn-venta-directa', 'n_clicks')],
    [State('input-compra', 'value'),
     State('input-venta', 'value'),
     State('input-venta-directa', 'value'),
     State('store-datos-anteriores', 'data')],
    prevent_initial_call=True
)
def calcular_precios(nc, nv, nd, pct_compra_str, pct_venta_str, pct_directa_str, datos_anteriores):
    """Calcula los precios y guarda los porcentajes en disco."""
    def parse_pct(s):
        try:
            return float(str(s).replace(",", ".")) if s not in (None, "") else 0.0
        except:
            return 0.0

    # Convertir entradas
    pct_compra = parse_pct(pct_compra_str)
    pct_venta = parse_pct(pct_venta_str)
    pct_directa = parse_pct(pct_directa_str)

    # Precio base
    if datos_anteriores and "full_cop" in datos_anteriores:
        precio_base = datos_anteriores["full_cop"]
    else:
        precio_base = (1950.0 / 31.10347) * 3950.0

    # Calcular precios ajustados
    precio_compra = precio_base * (1 + pct_compra / 100.0)
    precio_venta = precio_base * (1 + pct_venta / 100.0)
    precio_directa = precio_base * (1 + pct_directa / 100.0)

    # 💾 Guardar en JSON (persistencia real)
    persistence_manager.save_percentages(pct_compra, pct_venta, pct_directa)

    # 🔄 Actualizar store para reflejar cambios en la interfaz
    datos_anteriores = datos_anteriores or {}
    datos_anteriores.update({
        "compra": pct_compra,
        "venta": pct_venta,
        "venta_directa": pct_directa
    })

    # Formato visual
    res_compra = f"${formato_colombiano(precio_compra)}"
    lbl_compra = f"VENTA (+{pct_compra:.1f}%)" if pct_compra != 0.0 else "VENTA"

    res_venta = f"${formato_colombiano(precio_venta)}"
    lbl_venta = f"COMPRA (+{pct_venta:.1f}%)" if pct_venta != 0.0 else "COMPRA"

    res_directa = f"${formato_colombiano(precio_directa)}"
    lbl_directa = f"CONTRATACIÓN (+{pct_directa:.1f}%)" if pct_directa != 0.0 else "CONTRATACIÓN"

    return (
        res_compra, lbl_compra,
        res_venta, lbl_venta,
        res_directa, lbl_directa,
        datos_anteriores
    )


    # OJO: Los labels visibles cambian de nombre
    res_compra = f"${formato_colombiano(precio_compra)}"
    lbl_compra = f"VENTA (+{pct_compra:.1f}%)" if pct_compra != 0.0 else "VENTA"

    res_venta = f"${formato_colombiano(precio_venta)}"
    lbl_venta = f"COMPRA (+{pct_venta:.1f}%)" if pct_venta != 0.0 else "COMPRA"

    res_dir = f"${formato_colombiano(precio_venta_directa)}"
    lbl_dir = f"CONTRATACIÓN (+{pct_directa:.1f}%)" if pct_directa != 0.0 else "CONTRATACIÓN"

    return res_compra, lbl_compra, res_venta, lbl_venta, res_dir, lbl_dir

@app.callback(
    [Output('input-compra', 'value'),
     Output('input-venta', 'value'),
     Output('input-venta-directa', 'value')],
    [Input('store-datos-anteriores', 'data')],
    prevent_initial_call=False
)
def sincronizar_inputs_con_json(datos_anteriores):
    """Recarga los valores guardados en JSON al iniciar el dashboard."""
    try:
        data = persistence_manager.load_percentages()
        return (
            f"{data['compra']:.1f}",
            f"{data['venta']:.1f}",
            f"{data['venta_directa']:.1f}"
        )
    except Exception as e:
        print(f"❌ Error sincronizando inputs: {e}")
        return "0.0", "0.0", "0.0"


@app.callback(
    [Output('resultado-compra', 'children', allow_duplicate=True),
     Output('label-compra', 'children', allow_duplicate=True),
     Output('resultado-venta', 'children', allow_duplicate=True),
     Output('label-venta', 'children', allow_duplicate=True),
     Output('resultado-venta-directa', 'children', allow_duplicate=True),
     Output('label-venta-directa', 'children', allow_duplicate=True)],
    [Input('input-compra', 'value'),
     Input('input-venta', 'value'),
     Input('input-venta-directa', 'value'),
     Input('store-datos-anteriores', 'data')],
    [State('store-datos-anteriores', 'data')],
    prevent_initial_call=True
)
def calcular_automatico(compra_str, venta_str, directa_str, _trigger, datos_anteriores):
    def parse_pct(s):
        try:
            return float(str(s).replace(",", ".")) if s not in (None, "") else 0.0
        except:
            return 0.0
    pct_compra, pct_venta, pct_directa = parse_pct(compra_str), parse_pct(venta_str), parse_pct(directa_str)

    if datos_anteriores and "full_cop" in datos_anteriores:
        precio_base = datos_anteriores["full_cop"]
    else:
        precio_base = (1950.0 / 31.10347) * 3950.0

    precio_compra = precio_base * (1 + pct_compra / 100.0)
    precio_venta = precio_base * (1 + pct_venta / 100.0)
    precio_venta_directa = precio_base * (1 + pct_directa / 100.0)

    res_compra = f"${formato_colombiano(precio_compra)}"
    lbl_compra = f"VENTA (+{pct_compra:.1f}%)" if pct_compra != 0.0 else "VENTA"

    res_venta = f"${formato_colombiano(precio_venta)}"
    lbl_venta = f"COMPRA (+{pct_venta:.1f}%)" if pct_venta != 0.0 else "COMPRA"

    res_dir = f"${formato_colombiano(precio_venta_directa)}"
    lbl_dir = f"CONTRATACIÓN (+{pct_directa:.1f}%)" if pct_directa != 0.0 else "CONTRATACIÓN"

    if any([pct_compra, pct_venta, pct_directa]):
        persistence_manager.save_percentages(pct_compra, pct_venta, pct_directa)

    return res_compra, lbl_compra, res_venta, lbl_venta, res_dir, lbl_dir

@app.callback(
    Output("trm-editor", "style"),
    [Input("editar-trm-btn", "n_clicks")],
    prevent_initial_call=True
)
def mostrar_editor_trm(n):
    if n and n > 0:
        return {"display": "block", "marginTop": "10px"}
    return {"display": "none"}

@app.callback(
    Output("trm-anterior", "children", allow_duplicate=True),
    Output("hora-anterior", "children", allow_duplicate=True),
    Output("trm-editor", "style", allow_duplicate=True),
    Input("guardar-trm-btn", "n_clicks"),
    State("input-trm-manual", "value"),
    prevent_initial_call=True
)
def guardar_trm_manual(n_clicks, trm_valor):
    """
    Guarda la TRM manual en un archivo local y actualiza la vista.
    Además, oculta el recuadro del editor después de guardar.
    """
    if n_clicks and trm_valor:
        try:
            # 📝 Guardar valor manual en archivo
            Path("storage").mkdir(exist_ok=True)
            with open("storage/trm_manual.json", "w", encoding="utf-8") as f:
                json.dump({
                    "trm": trm_valor,
                    "fecha": datetime.now().strftime("%Y-%m-%d")
                }, f, indent=2, ensure_ascii=False)

            print(f"📝 TRM manual guardada: ${trm_valor:,.0f}")
            hora_actual = datetime.now().strftime("%H:%M:%S")

            # ✅ Devuelve el nuevo valor, la hora, y oculta el cuadro
            return (
                f"${formato_colombiano(trm_valor)} COP",
                f"Actualizado manualmente: {hora_actual}",
                {"display": "none"}  # 👈 Esto oculta el input
            )
        except Exception as e:
            print(f"❌ Error guardando TRM manual: {e}")

    # Si no hay valor o falla, no actualiza nada
    return dash.no_update, dash.no_update, dash.no_update

# ======================================================
# MAIN
# ======================================================
if __name__ == '__main__':
    
    print("\n" + "="*60)
    print("🚀 OROEXPRESS - SISTEMA UNIFICADO")
    print("="*60)
    print("📊 VISTAS DISPONIBLES:")
    print("   🌐 LINGOTES:  http://localhost:8050/")
    print("   📈 DASHBOARD: http://localhost:8050/dashboard")
    print("\n📁 CARACTERÍSTICAS:")
    print("   ✅ Estética unificada (fondos, header, logo)")
    print("   ✅ Engranaje (login) en LINGOTES → redirige al dashboard si ok")
    print("   ✅ Flecha '←' en Dashboard (arriba derecha) para volver a LINGOTES")
    print("   ✅ Persistencia REAL en disco (JSON)")
    print("   ✅ Cálculos y sincronización automática")
    print(f"📁 Archivo JSON: {persistence_manager.percentages_file}")
    print("="*60)
    app.run(host='0.0.0.0', debug=False, port=8050)
