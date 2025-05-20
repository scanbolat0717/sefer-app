import streamlit as st
import pandas as pd
import openrouteservice
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# === ORS API KEY ===
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"  # <- Buraya kendi API anahtarını yaz

client = openrouteservice.Client(key=ORS_API_KEY)
geolocator = Nominatim(user_agent="ilce_rotasi_web")

# === İlçeleri Koordinatlara Çevirme ===
def ilce_koordinat_getir(ilce_adi):
    try:
        location = geolocator.geocode(f"{ilce_adi}, Türkiye")
        if location:
            return [location.longitude, location.latitude]
    except:
        return None

# === Rota ve Mesafe Hesaplama ===
def rota_ve_mesafe_hesapla(ilk, son):
    try:
        yss_koprusu = [29.0742, 41.1995]
        avrupa_lon = 28.8
        from_asya = ilk[0] > avrupa_lon
        to_asya = son[0] > avrupa_lon
        kopru_zorunlu = from_asya != to_asya

        # Hava mesafesi ile 150 km kontrolü (ORS sınırı)
        mesafe_hava = geodesic((ilk[1], ilk[0]), (son[1], son[0])).km
        kullan_avoid_polygons = mesafe_hava < 150

        if kopru_zorunlu:
            koordinatlar = [ilk, yss_koprusu, son]
        else:
            koordinatlar = [ilk, son]

        # Osmangazi ve Çanakkale çevresi (küçültülmüş)
        yasakli_bolgeler = {
            "type": "MultiPolygon",
            "coordinates": [
                [[
                    [29.55, 40.63], [29.65, 40.63],
                    [29.65, 40.73], [29.55, 40.73],
                    [29.55, 40.63]
                ]],
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

        if kullan_avoid_polygons:
            rota_opts["options"]["avoid_polygons"] = yasakli_bolgeler

        rota = client.directions(**rota_opts)

        mesafe = rota['features'][0]['properties']['segments'][0]['distance'] / 1000
        rota_link = f"https://maps.openrouteservice.org/directions?a={koordinatlar[0][1]},{koordinatlar[0][0]}"
        for k in koordinatlar[1:]:
            rota_link += f",{k[1]},{k[0]}"
        rota_link += "&b=0&c=0&k1=en-US&k2=km"

        return round(mesafe, 2), rota_link
    except Exception as e:
        return None, f"Hata: {str(e)}"

# === Streamlit Arayüzü ===
st.title("🚛 İlçe Bazlı Rota Hesaplayıcı")
st.markdown("""
Excel dosyanızda **'Çıkış'** ve **'Varış'** sütunları olmalı.  
- Kıta geçişinde **Yavuz Sultan Selim Köprüsü zorunludur.**  
- **Osmangazi ve Çanakkale köprüleri** yasaklıdır (kısa rotalarda).  
- **Feribot kullanılmaz.**
""")

yuklenen_dosya = st.file_uploader("📄 Excel Dosyası Yükle (.xlsx)", type=["xlsx"])

if yuklenen_dosya:
    df = pd.read_excel(yuklenen_dosya)

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("❌ 'Çıkış' ve 'Varış' sütunları bulunamadı.")
    else:
        mesafeler = []
        linkler = []

        with st.spinner("📍 Rotalar hesaplanıyor..."):
            for index, row in df.iterrows():
                cikis = ilce_koordinat_getir(row["Çıkış"])
                varis = ilce_koordinat_getir(row["Varış"])

                if not cikis or not varis:
                    mesafeler.append("Koordinat bulunamadı")
                    linkler.append("Yok")
                    continue

                mesafe, link = rota_ve_mesafe_hesapla(cikis, varis)
                mesafeler.append(mesafe)
                linkler.append(link)

                time.sleep(1)  # ORS API sınırı

        df["Mesafe (km)"] = mesafeler
        df["Rota Linki"] = linkler

        st.success("✅ Hesaplama tamamlandı.")
        st.dataframe(df)

        from io import BytesIO
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Sonuçları İndir (.xlsx)", data=buffer.getvalue(), file_name="rota_sonuclari.xlsx")

