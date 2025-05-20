import streamlit as st
import pandas as pd
import openrouteservice
from geopy.geocoders import Nominatim
import time

# === ORS API KEY ===
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"  # Buraya kendi OpenRouteService API anahtarını yaz

client = openrouteservice.Client(key=ORS_API_KEY)
geolocator = Nominatim(user_agent="ilce_rotasi_web")

def ilce_koordinat_getir(ilce_adi):
    try:
        location = geolocator.geocode(f"{ilce_adi}, Türkiye")
        if location:
            return [location.longitude, location.latitude]
    except:
        return None

def rota_ve_mesafe_hesapla(ilk, son):
    try:
        yss_koprusu = [29.0742, 41.1995]

        # Küçültülmüş yasaklı bölgeler (Osmangazi ve Çanakkale köprü çevresi)
        yasakli_bolgeler = {
            "type": "MultiPolygon",
            "coordinates": [
                [[  # Osmangazi çevresi
                    [29.55, 40.63], [29.65, 40.63],
                    [29.65, 40.73], [29.55, 40.73],
                    [29.55, 40.63]
                ]],
                [[  # Çanakkale çevresi
                    [26.35, 40.12], [26.45, 40.12],
                    [26.45, 40.22], [26.35, 40.22],
                    [26.35, 40.12]
                ]]
            ]
        }

        avrupa_lon = 28.8
        from_asya = ilk[0] > avrupa_lon
        to_asya = son[0] > avrupa_lon
        kopru_zorunlu = from_asya != to_asya

        if kopru_zorunlu:
            koordinatlar = [ilk, yss_koprusu, son]
        else:
            koordinatlar = [ilk, son]

        rota = client.directions(
            coordinates=koordinatlar,
            profile='driving-car',
            format='geojson',
            options={
                "avoid_polygons": yasakli_bolgeler,
                "avoid_features": ["ferries"]
            }
        )

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
- Kıta geçişinde **Yavuz Sultan Selim Köprüsü** zorunludur.  
- **Osmangazi ve Çanakkale köprüleri** yasaklıdır.  
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

                time.sleep(1)  # API sınırına uymak için

        df["Mesafe (km)"] = mesafeler
        df["Rota Linki"] = linkler

        st.success("✅ Hesaplama tamamlandı.")
        st.dataframe(df)

        from io import BytesIO
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Sonuçları İndir (.xlsx)", data=buffer.getvalue(), file_name="rota_sonuclari.xlsx")

