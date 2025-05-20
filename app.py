import streamlit as st
import pandas as pd
import openrouteservice
from geopy.geocoders import Nominatim
import time

# === ORS API KEY ===
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"  # <== BURAYA KENDİ API ANAHTARINI YAZ

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
        yasakli_bolgeler = {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [29.45, 40.6], [29.8, 40.6],
                    [29.8, 40.8], [29.45, 40.8],
                    [29.45, 40.6]
                ],
                [
                    [26.25, 40.1], [26.75, 40.1],
                    [26.75, 40.5], [26.25, 40.5],
                    [26.25, 40.1]
                ]
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
            avoid_polygons=yasakli_bolgeler,
            options={"avoid_features": ["ferries"]}
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
st.title("🚚 İlçe Bazlı Rota Hesaplayıcı")
st.markdown("""
Excel dosyanızda **'Çıkış'** ve **'Varış'** adında iki sütun olmalı.  
Bu uygulama kıta geçişlerinde *Yavuz Sultan Selim Köprüsü* kullanır.  
*Osmangazi, Çanakkale köprüleri* ve *feribotlar* yasaktır.
""")

yuklenen_dosya = st.file_uploader("📁 Excel Dosyası Yükle (.xlsx)", type=["xlsx"])

if yuklenen_dosya:
    df = pd.read_excel(yuklenen_dosya)

    if "Çıkış" not in df.columns or "Varış" not in df.columns:
        st.error("❌ Lütfen 'Çıkış' ve 'Varış' sütunlarını içeren bir dosya yükleyin.")
    else:
        mesafeler = []
        linkler = []

        with st.spinner("🧭 Rotalar hesaplanıyor..."):
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

                time.sleep(1)  # ORS API limitine uymak için bekle

        df["Mesafe (km)"] = mesafeler
        df["Rota Linki"] = linkler

        st.success("✅ Rotalar başarıyla hesaplandı.")
        st.dataframe(df)

        # İndirilebilir Excel
        from io import BytesIO
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Sonuçları İndir (.xlsx)", data=buffer.getvalue(), file_name="rotali_sonuclar.xlsx")

