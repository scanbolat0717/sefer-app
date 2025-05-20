import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import openrouteservice
from geopy.geocoders import Nominatim
import time

# === OpenRouteService API Anahtarı ===
ORS_API_KEY = "YOUR_ORS_API_KEY"  # <-- BURAYA KENDİ ANAHTARINI YAZ

client = openrouteservice.Client(key=ORS_API_KEY)
geolocator = Nominatim(user_agent="ilce_rotasi")

# === İlçe adını koordinata çevir ===
def ilce_koordinat_getir(ilce_adi):
    try:
        location = geolocator.geocode(f"{ilce_adi}, Türkiye")
        if location:
            return [location.longitude, location.latitude]
    except:
        return None

# === Rota ve mesafe hesaplama ===
def rota_ve_mesafe_hesapla(ilk, son):
    try:
        # Yavuz Sultan Selim Köprüsü (YSS) koordinatları
        yss_koprusu = [29.0742, 41.1995]

        # Yasaklı bölgeler: Osmangazi ve Çanakkale köprüleri çevresi
        yasakli_bolgeler = {
            "type": "MultiPolygon",
            "coordinates": [
                [  # Osmangazi
                    [29.45, 40.6], [29.8, 40.6],
                    [29.8, 40.8], [29.45, 40.8],
                    [29.45, 40.6]
                ],
                [  # Çanakkale
                    [26.25, 40.1], [26.75, 40.1],
                    [26.75, 40.5], [26.25, 40.5],
                    [26.25, 40.1]
                ]
            ]
        }

        # Kıta değişimi kontrolü
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

# === Excel işle ve yaz ===
def dosya_sec_ve_isle():
    dosya_yolu = filedialog.askopenfilename(filetypes=[("Excel Dosyaları", "*.xlsx")])
    if not dosya_yolu:
        return

    try:
        df = pd.read_excel(dosya_yolu)

        if "Çıkış" not in df.columns or "Varış" not in df.columns:
            messagebox.showerror("Hata", "Excel'de 'Çıkış' ve 'Varış' sütunları bulunmalı.")
            return

        mesafeler = []
        linkler = []

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

            time.sleep(1)  # API sınırına uymak için bekle

        df["Mesafe (km)"] = mesafeler
        df["Rota Linki"] = linkler

        yeni_yol = dosya_yolu.replace(".xlsx", "_rotali.xlsx")
        df.to_excel(yeni_yol, index=False)
        messagebox.showinfo("Tamamlandı", f"İşlem tamamlandı.\nKayıt: {yeni_yol}")

    except Exception as e:
        messagebox.showerror("Hata", str(e))

# === Arayüz (Tkinter) ===
pencere = tk.Tk()
pencere.title("İlçe Bazlı Rota Oluşturucu")
pencere.geometry("420x180")

etiket = tk.Label(pencere, text="Excel'de 'Çıkış' ve 'Varış' ilçeleri olan dosyayı seçin.")
etiket.pack(pady=20)

buton = tk.Button(pencere, text="Excel Dosyası Seç ve Hesapla", command=dosya_sec_ve_isle)
buton.pack(pady=10)

pencere.mainloop()

