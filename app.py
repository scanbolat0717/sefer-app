import streamlit as st
import pandas as pd
import openrouteservice
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium
import time

# --- API anahtarınız ---
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"  # ← Buraya kendi ORS API key'inizi yazın

client = openrouteservice.Client(key=ORS_API_KEY)
geolocator = Nominatim(user_agent="ilce_rotasi_web")

# --- İlçeyi koordinata çevir ---
def ilce_koordinat_getir(ilce_adi):
    try:
        location = geolocator.geocode(f"{ilce_adi}, Türkiye")
        if location:
            return [location.longitude, location.latitude]
    except:
        return None

# --- Google Maps Linki ---
def google_maps_link(ilk, son):
    return f"https://www.google.com/maps/dir/{ilk[1]},{ilk[0]}/{son[1]},{son[0]}"

# --- Harita Göster ---
def rota_harita_goster(rota_geojson, baslik):
    m = folium.Map(location=[41.0, 29.0], zoom_start=8)
    folium.GeoJson(rota_geojson, name="Rota").add_to(m)
    folium.LayerControl().add_to(m)
    st.markdown(f"### 🗺️ {baslik}")
    st_folium(m, width=700, height=500)

# --- Rota Hesapla ---
def rota_ve_mesafe_hesapla(ilk, son):
    try:
        yss_koprusu = [29.0742, 41.1995]
        avrupa_lon = 28.8
        from_asya = ilk[0] > avrupa_lon
        to_asya = son[0] > avrupa_lon
        kopru_zorunlu = from_asya != to_asya

        mesafe_hava = geodesic((ilk[1], ilk[0]), (son[1], son[0])).km
        kullan_avoid = mesafe_hava < 150

        koordinatlar = [ilk, son]
        if kopru_zorunlu:
            koordinatlar = [ilk, yss_koprusu, son]

        yasakli_bolgeler = {
            "type": "MultiPolygon",
            "coordinates": [
                # FSM Köprüsü
                [[
                    [29.03, 41.09], [29.08, 41.09],
                    [29.08, 41.12], [29.03, 41.12],
                    [29.03, 41.09]
                ]],
                # 15 Temmuz Köprüsü
                [[
                    [29.01, 41.02], [29.06, 41.02],
                    [29.06, 41.05], [29.01, 41.05],
                    [29.01, 41.02]
                ]],
                # Boğaz orta kısım (feribot engeli)
                [[
                    [29.00, 40.98], [29.07, 40.98],
                    [29.07, 41.07], [29.00, 41.07],
                    [29.00, 40.98]
                ]],
                # Osmangazi Köprüsü
                [[
                    [29.45, 40.63], [29.65, 40.63],
                    [29.65, 40.73], [29.45, 40.73],
                    [29.45, 40.63]
                ]],
                # Çanakkale Köprüsü
                [[
                    [26.35, 40.12], [26.45, 40.12],
                    [26.45, 40.22], [26.35, 40.22],
                    [26.35, 40.12]
                ]]
            ]
        }

        rota_opts = {
            "coordinates": koordinatlar,
            "profile": "driving-car",
            "format": "geojson",
            "options": {
                "avoid_features": ["ferries"]
            }
        }

        if kopru_zorunlu and kullan_avoid:
            rota_opts["options"]["avoid_polygons"] = yasakli_bolgeler

        rota = client.directions(**rota_opts)
        mesafe = rota['features'][0]['properties']['segments'][0]['distance'] / 1000
        return round(mesafe, 2), rota

    except Exception as e:
        return None, f"Hata: {str(e)}"

# --- Streamlit Arayüzü ---
st.title("🚛 İlçe Bazlı Rota Hesaplama (YSS Zorunlu)")
st.markdown("""
✅ Kıta geçişlerinde **Yavuz Sultan Selim Köprüsü** zorunludur  
⛔ **Osmangazi, Çanakkale** köprüleri ve **feribotlar** yasaklıdır  
📍 Rotalar interaktif harita ile gösterilir
""")

yuklenen_dosya = st.file_uploader("📄 Excel Dosyası (.xlsx)", type=["xlsx"])

if yuklenen_dosya:
    df = pd.read_excel(yuklenen_dosya)

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("❌ Lütfen 'Çıkış' ve 'Varış' sütunlarını içeren bir dosya yükleyin.")
    else:
        mesafeler = []
        google_linkler = []

        with st.spinner("📍 Rotalar hesaplanıyor..."):
            for index, row in df.iterrows():
                cikis = ilce_koordinat_getir(row["Çıkış"])
                varis = ilce_koordinat_getir(row["Varış"])

                if not cikis or not varis:
                    mesafeler.append("Koordinat yok")
                    google_linkler.append("Yok")
                    continue

                mesafe, rota = rota_ve_mesafe_hesapla(cikis, varis)
                mesafeler.append(mesafe)
                google_linkler.append(google_maps_link(cikis, varis))

                if isinstance(rota, dict):
                    rota_harita_goster(rota, f"{row['Çıkış']} → {row['Varış']}")

                time.sleep(1)

        df["Mesafe (km)"] = mesafeler
        df["Google Maps Linki"] = google_linkler

        st.success("✅ Tüm rotalar hesaplandı.")
        st.dataframe(df)

        from io import BytesIO
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Sonuçları İndir (.xlsx)", data=buffer.getvalue(), file_name="rota_sonuclari.xlsx")
