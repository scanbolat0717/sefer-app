
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
    response = requests.post(url, json=body, headers=headers)
    if response.status_code == 200:
        data = response.json()
        distance_km = data["features"][0]["properties"]["summary"]["distance"] / 1000
        geometry = data["features"][0]["geometry"]["coordinates"]
        return round(distance_km, 2), geometry
    else:
        return None, None

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("Yüklenen veri:")
    st.dataframe(df)

    if "Çıkış" in df.columns and "Varış" in df.columns:
        st.subheader("Rota Sonuçları")

        routes = []
        for idx, row in df.iterrows():
            origin = [float(i) for i in row["Çıkış"].split(",")]
            destination = [float(i) for i in row["Varış"].split(",")]
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
