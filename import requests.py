import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext
from geopy.geocoders import Nominatim
from plyer import notification


def get_coordinates(city_name):
    geolocator = Nominatim(user_agent="weather_alert_app")
    location = geolocator.geocode(city_name)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None


def get_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("features", [])
    except Exception as e:
        messagebox.showerror("Erreur", f"Échec de récupération des alertes : {e}")
        return []


def show_alerts():
    city = city_entry.get()
    lat, lon = get_coordinates(city)

    if not lat or not lon:
        messagebox.showwarning("Ville inconnue", "Impossible de trouver la ville.")
        return

    alerts = get_alerts(lat, lon)
    output_area.delete(1.0, tk.END)

    if not alerts:
        output_area.insert(tk.END, "✅ Aucune alerte active trouvée pour cette ville.")
    else:
        for alert in alerts:
            title = alert['properties']['event']
            desc = alert['properties']['headline'] or alert['properties']['description'][:200]
            output_area.insert(tk.END, f"\n⚠️ {title}\n{desc}\n{'-'*40}\n")
            notification.notify(
                title=f"Alerte météo : {title}",
                message=desc,
                timeout=10
            )


# Interface Tkinter
root = tk.Tk()
root.title("Alertes Météo - NOAA/SPC")
root.geometry("500x400")

frame = tk.Frame(root)
frame.pack(pady=10)

label = tk.Label(frame, text="Entrez votre ville :")
label.pack(side=tk.LEFT)

city_entry = tk.Entry(frame, width=30)
city_entry.pack(side=tk.LEFT, padx=5)

btn = tk.Button(frame, text="Chercher les alertes", command=show_alerts)
btn.pack(side=tk.LEFT)

output_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=20)
output_area.pack(padx=10, pady=10)

root.mainloop()