import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# OpenRouteService API Anahtarı
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"  # <-- BURAYA KENDİ ANAHTARINI YAZ

def get_coordinates_from_text(place_name):
    st.write(f"{origin_text} koordinatları: {origin_coords}")
    st.write(f"{dest_text} koordinatları: {dest_coords}")
    url = "https://api.openrouteservice.org/geocode/search"
    headers = {"Authorization": ORS_API_KEY}
    params = {
        "text": place_name,
        "size": 1,
        "boundary.country": "TR",
        "boundary.rect.min_lon": 25.0,
        "boundary.rect.min_lat": 35.0,
        "boundary.rect.max_lon": 45.0,
        "boundary.rect.max_lat": 43.0
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if response.status_code == 200 and data.get("features"):
            coords = data["features"][0]["geometry"]["coordinates"]  # [lon, lat]
            return coords
    except Exception:
        pass
    return None

def get_route_distance(origin, destination):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}
    body = {
        "coordinates": [origin, destination]
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        data = response.json()
        if response.status_code != 200 or "features" not in data:
            return None, None
        distance_km = data["features"][0]["properties"]["summary"]["distance"] / 1000
        geometry = data["features"][0]["geometry"]["coordinates"]
        return distance_km, geometry
    except Exception as e:
        st.warning(f"ORS yanıtı işlenemedi: {e}")
        return None, None

st.title("🗺️ Şehir İsimleriyle Sefer Rota ve Mesafe Hesaplayıcı")

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

        distance, route = get_route_distance(origin_coords, dest_coords)
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

