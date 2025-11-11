import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_gold_previous_day():
    """
    Obtiene el precio del oro (USD/onza) del día anterior desde Investing.com.
    Detecta correctamente la segunda fila (día anterior) de la tabla histórica.
    """
    try:
        url = "https://www.investing.com/commodities/gold-historical-data"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.select("table tbody tr")
        if len(rows) < 2:
            raise ValueError("No hay suficientes filas en la tabla para obtener el día anterior.")

        # Buscamos la segunda fila válida (la primera suele ser hoy)
        valid_rows = []
        for r in rows:
            cols = [c.get_text(strip=True).replace(",", "") for c in r.find_all("td")]
            if len(cols) >= 2:
                try:
                    float(cols[1])
                    valid_rows.append(cols)
                except ValueError:
                    continue

        if len(valid_rows) < 2:
            raise ValueError("No se encontró una segunda fila con valor numérico.")

        # Segunda fila → día anterior
        date_str, price_str = valid_rows[1][0], valid_rows[1][1]
        close_price = float(price_str)

        # Detectar formato de fecha
        parsed_date = None
        for fmt in ("%b %d, %Y", "%b %d %Y", "%d.%m.%Y"):
            try:
                parsed_date = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

        if not parsed_date:
            raise ValueError(f"Formato de fecha desconocido: {date_str}")

        print(f"📅 Fecha detectada (día anterior): {parsed_date} | 💰 Oro (USD): {close_price}")
        return float(close_price)

    except Exception as e:
        print(f"⚠️ Error al obtener el precio del oro desde Investing: {e}")
        return 1950.0


if __name__ == "__main__":
    precio = get_gold_previous_day()
    print(f"💰 Precio del oro (día anterior, USD): {precio}")
