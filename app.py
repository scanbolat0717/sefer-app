import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# OpenRouteService API anahtarınızı buraya yapıştırın
ORS_API_KEY = "YOUR_ORS_API_KEY"  # 🔁 <--- kendi API anahtarını buraya koy

def get_route_distance(origin, destination):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}
    body = {
        "coordinates": [origin, destination]
    }

    response = requests.post(url, json=body, headers=headers)
    data = response.json()

    if response.status_code != 200:
        error_msg = data.get("error", {}).get("message", "Bilinmeyen hata")
        st.warning(f"ORS API hatası ({response.status_code}): {error_msg}")
        return None, None

    try:
        distance_km = data["features"][0]["properties"]["summary"]["distance"] / 1000
        geometry = data["features"][0]["geometry"]["coordinates"]
        return distance_km, geometry
    except Exception as e:
        st.warning(f"Yanıt işlenemedi: {e}")
        return None, None

# Streamlit arayüzü
st.title("Sefer Rota Hesaplayıcı")
uploaded_file = st.file_uploader("Excel dosyanızı yükleyin", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Excel okunamadı: {e}")
        st.stop()

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("Excel dosyasında 'Çıkış' ve 'Varış' sütunları bulunmalı.")
        st.stop()

    map_center = [39.0, 35.0]
    m = folium.Map(location=map_center, zoom_start=6)

    distances = []
    for idx, row in df.iterrows():
        try:
            # Temizleme
            origin_raw = str(row["Çıkış"]).replace("[", "").replace("]", "")
            destination_raw = str(row["Varış"]).replace("[", "").replace("]", "")

            # Koordinatlara çevirme
            origin = [float(i.strip()) for i in origin_raw.split(",")]
            destination = [float(i.strip()) for i in destination_raw.split(",")]

            # Enlem, boylam → boylam, enlem
            if len(origin) == 2:
                origin = [origin[1], origin[0]]
            if len(destination) == 2:
                destination = [destination[1], destination[0]]

            distance, route = get_route_distance(origin, destination)
            if distance is None:
                st.warning(f"Rota alınamadı (satır {idx+2})")
                continue

            distances.append(distance)
            folium.Marker(location=origin[::-1], popup="Çıkış", icon=folium.Icon(color="blue")).add_to(m)
            folium.Marker(location=destination[::-1], popup="Varış", icon=folium.Icon(color="green")).add_to(m)
            folium.PolyLine(locations=[[coord[1], coord[0]] for coord in route], color="red").add_to(m)

        except Exception as e:
            st.warning(f"Koordinat işlenemedi (satır {idx+2}): {e}")
            continue

    folium_static(m)

    if distances:
        st.success(f"Toplam {len(distances)} sefer işlendi.")
        st.write(f"Toplam mesafe: {sum(distances):.2f} km")
    else:
        st.warning("Hiçbir sefer işlenemedi.")
