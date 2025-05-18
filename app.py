import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# OpenRouteService API Key
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"

# Zorunlu geçiş noktaları (lon, lat)
KMO_ASYA = [29.3575, 41.1445]       # Kuzey Marmara Otoyolu – Asya tarafı
YSS_ASYA = [29.0386, 41.1772]       # YSS Köprüsü – Asya rampası
YSS_AVRUPA = [29.0582, 41.1821]     # YSS Köprüsü – Avrupa rampası
KMO_AVRUPA = [28.8100, 41.2000]     # Kuzey Marmara Otoyolu – Avrupa tarafı

# İstanbul ilçeleri
asya_ilceler = ["Üsküdar", "Kadıköy", "Ataşehir", "Maltepe", "Kartal", "Pendik", "Tuzla", "Sancaktepe", "Sultanbeyli", "Çekmeköy", "Ümraniye", "Şile", "Beykoz"]
avrupa_ilceler = ["Fatih", "Eminönü", "Bakırköy", "Beşiktaş", "Şişli", "Sarıyer", "Eyüpsultan", "Kağıthane", "Bayrampaşa", "Zeytinburnu", "Avcılar", "Beylikdüzü", "Esenyurt", "Başakşehir", "Bağcılar", "Gaziosmanpaşa", "Küçükçekmece"]

# Türkiye şehirleri (kıta ayrımı)
asya_iller = ["Adana", "Ankara", "Antalya", "Bursa", "Konya", "Kayseri", "Eskişehir", "Samsun", "Erzurum", "Diyarbakır", "Trabzon", "Mersin", "Van", "Gaziantep", "Kocaeli", "Sakarya", "Manisa", "İzmir"]
avrupa_iller = ["Edirne", "Kırklareli", "Tekirdağ", "İstanbul"]

# Kıta belirleme fonksiyonu
def get_kita(text):
    text = text.lower()
    for ilce in asya_ilceler:
        if ilce.lower() in text:
            return "asya"
    for ilce in avrupa_ilceler:
        if ilce.lower() in text:
            return "avrupa"
    for il in asya_iller:
        if il.lower() in text:
            return "asya"
    for il in avrupa_iller:
        if il.lower() in text:
            return "avrupa"
    return None

# ORS geocode
def get_coordinates(address):
    url = "https://api.openrouteservice.org/geocode/search"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    params = {
        "text": address,
        "boundary.country": "TR"
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    try:
        coords = data["features"][0]["geometry"]["coordinates"]
        return coords
    except:
        return None

# ORS yönlendirme fonksiyonu
def get_route_with_ors(origin, destination, use_yss_kmo=False):
    try:
        if use_yss_kmo:
            coords = [origin, KMO_ASYA, YSS_ASYA, YSS_AVRUPA, KMO_AVRUPA, destination]
        else:
            coords = [origin, destination]

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
    except Exception:
        return None, None

# Streamlit arayüz
st.title("🚛 YSS + KMO Zorunlu Türkiye Rota Hesaplama")

uploaded_file = st.file_uploader("📥 Excel dosyasını yükleyin ('Çıkış' ve 'Varış' sütunları içermeli)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Excel okunamadı: {e}")
        st.stop()

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("Excel dosyasında 'Çıkış' ve 'Varış' sütunları olmalı.")
        st.stop()

    m = folium.Map(location=[39.0, 35.0], zoom_start=6)
    toplam_mesafe = 0
    basarili = 0

    for idx, row in df.iterrows():
        origin_text = str(row["Çıkış"])
        dest_text = str(row["Varış"])

        origin_coords = get_coordinates(origin_text)
        dest_coords = get_coordinates(dest_text)

        if not origin_coords or not dest_coords:
            st.warning(f"Koordinat alınamadı (satır {idx+2}): {origin_text} → {dest_text}")
            continue

        origin_kita = get_kita(origin_text)
        dest_kita = get_kita(dest_text)
        use_yss_kmo = origin_kita and dest_kita and origin_kita != dest_kita

        distance_km, route = get_route_with_ors(origin_coords, dest_coords, use_yss_kmo)

        if distance_km is None or route is None:
            st.warning(f"Rota alınamadı (satır {idx+2}): {origin_text} → {dest_text}")
            continue

        folium.Marker(location=origin_coords[::-1], popup=origin_text, icon=folium.Icon(color="blue")).add_to(m)
        folium.Marker(location=dest_coords[::-1], popup=dest_text, icon=folium.Icon(color="green")).add_to(m)
        folium.PolyLine(locations=[[pt[1], pt[0]] for pt in route], color="red", weight=4).add_to(m)

        toplam_mesafe += distance_km
        basarili += 1

    folium_static(m)

    if basarili > 0:
        st.success(f"{basarili} rota başarıyla hesaplandı.")
        st.write(f"Toplam mesafe: **{toplam_mesafe:.2f} km**")
    else:
        st.warning("Hiçbir rota hesaplanamadı.")

