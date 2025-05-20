import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import openrouteservice
from geopy.geocoders import Nominatim
import time

# === OpenRouteService API Anahtarı ===
ORS_API_KEY = "5b3ce3597851110001cf6248df20429e7cbf4319809f3fd4eca2bc93"  # <-- BURAYA KENDİ ANAHTARINI YAZ

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
                [[  # Osmangazi
                    [29.45, 40.6], [29.8, 40.6],
                    [29.8, 40.8], [29.45,]()


