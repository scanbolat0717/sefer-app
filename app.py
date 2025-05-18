import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# ORS API Key'inizi buraya yazın
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"

# YSS Köprüsü (3. Köprü) koordinatları (lon, lat)
YSS_COORDS = [29.0729, 41.1858]

def get_coordinates(address):
    """ORS Geocoding API ile adresi koordinata çevirir"""
    url = f"https://api.openrouteservice.org/geocode/search"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    params = {
        "api_key": ORS_API_KEY,
        "text": address,
        "boundary.country": "TR"
    }
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    try:
        coords = data["features"][0]["geometry"]["coordinates"]
        return coords  # [lon, lat]
    except:
        return None

def get_route_with_ors(origin, destination, use_yss=False):
    """ORS Directions API ile rota alır"""
    try:
        coords = [origin]
        if use_yss:
            coords.append(YSS_COORDS)
        coords.append(destination)

        body = {
            "coordinates": coords,
            "format": "geojson"
        }

        headers = {
            "Authorization": ORS_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
            json=body, headers=headers
        )
        data = response.json()

        distance_km = data["features"][0]["properties"]["summary"]["distance"] / 1000
        geometry = data["features"][0]["geometry"]["coordinates"]
        return distance_km, geometry
    except Exception as e:
        return None, None

# Streamlit Arayüz
st.title("🚐 İlçe ve Şehir Bazlı Türkiye Sefer Rotaları (ORS + YSS Köprüsü)")

uploaded_file = st.file_uploader("📥 Excel dosyasını yükleyin (Çıkış ve Varış sütunları içermeli)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Dosya okunamadı: {e}")
        st.stop()

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("Excel dosyasında 'Çıkış' ve 'Varış' sütunları olmalı.")
        st.stop()

    m = folium.Map(location=[39.0, 35.0], zoom_start=6)
    toplam = 0
    basarili = 0

    for idx, row in df.iterrows():
        origin_text = str(row["Çıkış"])
        dest_text = str(row["Varış"])

        origin_coords = get_coordinates(origin_text)
        dest_coords = get_coordinates(dest_text)

        if not origin_coords or not dest_coords:
            st.warning(f"Koordinat işlenemedi (satır {idx+2}): {origin_text} → {dest_text}")
            continue

        use_yss = "İstanbul" in origin_text or "İstanbul" in dest_text
        distance_km, route = get_route_with_ors(origin_coords, dest_coords, use_yss=use_yss)

        if distance_km is None or route is None:
            st.warning(f"Rota alınamadı (satır {idx+2}): {origin_text} → {dest_text}")
            continue

        folium.Marker(location=origin_coords[::-1], popup=origin_text, icon=folium.Icon(color="blue")).add_to(m)
        folium.Marker(location=dest_coords[::-1], popup=dest_text, icon=folium.Icon(color="green")).add_to(m)
        folium.PolyLine(locations=[[pt[1], pt[0]] for pt in route], color="red").add_to(m)

        toplam += distance_km
        basarili += 1

    folium_static(m)

    if basarili > 0:
        st.success(f"{basarili} rota başarıyla işlendi.")
        st.write(f"Toplam mesafe: **{toplam:.2f} km**")
    else:
        st.warning("Hiçbir rota başarıyla işlenemedi.")

