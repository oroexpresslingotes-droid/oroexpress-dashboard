# ======================================================
# DIAGNÓSTICO - VERIFICACIÓN DE DATOS EXTRAÍDOS
# ======================================================
from datetime import datetime, date, timedelta
import requests
from bs4 import BeautifulSoup
import investpy
import pandas as pd

def diagnostico_extraccion_datos():
    print("🔍 INICIANDO DIAGNÓSTICO DE EXTRACCIÓN DE DATOS")
    print("=" * 60)
    
    # Fechas de referencia
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    print(f"📅 Fecha hoy: {hoy.strftime('%d/%m/%Y')}")
    print(f"📅 Fecha ayer: {ayer.strftime('%d/%m/%Y')}")
    print(f"⏰ Hora actual: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # ======================================================
    # 1. DIAGNÓSTICO TRM - BANCO DE LA REPÚBLICA
    # ======================================================
    print("1. 🔄 DIAGNÓSTICO TRM - BANCO DE LA REPÚBLICA")
    print("-" * 40)
    
    try:
        url = "https://www.datos.gov.co/resource/32sa-8pi3.json?$limit=5&$order=vigenciadesde%20desc"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print("📊 ÚLTIMOS 5 REGISTROS ENCONTRADOS:")
        for i, registro in enumerate(data):
            fecha = registro["vigenciadesde"][:10]
            valor = float(registro["valor"])
            print(f"   {i+1}. Fecha: {fecha} - TRM: ${valor:,.0f} COP")
        
        trm_actual = float(data[0]["valor"])
        fecha_actual = data[0]["vigenciadesde"][:10]
        print(f"\n✅ TRM ACTUAL (más reciente):")
        print(f"   Fecha: {fecha_actual}")
        print(f"   Valor: ${trm_actual:,.0f} COP")
        
        # Buscar específicamente el día anterior
        fecha_ayer_str = ayer.strftime("%Y-%m-%d")
        url_ayer = f"https://www.datos.gov.co/resource/32sa-8pi3.json?vigenciadesde={fecha_ayer_str}"
        response_ayer = requests.get(url_ayer, timeout=10)
        data_ayer = response_ayer.json()
        
        if data_ayer:
            trm_ayer = float(data_ayer[0]["valor"])
            print(f"\n🎯 TRM DÍA ANTERIOR (específico):")
            print(f"   Fecha: {fecha_ayer_str}")
            print(f"   Valor: ${trm_ayer:,.0f} COP")
        else:
            print(f"\n❌ NO se encontró TRM para ayer ({fecha_ayer_str})")
            
    except Exception as e:
        print(f"❌ Error en TRM: {e}")
    
    print()
    
    # ======================================================
    # 2. DIAGNÓSTICO ORO - INVESTPY
    # ======================================================
    print("2. 🔄 DIAGNÓSTICO ORO - INVESTPY")
    print("-" * 40)
    
    try:
        # Intentar obtener datos históricos
        fecha_inicio = (hoy - timedelta(days=3)).strftime("%d/%m/%Y")  # Últimos 3 días
        fecha_fin = hoy.strftime("%d/%m/%Y")
        
        print(f"📅 Solicitando datos desde: {fecha_inicio} hasta: {fecha_fin}")
        
        df = investpy.get_commodity_historical_data(
            commodity='gold',
            from_date=fecha_inicio,
            to_date=fecha_fin
        )
        
        print("📊 DATOS OBTENIDOS:")
        print(df.tail())  # Últimas filas
        
        if not df.empty:
            # Verificar fechas disponibles
            print(f"\n📈 Rango de fechas en datos:")
            print(f"   Primera fecha: {df.index[0]}")
            print(f"   Última fecha: {df.index[-1]}")
            
            # Buscar específicamente el día anterior
            fecha_ayer_investpy = ayer.strftime("%d/%m/%Y")
            print(f"\n🔍 Buscando datos para ayer: {fecha_ayer_investpy}")
            
            # Convertir índice a formato comparable
            df_fechas = df.reset_index()
            df_fechas['date_str'] = df_fechas['Date'].dt.strftime('%d/%m/%Y')
            
            datos_ayer = df_fechas[df_fechas['date_str'] == fecha_ayer_investpy]
            
            if not datos_ayer.empty:
                precio_cierre_ayer = float(datos_ayer['Close'].iloc[0])
                print(f"✅ ORO DÍA ANTERIOR ENCONTRADO:")
                print(f"   Fecha: {fecha_ayer_investpy}")
                print(f"   Cierre: ${precio_cierre_ayer:,.2f} USD")
            else:
                print(f"❌ NO se encontraron datos de oro para ayer")
                
            # Mostrar el dato más reciente
            ultimo_precio = float(df['Close'].iloc[-1])
            ultima_fecha = df.index[-1].strftime('%d/%m/%Y')
            print(f"\n📊 ÚLTIMO DATO DISPONIBLE:")
            print(f"   Fecha: {ultima_fecha}")
            print(f"   Cierre: ${ultimo_precio:,.2f} USD")
                
        else:
            print("❌ No se obtuvieron datos del oro")
            
    except Exception as e:
        print(f"❌ Error en InvestPy: {e}")
        print("💡 InvestPy puede estar deprecado o bloqueado")
    
    print()
    
    # ======================================================
    # 3. DIAGNÓSTICO ORO - KITCO (TIEMPO REAL)
    # ======================================================
    print("3. 🔄 DIAGNÓSTICO ORO - KITCO (TIEMPO REAL)")
    print("-" * 40)
    
    try:
        url = "https://www.kitco.com/charts/livegold.html"
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        s = BeautifulSoup(r.text, "html.parser")
        h3 = s.find("h3", class_="font-mulish")
        
        if h3:
            valor = h3.text.strip().replace(",", "")
            precio_actual = float(valor)
            print(f"✅ ORO TIEMPO REAL (Kitco):")
            print(f"   Precio actual: ${precio_actual:,.2f} USD")
        else:
            print("❌ No se pudo extraer precio de Kitco")
            
    except Exception as e:
        print(f"❌ Error en Kitco: {e}")
    
    print()
    print("=" * 60)
    print("🎯 RESUMEN DEL DIAGNÓSTICO:")
    print("=" * 60)
    print("• TRM: Verificar si el primer registro es de HOY o de AYER")
    print("• ORO: Verificar si InvestPy devuelve datos históricos correctos")
    print("• COMPARAR: ¿Los datos de 'ayer' coinciden con cierres reales?")
    print("=" * 60)

# Ejecutar diagnóstico
if __name__ == "__main__":
    diagnostico_extraccion_datos()