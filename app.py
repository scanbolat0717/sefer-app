import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import openrouteservice as ors
from openrouteservice.exceptions import ApiError
from geopy.geocoders import Nominatim
import time

st.set_page_config(page_title="Sefer Rota Uygulaması", layout="wide")

# ORS API key buraya
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"
client = ors.Client(key=ORS_API_KEY)
geolocator = Nominatim(user_agent="sefer-app", timeout=10)

# Kıta bilgisi
AVRUPA_ILLERI = [
    "Edirne", "Kırklareli", "Tekirdağ", "İstanbul"
]
ASYA_ILLERI = [
    "Kocaeli", "Sakarya", "Yalova", "Bursa", "Balıkesir", "Bilecik", "Ankara", "İzmit",
    "ve diğer Anadolu illeri..."
]

# YSS Köprüsü üzerinde geçiş için ek noktalar
YSS_KOPRUSU_NOKTASI = [29.0742, 41.1815]  # Enlem, Boylam
KUZEY_MARMARA_GIRIS = [29.0135, 41.1769]
KUZEY_MARMARA_CIKIS = [29.1791, 41.1083]

def get_coordinates(place_name):
    try:
        location = geolocator.geocode(place_name)
        if location:
            return [location.longitude, location.latitude]
    except Exception as e:
        st.warning(f"Koordinat işlenemedi: {place_name} → {e}")
    return None

def get_route_distance(origin, destination, force_yss=False):
    try:
        coords = [origin]
        if force_yss:
            coords += [KUZEY_MARMARA_GIRIS, YSS_KOPRUSU_NOKTASI, KUZEY_MARMARA_CIKIS]
        coords.append(destination)

        route = client.directions(
            coordinates=coords,
            profile='driving-car',
            format='geojson'
        )
        distance_km = route['features'][0]['properties']['summary']['distance'] / 1000
        return distance_km, route
    except ApiError as e:
        st.error(f"ORS API hatası: {e}")
        return None, None

st.title("🗺️ Sefer Rota Uygulaması")
st.markdown("Excel dosyanızdan çıkış ve varış şehirlerini alır, OpenRouteService ile rota çizer.")

uploaded_file = st.file_uploader("Excel dosyanızı yükleyin (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    if 'Çıkış' not in df.columns or 'Varış' not in df.columns:
        st.error("Excel dosyasında 'Çıkış' ve 'Varış' sütunları bulunmalı.")
    else:
        m = folium.Map(location=[30.0, 30.0], zoom_start=6)
        results = []

        for idx, row in df.iterrows():
            origin_text = str(row["Çıkış"])
            dest_text = str(row["Varış"])

            origin_coords = get_coordinates(origin_text)
            dest_coords = get_coordinates(dest_text)

            st.write(f"Satır {idx+1} Çıkış: {origin_text} → {origin_coords}")
            st.write(f"Satır {idx+1} Varış: {dest_text} → {dest_coords}")

            if not origin_coords or not dest_coords:
                st.warning(f"Koordinat alınamadı (satır {idx+1}): {origin_text} → {dest_text}")
                continue

            origin_il = origin_text.split(",")[-1].strip()
            dest_il = dest_text.split(",")[-1].strip()

            force_yss = (
                (origin_il in AVRUPA_ILLERI and dest_il in ASYA_ILLERI) or
                (origin_il in ASYA_ILLERI and dest_il in AVRUPA_ILLERI)
            )

            distance, route = get_route_distance(origin_coords, dest_coords, force_yss=force_yss)

            if not distance:
                st.warning(f"Rota alınamadı (satır {idx+1}): {origin_text} → {dest_text}")
                continue

            results.append({
                "Çıkış": origin_text,
                "Varış": dest_text,
                "Mesafe (km)": round(distance, 2)
            })

            folium.Marker(
                location=[origin_coords[1], origin_coords[0]],
                popup=f"Çıkış: {origin_text}",
                icon=folium.Icon(color="green")
            ).add_to(m)

            folium.Marker(
                location=[dest_coords[1], dest_coords[0]],
                popup=f"Varış: {dest_text}",
                icon=folium.Icon(color="red")
            ).add_to(m)

            folium.PolyLine(
                locations=[
                    [coord[1], coord[0]] for coord in route['features'][0]['geometry']['coordinates']
                ],
                color="blue",
                weight=4,
                opacity=0.8
            ).add_to(m)

            time.sleep(1)  # Geocoding sınırını aşmamak için

        st_folium(m, width=1000)
        st.dataframe(pd.DataFrame(results))


