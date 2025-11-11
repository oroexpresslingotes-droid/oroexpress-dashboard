import requests
from bs4 import BeautifulSoup

def get_dolar_bogota(cert_path="certificados/Pbit.bancodebogota.crt"):
    """
    Obtiene las tasas de compra y venta del dólar desde Banco de Bogotá.
    """
    url = "https://pbit.bancodebogota.com/Informes/InformesEconomicos.aspx"
    response = requests.get(url, verify=cert_path)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    # Aquí deberemos inspeccionar el HTML real para ubicar las celdas correctas
    # Ejemplo de extracción (puede necesitar ajuste):
    dolar_data = soup.find_all("td", class_="valor")
    compra = dolar_data[0].text.strip()
    venta = dolar_data[1].text.strip()

    return {"compra": compra, "venta": venta}
