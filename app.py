import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# OpenRouteService API anahtarını buraya yaz
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"  # 🔁 BURAYA KENDİ ANAHTARINI YAZ

def get_coordinates_from_text(place_name):
    url = "https://api.openrouteservice.org/geocode/search"
    headers = {"Authorization": ORS_API_KEY}
    params = {
        "text": place_name,
        "size": 1,
        "boundary.country": "TR"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if response.status_code == 200 and data.get("features"):
            return data["features"][0]["geometry"]["coordinates"]  # [lon, lat]
    except Exception:
        pass
    return None

def get_route_distance(origin, destination):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}
    body = {
        "coordinates": [origin, destination]
    }

    response = requests.post(url, json=body, headers=headers)

    try:
        data = response.json()
    except ValueError:
        st.warning(f"ORS API JSON yanıtı çözülemedi. Ham içerik: {response.text}")
        return None, None

    if response.status_code != 200:
        error_msg = data.get("error", {}).get("message", "Bilinmeyen hata")
        st.warning(f"ORS API hatası ({response.status_code}): {error_msg}")
        return None, None

    try:
        distance_km = data["features"][0]["properties"]["summary"]["distance"] / 1000
        geometry = data["features"][0]["geometry"]["coordinates"]
        return distance_km, geometry
    except Exception as e:
        st.warning(f"ORS yanıtı işlenemedi: {e}")
        return None, None

# Streamlit Arayüzü
st.title("🚗 Şehir Bazlı Sefer Rota Hesaplayıcı")

uploaded_file = st.file_uploader("Excel dosyanızı yükleyin (Çıkış, Varış sütunlarıyla)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Excel okunamadı: {e}")
        st.stop()

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("Excel'de 'Çıkış' ve 'Varış' sütunları bulunmalı.")
        st.stop()

    m = folium.Map(location=[39.0, 35.0], zoom_start=6)
    distances = []

    for idx, row in df.iterrows():
        origin_name = str(row["Çıkış"]).strip()
        dest_name = str(row["Varış"]).strip()

        origin_coords = get_coordinates_from_text(origin_name)
        dest_coords = get_coordinates_from_text(dest_name)

        if not origin_coords or not dest_coords:
            st.warning(f"Koordinat bulunamadı (satır {idx+2}): {origin_name} → {dest_name}")
            continue

        distance, route = get_route_distance(origin_coords, dest_coords)
        if distance is None:
            st.warning(f"Rota alınamadı (satır {idx+2})")
            continue

        distances.append(distance)

        folium.Marker(location=origin_coords[::-1], popup=origin_name, icon=folium.Icon(color="blue")).add_to(m)
        folium.Marker(location=dest_coords[::-1], popup=dest_name, icon=folium.Icon(color="green")).add_to(m)
        folium.PolyLine(locations=[[pt[1], pt[0]] for pt in route], color="red").add_to(m)

    folium_static(m)

    if distances:
        st.success(f"✅ {len(distances)} sefer işlendi.")
        st.write(f"🛣️ Toplam mesafe: **{sum(distances):.2f} km**")
    else:
        st.warning("Hiçbir sefer başarıyla işlenemedi.")
