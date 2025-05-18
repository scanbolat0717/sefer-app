import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

# ORS API anahtarını al
ORS_API_KEY = st.secrets["ORS_API_KEY"]

st.set_page_config(page_title="Sefer Rota Hesaplama", layout="wide")
st.title("🧭 Sefer Rota Mesafe Hesaplama Uygulaması")

uploaded_file = st.file_uploader("Excel dosyanızı yükleyin", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Excel okunamadı: {e}")
        st.stop()

    # Sütun kontrolü
    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("Excel dosyasında 'Çıkış' ve 'Varış' sütunları bulunmalı.")
        st.stop()

    distances = []

    # Her satır için rota hesapla
    for index, row in df.iterrows():
        try:
            origin = [float(i.strip()) for i in str(row["Çıkış"]).split(",")]
            destination = [float(i.strip()) for i in str(row["Varış"]).split(",")]

            if len(origin) != 2 or len(destination) != 2:
                st.warning(f"Geçersiz koordinat formatı: {row['Çıkış']} → {row['Varış']}")
                continue

            # ORS API'den mesafe bilgisi al
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
                try:
                    data = response.json()

                    if response.status_code != 200:
                        st.warning(f"ORS API hatası ({response.status_code}): {data.get('error', {}).get('message', 'Bilinmeyen hata')}")
                        return None, None

                    features = data.get("features", [])
                    if not features:
                        st.warning(f"Rota bulunamadı: {origin} → {destination}")
                        return None, None

                    distance_km = features[0]["properties"]["summary"]["distance"] / 1000
                    geometry = features[0]["geometry"]["coordinates"]
                    return round(distance_km, 2), geometry
                except Exception as e:
                    st.warning(f"ORS yanıt hatası: {e}")
                    return None, None

            distance, geometry = get_route_distance(origin, destination)

            if distance is not None:
                distances.append({
                    "Çıkış": row["Çıkış"],
                    "Varış": row["Varış"],
                    "Mesafe (km)": distance
                })

                # Harita göster
                m = folium.Map(location=[origin[1], origin[0]], zoom_start=10)
                folium.Marker([origin[1], origin[0]], tooltip="Çıkış").add_to(m)
                folium.Marker([destination[1], destination[0]], tooltip="Varış").add_to(m)

                if geometry:
                    folium.PolyLine([[coord[1], coord[0]] for coord in geometry], color="blue").add_to(m)

                st.markdown(f"### 🛣️ {row['Çıkış']} → {row['Varış']}")
                st.markdown(f"**Mesafe:** {distance} km")
                st_folium(m, width=700, height=400)

        except Exception as e:
            st.warning(f"Koordinat işlenemedi (satır {index + 2}): {e}")
            continue

    # Tüm sonuçları tablo olarak göster
    if distances:
        result_df = pd.DataFrame(distances)
        st.markdown("## 📊 Tüm Mesafeler")
        st.dataframe(result_df)

        # Excel çıktısı indir
        output = result_df.to_excel(index=False)
        st.download_button("📥 Sonuçları indir (Excel)", data=output, file_name="rota_sonuclari.xlsx")

else:
    st.info("Lütfen yukarıdan Excel dosyanızı yükleyin.")


        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Sonuçları İndir (CSV)", csv, "rota_sonuclari.csv", "text/csv")
    else:
        st.error("Excel dosyasında 'Çıkış' ve 'Varış' sütunları bulunmalı.")
