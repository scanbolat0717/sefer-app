import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# Türkiye şehirlerinin sabit koordinatları (lon, lat)
şehir_koordinatları = {
    "İstanbul": [28.9784, 41.0082],
    "Ankara": [32.8540, 39.9208],
    "İzmir": [27.1428, 38.4192],
    "Bursa": [29.0610, 40.1952],
    "Konya": [32.4846, 37.8746],
    "Adana": [35.3213, 37.0025],
    "Antalya": [30.7133, 36.8841],
    "Gaziantep": [37.3780, 37.0650],
    "Trabzon": [39.7200, 41.0015],
    "Kayseri": [35.4955, 38.7225],
    "Eskişehir": [30.5234, 39.7667],
    "Diyarbakır": [40.2100, 37.9144],
    "Samsun": [36.3300, 41.2867],
    "Erzurum": [41.2756, 39.9043],
    "Malatya": [38.3000, 38.3552],
    "Mersin": [34.6415, 36.8000],
    "Denizli": [29.0870, 37.7765],
    "Manisa": [27.4217, 38.6191]
}

# Yavuz Sultan Selim Köprüsü koordinatları (tam ortası) – (lon, lat)
yss_koprusu = [29.0729, 41.1858]

def get_coordinates_from_text(place_name):
    return şehir_koordinatları.get(place_name)

def get_route_osrm(origin, destination, use_yss=False):
    try:
        if use_yss:
            coord_string = f"{origin[0]},{origin[1]};{yss_koprusu[0]},{yss_koprusu[1]};{destination[0]},{destination[1]}"
        else:
            coord_string = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
        
        url = f"http://router.project-osrm.org/route/v1/driving/{coord_string}?overview=full&geometries=geojson"
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200 or "routes" not in data:
            return None, None
        distance_km = data["routes"][0]["distance"] / 1000
        geometry = data["routes"][0]["geometry"]["coordinates"]
        return distance_km, geometry
    except Exception as e:
        st.warning(f"OSRM yanıtı işlenemedi: {e}")
        return None, None

# Streamlit Arayüzü
st.title("🛣️ Türkiye Şehirler Arası Rota Hesaplama (YSS Köprüsü Zorunlu)")

uploaded_file = st.file_uploader("Excel dosyasını yükleyin (Çıkış ve Varış sütunlarıyla)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Excel dosyası okunamadı: {e}")
        st.stop()

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("Excel'de 'Çıkış' ve 'Varış' sütunları bulunmalı.")
        st.stop()

    m = folium.Map(location=[39.0, 35.0], zoom_start=6)
    toplam_mesafeler = []

    for idx, row in df.iterrows():
        origin_text = str(row["Çıkış"]).strip()
        dest_text = str(row["Varış"]).strip()

        origin_coords = get_coordinates_from_text(origin_text)
        dest_coords = get_coordinates_from_text(dest_text)

        if not origin_coords or not dest_coords:
            st.warning(f"Koordinat alınamadı (satır {idx+2}): {origin_text} → {dest_text}")
            continue

        # İstanbul geçişi varsa, YSS Köprüsü kullanılsın
        yss_zorunlu = origin_text == "İstanbul" or dest_text == "İstanbul"

        distance, route = get_route_osrm(origin_coords, dest_coords, use_yss=yss_zorunlu)
        if distance is None:
            st.warning(f"Rota alınamadı (satır {idx+2}): {origin_text} → {dest_text}")
            continue

        toplam_mesafeler.append(distance)
        folium.Marker(location=origin_coords[::-1], popup=origin_text, icon=folium.Icon(color="blue")).add_to(m)
        folium.Marker(location=dest_coords[::-1], popup=dest_text, icon=folium.Icon(color="green")).add_to(m)
        folium.PolyLine(locations=[[pt[1], pt[0]] for pt in route], color="red").add_to(m)

    folium_static(m)

    if toplam_mesafeler:
        st.success(f"{len(toplam_mesafeler)} sefer işlendi.")
        st.write(f"Toplam mesafe: **{sum(toplam_mesafeler):.2f} km**")
    else:
        st.warning("Hiçbir sefer başarıyla işlenemedi.")


