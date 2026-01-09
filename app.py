# SISTEMA OROEXPRESS UNIFICADO - DASHBOARD INTEGRAL
from dash import Dash, html, dcc, Input, Output, State
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import requests, re, os
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import base64
from pathlib import Path
import json

print("🚀 INICIANDO SISTEMA OROEXPRESS UNIFICADO...")

# 🥇 Sustituimos InvestPy (que fallaba) por nuestro módulo nuevo
from data.kitco_gold import get_gold_previous_day as obtener_oro_dia_anterior

# CONFIGURACIÓN INICIAL
from pathlib import Path

# 📁 Ruta base dinámica (carpeta donde está app.py)
BASE_DIR = Path(__file__).resolve().parent

# AUTENTICACIÓN DE USUARIOS
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

# INICIALIZAR APP (evita error de IDs fuera del layout activo)
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "OroExpress - Lingotes"
server = app.server

# PERSISTENCIA EN DISCO (JSON)
class PersistenceManager:
    def __init__(self):
        self.data_dir = Path("storage")
        self.data_dir.mkdir(exist_ok=True)
        self.percentages_file = self.data_dir / "calculator_percentages.json"
        print(f"📁 Persistencia en disco: {self.data_dir.absolute()}")

    def save_percentages(self, compra, venta, venta_directa,
                         venta_1gr=0.0, venta_5gr=0.0, venta_10gr=0.0,
                         venta_20gr=0.0, venta_1oz=0.0, venta_100gr=0.0, venta_200gr=0.0):
        """Guarda todos los porcentajes, incluidos los nuevos 7 de venta."""
        try:
            data = {
                'compra': compra,
                'venta': venta,
                'venta_directa': venta_directa,
                'venta_1gr': venta_1gr,
                'venta_5gr': venta_5gr,
                'venta_10gr': venta_10gr,
                'venta_20gr': venta_20gr,
                'venta_1oz': venta_1oz,
                'venta_100gr': venta_100gr,
                'venta_200gr': venta_200gr,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.percentages_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("💾 Guardado de porcentajes extendido correctamente.")
            return True
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            return False
    
    def load_percentages(self):
        """Carga TODOS los porcentajes guardados en el JSON, y agrega los faltantes si no existen."""
        try:
            if self.percentages_file.exists():
                with open(self.percentages_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Lista completa de campos obligatorios
                campos = [
                    'compra', 'venta', 'venta_directa',
                    'venta_1gr', 'venta_5gr', 'venta_10gr', 'venta_20gr',
                    'venta_1oz', 'venta_100gr', 'venta_200gr'
                ]

                # Agregar faltantes
                for campo in campos:
                    data.setdefault(campo, 0.0)

                return data

            # Si NO existe archivo, crearlo con valores iniciales
            else:
                print("📂 Creando archivo con valores por defecto")
                self.save_percentages(0, 0, 0)
                return self.get_default()

        except Exception as e:
            print(f"❌ Error cargando porcentajes: {e}")
            return self.get_default()
            
    def get_default(self):
        """Valores iniciales en caso de no existir el archivo."""
        return {
            'compra': 0.0,
            'venta': 0.0,
            'venta_directa': 0.0,
            'venta_1gr': 0.0,
            'venta_5gr': 0.0,
            'venta_10gr': 0.0,
            'venta_20gr': 0.0,
            'venta_1oz': 0.0,
            'venta_100gr': 0.0,
            'venta_200gr': 0.0,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

persistence_manager = PersistenceManager()
percentages_data = persistence_manager.load_percentages()

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
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

# EXTRACCIÓN DE DATOS (fuentes externas)
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
    TRM VIGENTE (OFICIAL – datos.gov.co).
    Regla:
    - Toma la TRM más reciente por 'vigenciadesde' (DESC).
    - En fines de semana/festivos, la vigente suele ser la última publicada.
    """
    try:
        url = (
            "https://www.datos.gov.co/resource/32sa-8pi3.json"
            "?$limit=1&$order=vigenciadesde DESC"
        )

        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data:
            return 3950.0, "Sin datos"

        item = data[0]
        trm = float(item["valor"])
        fecha = item.get("vigenciadesde", "")[:10]

        print(f"📌 TRM vigente ({fecha}): {trm}")
        return trm, fecha

    except Exception as e:
        print(f"❌ Error TRM datos.gov.co: {e}")
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

# COMPONENTES / WIDGETS
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

# LAYOUT LINGOTES
def layout_lingotes():
    # Cargar SIEMPRE los porcentajes actuales desde el JSON
    percentages_data = persistence_manager.load_percentages()

    # ======================
    # HEADER
    # ======================
    header = html.Div([
        dbc.Row([
            dbc.Col([crear_logo()], width=3),
            dbc.Col([], width=9)
        ], className="header-container"),
        html.Button("👤", id="open-login-modal", className="icon-btn", n_clicks=0)
    ], style={"position": "relative"})

    # ======================
    # MODAL LOGIN
    # ======================
    modal = dbc.Modal([
        dbc.ModalHeader("Acceso Administrativo"),
        dbc.ModalBody([

            # --- LOGIN ---
            html.Div(id="login-section", children=[
                dbc.Input(
                    id="login-username",
                    placeholder="Usuario",
                    type="text",
                    className="mb-2"
                ),
                dbc.Input(
                    id="login-password",
                    placeholder="Contraseña",
                    type="password",
                    className="mb-3"
                ),
                html.Div(
                    id="login-message",
                    className="text-danger mb-2 text-center"
                ),
                dbc.Button(
                    "Ingresar",
                    id="login-submit",
                    color="primary",
                    className="w-100 mb-3"
                ),
                html.Div([
                    html.A(
                        "🔄 Actualizar usuario o contraseña",
                        id="show-update-form",
                        href="#",
                        style={
                            "color": "#FFD700",
                            "textDecoration": "none",
                            "fontSize": "0.9em"
                        }
                    )
                ], className="text-center")
            ]),

            # --- VERIFICAR CONTRASEÑA ACTUAL ---
            html.Div(
                id="verify-section",
                style={"display": "none"},
                children=[
                    html.H6("Verificación de seguridad", className="mb-3"),
                    dbc.Input(
                        id="old-password",
                        placeholder="Contraseña actual",
                        type="password",
                        className="mb-2"
                    ),
                    dbc.Button(
                        "Verificar",
                        id="verify-password-btn",
                        color="primary",
                        className="w-100 mb-2"
                    ),
                    html.Div(
                        id="verify-message",
                        className="text-danger text-center mt-2"
                    ),
                    html.A(
                        "⬅ Volver al inicio de sesión",
                        id="back-to-login-1",
                        href="#",
                        style={"color": "#FFD700", "fontSize": "0.9em"}
                    )
                ]
            ),

            # --- ACTUALIZAR CREDENCIALES ---
            html.Div(
                id="update-section",
                style={"display": "none"},
                children=[
                    html.H6("Actualizar Credenciales", className="mb-3"),
                    dbc.Input(
                        id="new-username",
                        placeholder="Nuevo usuario",
                        type="text",
                        className="mb-2"
                    ),
                    dbc.Input(
                        id="new-password",
                        placeholder="Nueva contraseña",
                        type="password",
                        className="mb-2"
                    ),
                    dbc.Input(
                        id="confirm-password",
                        placeholder="Confirmar contraseña",
                        type="password",
                        className="mb-3"
                    ),
                    dbc.Button(
                        "Actualizar",
                        id="update-btn",
                        color="success",
                        className="w-100"
                    ),
                    html.Div(
                        id="update-message",
                        className="text-success text-center mt-3"
                    ),
                    html.A(
                        "⬅ Volver al inicio de sesión",
                        id="back-to-login-2",
                        href="#",
                        style={"color": "#FFD700", "fontSize": "0.9em"}
                    )
                ]
            )
        ]),
        dbc.ModalFooter([
            dbc.Button(
                "Cerrar",
                id="login-cancel",
                color="secondary"
            )
        ])
    ], id="modal-login", is_open=False, centered=True)

    # ======================
    # RETURN FINAL
    # ======================
    return html.Div([

        # 🔥 OVERLAY DE TRANSICIÓN LOGIN → DASHBOARD
        html.Div(
            id="login-overlay",
            className="login-overlay",
            children=html.Div(className="login-spinner")
        ),

        # Estado / timers
        dcc.Interval(
            id='interval-lingotes',
            interval=30 * 1000,
            n_intervals=0
        ),
        dcc.Store(
            id='store-porcentajes-lingotes',
            data=percentages_data
        ),
        html.Div(id="nav-sentinel"),

        # CONTENIDO PRINCIPAL
        html.Div([
            header,
            html.Hr(className="divider"),

            dbc.Row([
                dbc.Col([
                    html.H1(
                        "LINGOTES",
                        className="lingotes-title"
                    )
                ], width=12)
            ]),

            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("VENTA", className="card-title"),
                        html.Div(
                            id="valor-compra-lingotes",
                            className="card-value"
                        ),
                        html.Div(
                            id="porcentaje-compra-lingotes",
                            className="card-percentage"
                        ),
                    ], id="card-venta",
                       className="lingotes-card lingotes-card-venta")
                ], md=4),

                dbc.Col([
                    html.Div([
                        html.H3("COMPRA", className="card-title"),
                        html.Div(
                            id="valor-venta-lingotes",
                            className="card-value"
                        ),
                        html.Div(
                            id="porcentaje-venta-lingotes",
                            className="card-percentage"
                        ),
                    ], className="lingotes-card lingotes-card-blanca")
                ], md=4),

                dbc.Col([
                    html.Div([
                        html.H3("CONTRATACIÓN", className="card-title"),
                        html.Div(
                            id="valor-venta-directa-lingotes",
                            className="card-value"
                        ),
                        html.Div(
                            id="porcentaje-venta-directa-lingotes",
                            className="card-percentage"
                        ),
                    ], className="lingotes-card lingotes-card-blanca")
                ], md=4),
            ], className="mb-4"),

            html.P(
                id="hora-actualizacion-lingotes",
                className="text-center text-muted mt-4"
            ),

            modal

        ], className="container-wide lingotes-container")

    ])

# LAYOUT DASHBOARD
def create_dashboard_layout():
    # 👉 Cargar SIEMPRE los porcentajes actualizados del JSON
    percentages_data = persistence_manager.load_percentages()

    header = html.Div([
        dbc.Row([
            dbc.Col([crear_logo()], width=3),
            dbc.Col([html.Div(id='tirilla-content', className="tirilla-container")], width=9),
        ], className="header-container"),
        html.A("⬅", href="/", className="icon-btn", id="go-back-btn")
    ], style={"position": "relative"})

    # MODAL UNIFICADO: LOGIN + ACTUALIZAR USUARIO/CONTRASEÑA
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

            # BLOQUE DE PRECIOS
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("PRECIOS DÍA ANTERIOR", className="block-title"),
                        html.Table([
                            html.Tr([html.Th("CONCEPTO"), html.Th("VALOR")]),
                            html.Tr([
                                html.Td([
                                    "TRM",
                                ]),
                                html.Td(id="trm-anterior")
                            ]),
                            html.Tr([html.Td("ONZA"), html.Td(id="oro-anterior")]),
                            html.Tr([html.Td("PRECIO FULL"), html.Td(id="full-anterior")]),
                        ], className="price-table"),

                        html.Div(id="trm-editor", style={"display": "none", "marginTop": "10px"}, children=[
                            dcc.Input(
                                id="input-trm-manual",
                                type="number",
                                placeholder="Ingrese TRM manual",
                                style={"width": "60%", "marginRight": "8px"}
                            ),
                            html.Button(
                                "Guardar",
                                id="guardar-trm-btn",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "#FFD700",
                                    "border": "none",
                                    "padding": "5px 10px",
                                    "fontWeight": "bold"
                                }
                            )
                        ]),
                        html.Div(id='hora-anterior', className="refresh-indicator")
                    ], className="price-block price-block-anterior")
                ], width=6),

                dbc.Col([
                    html.Div(id='bloque-vivo', className="price-block price-block-vivo")
                ], width=6),
            ]),

          
            # BLOQUE DE VENTAS DETALLADAS + COMPRA + CONTRATACIÓN
            dbc.Row([
                # Columna izquierda: Ventas detalladas
                dbc.Col([
                    html.Div([
                        html.Div("VENTAS DETALLADAS", className="calc-header",
                                 style={"color": "#FFD700", "fontSize": "1.1em"}),

                        dbc.Row([
                            dbc.Col([
                                html.Div("1 Gr", className="calc-label"),
                                dcc.Input(id="input-venta-1gr",
                                          value=f"{percentages_data.get('venta_1gr',0.0):.1f}",
                                          type="text", className="dash-input",
                                          placeholder="% 1 GR"),
                                html.Button("APLICAR", id="btn-venta-1gr", n_clicks=0,
                                            className="dash-button"),
                                html.Div(id="resultado-venta-1gr", className="calc-result")
                            ], width=3),

                            dbc.Col([
                                html.Div("5 GR", className="calc-label"),
                                dcc.Input(id="input-venta-5gr",
                                          value=f"{percentages_data.get('venta_5gr',0.0):.1f}",
                                          type="text", className="dash-input",
                                          placeholder="% 5 GR"),
                                html.Button("APLICAR", id="btn-venta-5gr", n_clicks=0,
                                            className="dash-button"),
                                html.Div(id="resultado-venta-5gr", className="calc-result")
                            ], width=3),

                            dbc.Col([
                                html.Div("10 GR", className="calc-label"),
                                dcc.Input(id="input-venta-10gr",
                                          value=f"{percentages_data.get('venta_10gr',0.0):.1f}",
                                          type="text", className="dash-input",
                                          placeholder="% 10 GR"),
                                html.Button("APLICAR", id="btn-venta-10gr", n_clicks=0,
                                            className="dash-button"),
                                html.Div(id="resultado-venta-10gr", className="calc-result")
                            ], width=3),

                            dbc.Col([
                                html.Div("20 GR", className="calc-label"),
                                dcc.Input(id="input-venta-20gr",
                                          value=f"{percentages_data.get('venta_20gr',0.0):.1f}",
                                          type="text", className="dash-input",
                                          placeholder="% 20 GR"),
                                html.Button("APLICAR", id="btn-venta-20gr", n_clicks=0,
                                            className="dash-button"),
                                html.Div(id="resultado-venta-20gr", className="calc-result")
                            ], width=3),
                        ]),

                        dbc.Row([
                            dbc.Col([
                                html.Div("1 OZ", className="calc-label"),
                                dcc.Input(id="input-venta-1oz",
                                          value=f"{percentages_data.get('venta_1oz',0.0):.1f}",
                                          type="text", className="dash-input",
                                          placeholder="% 1 OZ"),
                                html.Button("APLICAR", id="btn-venta-1oz", n_clicks=0,
                                            className="dash-button"),
                                html.Div(id="resultado-venta-1oz", className="calc-result")
                            ], width=4),

                            dbc.Col([
                                html.Div("100 GR", className="calc-label"),
                                dcc.Input(id="input-venta-100gr",
                                          value=f"{percentages_data.get('venta_100gr',0.0):.1f}",
                                          type="text", className="dash-input",
                                          placeholder="% 100 GR"),
                                html.Button("APLICAR", id="btn-venta-100gr", n_clicks=0,
                                            className="dash-button"),
                                html.Div(id="resultado-venta-100gr", className="calc-result")
                            ], width=4),

                            dbc.Col([
                                html.Div("200 GR", className="calc-label"),
                                dcc.Input(id="input-venta-200gr",
                                          value=f"{percentages_data.get('venta_200gr',0.0):.1f}",
                                          type="text", className="dash-input",
                                          placeholder="% 200 GR"),
                                html.Button("APLICAR", id="btn-venta-200gr", n_clicks=0,
                                            className="dash-button"),
                                html.Div(id="resultado-venta-200gr", className="calc-result")
                            ], width=4),
                        ])
                    ], className="calc-item")
                ], width=6),

                # Columna derecha: Compra + Contratación
                dbc.Col([
                    html.Div([
                        html.Div("COMPRA", className="calc-header"),
                        dbc.Row([
                            dbc.Col([
                                dcc.Input(id='input-venta',
                                          value=f"{percentages_data['venta']:.1f}",
                                          type='text', className='dash-input',
                                          placeholder='% compra')
                            ], width=8),
                            dbc.Col([
                                html.Button("APLICAR", id='btn-venta',
                                            n_clicks=0, className='dash-button')
                            ], width=4)
                        ]),
                        html.Div(id='label-venta', className="calc-label"),
                        html.Div(id='resultado-venta', className="calc-result"),

                        html.Hr(style={"margin": "25px 0"}),

                        html.Div("CONTRATACIÓN", className="calc-header"),
                        dbc.Row([
                            dbc.Col([
                                dcc.Input(id='input-venta-directa',
                                          value=f"{percentages_data['venta_directa']:.1f}",
                                          type='text', className='dash-input',
                                          placeholder='% contratación')
                            ], width=8),
                            dbc.Col([
                                html.Button("APLICAR", id='btn-venta-directa',
                                            n_clicks=0, className='dash-button')
                            ], width=4)
                        ]),
                        html.Div(id='label-venta-directa', className="calc-label"),
                        html.Div(id='resultado-venta-directa', className="calc-result")
                    ], className="calc-item")
                ], width=5)
            ])
        ], className="container-wide")
    ])

# LAYOUT RAÍZ + NAVEGACIÓN
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

# CALLBACKS LINGOTES
@app.callback(
    [
        Output('valor-compra-lingotes', 'children'),        # aquí irá la lista 1gr, 5gr, ...
        Output('porcentaje-compra-lingotes', 'children'),   # lo dejamos vacío
        Output('valor-venta-lingotes', 'children'),         # COMPRA (precio único)
        Output('porcentaje-venta-lingotes', 'children'),
        Output('valor-venta-directa-lingotes', 'children'), # CONTRATACIÓN (precio único)
        Output('porcentaje-venta-directa-lingotes', 'children'),
        Output('hora-actualizacion-lingotes', 'children'),
    ],
    [Input('interval-lingotes', 'n_intervals')]
)
def actualizar_lingotes(n):
    """
    LINGOTES:
    - VENTA (tarjeta resaltada): muestra 1gr, 5gr, 10gr, 20gr, 1oz, 100gr, 200gr
      usando los porcentajes venta_1gr, venta_5gr, etc.
    - COMPRA: un solo precio usando porcentaje 'venta'
    - CONTRATACIÓN: un solo precio usando porcentaje 'venta_directa'
    """
    try:
        # 🟡 1. Cargar TODOS los porcentajes guardados
        data = persistence_manager.load_percentages()

        # 🟡 2. Obtener TRM (manual si existe)
        trm, _ = obtener_trm_banrep()

        # 🟡 3. Obtener el oro del día anterior
        oro_anterior = obtener_oro_dia_anterior()
        if isinstance(oro_anterior, tuple):
            oro_anterior = oro_anterior[0]

        # 🟡 4. Precio base por gramo (FULL del día anterior)
        precio_base_gr = (oro_anterior / 31.10347) * trm

        # =============== VENTA DETALLADA (tarjeta que brilla) ===============
        factores = {
            "1gr": 1,
            "5gr": 5,
            "10gr": 10,
            "20gr": 20,
            "1oz": 31.10347,
            "100gr": 100,
            "200gr": 200,
        }

        venta_1gr   = precio_base_gr * factores["1gr"]   * (1 + data["venta_1gr"]   / 100.0)
        venta_5gr   = precio_base_gr * factores["5gr"]   * (1 + data["venta_5gr"]   / 100.0)
        venta_10gr  = precio_base_gr * factores["10gr"]  * (1 + data["venta_10gr"]  / 100.0)
        venta_20gr  = precio_base_gr * factores["20gr"]  * (1 + data["venta_20gr"]  / 100.0)
        venta_1oz   = precio_base_gr * factores["1oz"]   * (1 + data["venta_1oz"]   / 100.0)
        venta_100gr = precio_base_gr * factores["100gr"] * (1 + data["venta_100gr"] / 100.0)
        venta_200gr = precio_base_gr * factores["200gr"] * (1 + data["venta_200gr"] / 100.0)

        # Construimos el contenido de la tarjeta VENTA como una pequeña lista/tabla
        bloque_venta_detallada = html.Div(
    [
        html.Div([
            html.Span("  1    Gr", className="venta-label"),
            html.Span(f"${formato_colombiano(venta_1gr)}", className="venta-valor"),
        ], className="venta-row"),

        html.Div([
            html.Span("  5    Gr", className="venta-label"),
            html.Span(f"${formato_colombiano(venta_5gr)}", className="venta-valor"),
        ], className="venta-row"),

        html.Div([
            html.Span(" 10   Gr", className="venta-label"),
            html.Span(f"${formato_colombiano(venta_10gr)}", className="venta-valor"),
        ], className="venta-row"),

        html.Div([
            html.Span(" 20   Gr", className="venta-label"),
            html.Span(f"${formato_colombiano(venta_20gr)}", className="venta-valor"),
        ], className="venta-row"),

        html.Div([
            html.Span("  1    Oz", className="venta-label"),
            html.Span(f"${formato_colombiano(venta_1oz)}", className="venta-valor"),
        ], className="venta-row"),

        html.Div([
            html.Span("100 Gr", className="venta-label"),
            html.Span(f"${formato_colombiano(venta_100gr)}", className="venta-valor"),
        ], className="venta-row"),

        html.Div([
            html.Span("200 Gr", className="venta-label"),
            html.Span(f"${formato_colombiano(venta_200gr)}", className="venta-valor"),
        ], className="venta-row"),
    ],
    className="venta-detallada-container",
)
        # No queremos texto tipo "Aplicando 0.0%" aquí
        texto_porcentaje_venta_card = ""

        # =============== COMPRA (precio único) ===============
        precio_compra = precio_base_gr * (1 + data["venta"] / 100.0)
        valor_compra = f"${formato_colombiano(precio_compra)}"
        porcentaje_compra = f"+{data['venta']:.1f}%" if data["venta"] != 0.0 else ""

        # =============== CONTRATACIÓN (precio único) ===============
        precio_directa = precio_base_gr * (1 + data["venta_directa"] / 100.0)
        valor_directa = f"${formato_colombiano(precio_directa)}"
        porcentaje_directa = f"+{data['venta_directa']:.1f}%" if data["venta_directa"] != 0.0 else ""

        # =============== Hora de actualización ===============
        hora_actualizacion = f"Actualizado: {datetime.now().strftime('%H:%M:%S')}"

        return (
            bloque_venta_detallada,          # contenido tarjeta VENTA
            texto_porcentaje_venta_card,     # vacío
            valor_compra, porcentaje_compra, # COMPRA
            valor_directa, porcentaje_directa,  # CONTRATACIÓN
            hora_actualizacion,
        )

    except Exception as e:
        print(f"❌ Error actualizando LINGOTES: {e}")
        return (
            "Error", "", "Error", "", "Error", "", f"Error: {e}"
        )


# LOGIN + CAMBIO DE CREDENCIALES (en el mismo modal)
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
        Output("nav-sentinel", "children"),
        Output("url", "pathname"),
    ],
    [
        Input("open-login-modal", "n_clicks"),
        Input("login-cancel", "n_clicks"),
        Input("login-submit", "n_clicks"),
        Input("show-update-form", "n_clicks"),
        Input("verify-password-btn", "n_clicks"),
        Input("update-btn", "n_clicks"),
        Input("back-to-login-1", "n_clicks"),
        Input("back-to-login-2", "n_clicks"),
    ],
    [
        State("modal-login", "is_open"),
        State("login-username", "value"),
        State("login-password", "value"),
        State("old-password", "value"),
        State("new-username", "value"),
        State("new-password", "value"),
        State("confirm-password", "value"),
        State("url", "pathname"),
    ],
    prevent_initial_call=False
)
def manejar_modal_login(open_click, cancel_click, login_click, show_update_click,
                        verify_click, update_click, back1, back2,
                        is_open, username, password, old_pass, new_user, new_pass, confirm_pass,
                        current_path):

    trigger = dash.callback_context.triggered_id
    usuarios = cargar_usuarios()

    SHOW = {"display": "block"}
    HIDE = {"display": "none"}
    url_out = dash.no_update

    # --- ABRIR MODAL (emoji 👤) ---
    # Evita que se abra al refrescar (n_clicks pasa de None->0 y dispara el callback)
    if trigger == "open-login-modal":
        if open_click and open_click > 0:
            return True, SHOW, HIDE, HIDE, "", "", "", "", url_out
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # --- CERRAR MODAL ---
    if trigger == "login-cancel":
        return False, SHOW, HIDE, HIDE, "", "", "", "", url_out

    # --- LOGIN ---
    if trigger == "login-submit":
        if not username or not password:
            return True, SHOW, HIDE, HIDE, "⚠️ Ingresa usuario y contraseña", "", "", "", url_out

        if username not in usuarios:
            return True, SHOW, HIDE, HIDE, "⚠️ Usuario no registrado", "", "", "", url_out

        stored_hash = usuarios[username].get("password", "")
        if check_password_hash(stored_hash, password):
            usuario_autenticado["activo"] = True
            usuario_autenticado["nombre"] = username
            return False, SHOW, HIDE, HIDE, "", "", "", "", "/dashboard"
        else:
            return True, SHOW, HIDE, HIDE, "❌ Contraseña incorrecta", "", "", "", url_out

    # --- IR A VERIFICACIÓN (para actualizar credenciales) ---
    if trigger == "show-update-form":
        return True, HIDE, SHOW, HIDE, "", "", "", "", url_out

    # --- VERIFICAR CONTRASEÑA ACTUAL ---
    if trigger == "verify-password-btn":
        if "admin" not in usuarios:
            return True, HIDE, SHOW, HIDE, "", "❌ No existe usuario admin", "", "", url_out

        stored_hash = usuarios["admin"]["password"]
        if check_password_hash(stored_hash, old_pass or ""):
            return True, HIDE, HIDE, SHOW, "", "", "", "", url_out
        else:
            return True, HIDE, SHOW, HIDE, "", "⚠️ Contraseña incorrecta", "", "", url_out

    # --- ACTUALIZAR CREDENCIALES ---
    if trigger == "update-btn":
        if not new_user or not new_pass or not confirm_pass:
            return True, HIDE, HIDE, SHOW, "", "", "⚠️ Completa todos los campos", "", url_out

        if new_pass != confirm_pass:
            return True, HIDE, HIDE, SHOW, "", "", "⚠️ Las contraseñas no coinciden", "", url_out

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

        return True, HIDE, HIDE, SHOW, "", "", "✅ Credenciales actualizadas. Reinicia e inicia sesión.", "", url_out

    # --- VOLVER AL LOGIN ---
    if trigger in ("back-to-login-1", "back-to-login-2"):
        return True, SHOW, HIDE, HIDE, "", "", "", "", url_out

    # --- fallback: no tocar nada ---
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# CALLBACKS PRINCIPALES DEL DASHBOARD
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


# CALLBACKS PARA VENTAS DETALLADAS (1gr, 5gr, 10gr, etc.)
@app.callback(
    [
        Output("resultado-venta-1gr", "children"),
        Output("resultado-venta-5gr", "children"),
        Output("resultado-venta-10gr", "children"),
        Output("resultado-venta-20gr", "children"),
        Output("resultado-venta-1oz", "children"),
        Output("resultado-venta-100gr", "children"),
        Output("resultado-venta-200gr", "children"),
    ],
    [
        Input("btn-venta-1gr", "n_clicks"),
        Input("btn-venta-5gr", "n_clicks"),
        Input("btn-venta-10gr", "n_clicks"),
        Input("btn-venta-20gr", "n_clicks"),
        Input("btn-venta-1oz", "n_clicks"),
        Input("btn-venta-100gr", "n_clicks"),
        Input("btn-venta-200gr", "n_clicks"),
    ],
    [
        State("store-datos-anteriores", "data"),
        State("input-venta-1gr", "value"),
        State("input-venta-5gr", "value"),
        State("input-venta-10gr", "value"),
        State("input-venta-20gr", "value"),
        State("input-venta-1oz", "value"),
        State("input-venta-100gr", "value"),
        State("input-venta-200gr", "value"),
    ],
)
def calcular_ventas_detalladas(n1, n5, n10, n20, noz, n100, n200,
                               datos_anteriores,
                               v1, v5, v10, v20, voz, v100, v200):

    """
    Calcula los precios finales de cada lingote con base en el precio full del día anterior
    y guarda los porcentajes en el archivo JSON persistente.
    """
    def parse(v):
        try:
            return float(str(v).replace(",", ".")) if v not in (None, "") else 0.0
        except:
            return 0.0

    try:
        # 💰 Precio base del día anterior (full_cop)
        # Si store-datos-anteriores está vacío, recalculamos el FULL real.
        if not datos_anteriores or "full_cop" not in datos_anteriores:
            trm, _ = obtener_trm_banrep()
            oro_anterior = obtener_oro_dia_anterior()
            if isinstance(oro_anterior, tuple):
                oro_anterior = oro_anterior[0]
            precio_full = (oro_anterior / 31.10347) * trm
        else:
            precio_full = datos_anteriores["full_cop"]

        # Multiplicadores por peso
        factores = {
            "1gr": 1,
            "5gr": 5,
            "10gr": 10,
            "20gr": 20,
            "1oz": 31.10347,
            "100gr": 100,
            "200gr": 200
        }

        # Leer porcentajes desde los inputs
        v1, v5, v10, v20, voz, v100, v200 = map(parse, [v1, v5, v10, v20, voz, v100, v200])

        # Calcular resultados
        r1   = precio_full * factores["1gr"]   * (1 + v1  / 100)
        r5   = precio_full * factores["5gr"]   * (1 + v5  / 100)
        r10  = precio_full * factores["10gr"]  * (1 + v10 / 100)
        r20  = precio_full * factores["20gr"]  * (1 + v20 / 100)
        roz  = precio_full * factores["1oz"]   * (1 + voz / 100)
        r100 = precio_full * factores["100gr"] * (1 + v100 / 100)
        r200 = precio_full * factores["200gr"] * (1 + v200 / 100)

        # 💾 Guardar porcentajes en JSON
        data_actual = persistence_manager.load_percentages()
        persistence_manager.save_percentages(
            compra=data_actual.get("compra", 0.0),
            venta=data_actual.get("venta", 0.0),
            venta_directa=data_actual.get("venta_directa", 0.0),
            venta_1gr=v1, venta_5gr=v5, venta_10gr=v10,
            venta_20gr=v20, venta_1oz=voz,
            venta_100gr=v100, venta_200gr=v200
        )

        def fmt(v):
            return f"${formato_colombiano(v)}"

        return fmt(r1), fmt(r5), fmt(r10), fmt(r20), fmt(roz), fmt(r100), fmt(r200)

    except Exception as e:
        print(f"❌ Error calculando ventas detalladas: {e}")
        return ["Error"] * 7
    
# === REINICIALIZAR RESULTADOS AL CARGAR LA PÁGINA ===
@app.callback(
    [
        Output("input-venta-1gr", "value"),
        Output("input-venta-5gr", "value"),
        Output("input-venta-10gr", "value"),
        Output("input-venta-20gr", "value"),
        Output("input-venta-1oz", "value"),
        Output("input-venta-100gr", "value"),
        Output("input-venta-200gr", "value"),
    ],
    [Input("store-porcentajes-lingotes", "data")],
    prevent_initial_call=True
)
def cargar_porcentajes_guardados(p):
    """Carga los porcentajes anteriores en los inputs al abrir la página."""
    try:
        return (
            f"{p['venta_1gr']:.1f}",
            f"{p['venta_5gr']:.1f}",
            f"{p['venta_10gr']:.1f}",
            f"{p['venta_20gr']:.1f}",
            f"{p['venta_1oz']:.1f}",
            f"{p['venta_100gr']:.1f}",
            f"{p['venta_200gr']:.1f}",
        )
    except:
        return ["0.0"] * 7
    
# =======================
# CALLBACK: COMPRA (panel derecho)
# =======================
@app.callback(
    [
        Output("label-venta", "children"),
        Output("resultado-venta", "children"),
    ],
    Input("btn-venta", "n_clicks"),
    [
        State("input-venta", "value"),
        State("store-datos-anteriores", "data"),
    ],
    # Queremos que se ejecute también al cargar la página
    prevent_initial_call=False
)
def calcular_compra(n_clicks, porcentaje_str, datos_anteriores):
    # Parsear porcentaje desde el input (viene del JSON al cargar la página)
    try:
        porcentaje = float(str(porcentaje_str).replace(",", ".")) if porcentaje_str else 0.0
    except Exception:
        porcentaje = 0.0

    # FULL del día anterior
    if not datos_anteriores or "full_cop" not in datos_anteriores:
        trm, _ = obtener_trm_banrep()
        oro_anterior = obtener_oro_dia_anterior()
        if isinstance(oro_anterior, tuple):
            oro_anterior = oro_anterior[0]
        precio_full = (oro_anterior / 31.10347) * trm
    else:
        precio_full = datos_anteriores["full_cop"]

    precio = precio_full * (1 + porcentaje / 100.0)

    # 💾 Guardar en JSON (actualizando SOLO 'venta')
    data_actual = persistence_manager.load_percentages()
    persistence_manager.save_percentages(
        compra=data_actual.get("compra", 0.0),
        venta=porcentaje,
        venta_directa=data_actual.get("venta_directa", 0.0),
        venta_1gr=data_actual.get("venta_1gr", 0.0),
        venta_5gr=data_actual.get("venta_5gr", 0.0),
        venta_10gr=data_actual.get("venta_10gr", 0.0),
        venta_20gr=data_actual.get("venta_20gr", 0.0),
        venta_1oz=data_actual.get("venta_1oz", 0.0),
        venta_100gr=data_actual.get("venta_100gr", 0.0),
        venta_200gr=data_actual.get("venta_200gr", 0.0),
    )

    # Texto solo si el porcentaje es distinto de 0
    if porcentaje == 0.0:
        texto = ""
    else:
        texto = f""

    resultado = f"${formato_colombiano(precio)}"

    return texto, resultado


# ==========================
# CALLBACK: CONTRATACIÓN
# ==========================
@app.callback(
    [
        Output("label-venta-directa", "children"),
        Output("resultado-venta-directa", "children"),
    ],
    Input("btn-venta-directa", "n_clicks"),
    [
        State("input-venta-directa", "value"),
        State("store-datos-anteriores", "data"),
    ],
    # También se ejecuta al cargar para mostrar lo guardado
    prevent_initial_call=False
)
def calcular_contratacion(n_clicks, porcentaje_str, datos_anteriores):
    # Parsear porcentaje
    try:
        porcentaje = float(str(porcentaje_str).replace(",", ".")) if porcentaje_str else 0.0
    except Exception:
        porcentaje = 0.0

    # FULL del día anterior
    if not datos_anteriores or "full_cop" not in datos_anteriores:
        trm, _ = obtener_trm_banrep()
        oro_anterior = obtener_oro_dia_anterior()
        if isinstance(oro_anterior, tuple):
            oro_anterior = oro_anterior[0]
        precio_full = (oro_anterior / 31.10347) * trm
    else:
        precio_full = datos_anteriores["full_cop"]

    precio = precio_full * (1 + porcentaje / 100.0)

    # 💾 Guardar en JSON (actualizando SOLO 'venta_directa')
    data_actual = persistence_manager.load_percentages()
    persistence_manager.save_percentages(
        compra=data_actual.get("compra", 0.0),
        venta=data_actual.get("venta", 0.0),
        venta_directa=porcentaje,
        venta_1gr=data_actual.get("venta_1gr", 0.0),
        venta_5gr=data_actual.get("venta_5gr", 0.0),
        venta_10gr=data_actual.get("venta_10gr", 0.0),
        venta_20gr=data_actual.get("venta_20gr", 0.0),
        venta_1oz=data_actual.get("venta_1oz", 0.0),
        venta_100gr=data_actual.get("venta_100gr", 0.0),
        venta_200gr=data_actual.get("venta_200gr", 0.0),
    )

    # Texto solo si el porcentaje es distinto de 0
    if porcentaje == 0.0:
        texto = ""
    else:
        texto = f""

    resultado = f"${formato_colombiano(precio)}"

    return texto, resultado

# MAIN
if __name__ == '__main__':
    
    print("\n" + "="*60)
    print("🚀 OROEXPRESS - SISTEMA UNIFICADO")
    print("="*60)
    print("📊 VISTAS DISPONIBLES:")
    print("   🌐 LINGOTES:  http://localhost:8050/")
    print("   📈 DASHBOARD: http://localhost:8050/dashboard")
    print("\n📁 CARACTERÍSTICAS:")
    print(f"📁 Archivo JSON: {persistence_manager.percentages_file}")
    print("="*60)
    app.run(host='0.0.0.0', debug=False, port=8050)
