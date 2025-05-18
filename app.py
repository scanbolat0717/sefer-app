
import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Sefer Rota Hesaplayıcı", layout="wide")
st.title("🗺️ Sefer Rota Hesaplayıcı")

st.markdown("Excel dosyanızı yükleyin. Çıkış ve varış yerleri üzerinden en kısa rota hesaplanacaktır.")

uploaded_file = st.file_uploader("Excel dosyasını yükleyin", type=["xlsx"])

ORS_API_KEY = st.secrets["ORS_API_KEY"]

def get_route_distance(origin, destination):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [origin, destination]
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        data = response.json()

        # Geçersiz istek kontrolü
        if response.status_code != 200:
            st.warning(f"ORS API hatası ({response.status_code}): {data.get('error', {}).get('message', 'Bilinmeyen hata')}")
            return None, None

        features = data.get("features", [])
        if not features:
            st.warning("Rota bulunamadı. Lütfen koordinatları kontrol et.")
            return None, None

        distance_km = features[0]["properties"]["summary"]["distance"] / 1000
        geometry = features[0]["geometry"]["coordinates"]
        return round(distance_km, 2), geometry

    except Exception as e:
        st.error(f"Beklenmeyen bir hata oluştu: {e}")
        return None, None


if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("Yüklenen veri:")
    st.dataframe(df)

    if "Çıkış" in df.columns and "Varış" in df.columns:
        st.subheader("Rota Sonuçları")

        routes = []
for index, row in df.iterrows():
    try:
        origin = [float(i.strip()) for i in str(row["Çıkış"]).split(",")]
        destination = [float(i.strip()) for i in str(row["Varış"]).split(",")]

        if len(origin) != 2 or len(destination) != 2:
            st.warning(f"Geçersiz koordinat formatı: {row['Çıkış']} → {row['Varış']}")
            continue

        distance, geometry = get_route_distance(origin, destination)

        if distance is not None:
            distances.append({
                "Çıkış": row["Çıkış"],
                "Varış": row["Varış"],
                "Mesafe (km)": distance
            })
    except Exception as e:
        st.warning(f"Koordinat işlenemedi: {e}")
        continue
            distance, _ = get_route_distance(origin, destination)
            routes.append({
                "Çıkış": row["Çıkış"],
                "Varış": row["Varış"],
                "Mesafe (km)": distance
            })

        result_df = pd.DataFrame(routes)
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Sonuçları İndir (CSV)", csv, "rota_sonuclari.csv", "text/csv")
    else:
        st.error("Excel dosyasında 'Çıkış' ve 'Varış' sütunları bulunmalı.")
