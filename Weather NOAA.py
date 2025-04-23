import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk
from geopy.geocoders import Nominatim
from plyer import notification
import pyttsx3
import pygame
import time
import threading
import folium
from folium.plugins import FloatImage
import os
from tkinterweb import HtmlFrame

# Initialize pygame mixer
pygame.mixer.init()

# Global variables
monitoring = False
mute_audio = False
refresh_interval = 60  # default to 60 seconds
cities = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"
]


def play_tornado_sound():
    try:
        pygame.mixer.music.load("tornado_alert.mp3")
        pygame.mixer.music.play()
        time.sleep(10)
        pygame.mixer.music.stop()
    except Exception as e:
        messagebox.showerror("Sound Error", f"Unable to play tornado sound: {e}")


def get_coordinates(city_name):
    geolocator = Nominatim(user_agent="weather_alert_app")
    locations = geolocator.geocode(city_name, exactly_one=False, limit=5)
    if not locations:
        return None, None
    if len(locations) > 1:
        options = {f"{loc.address}": loc for loc in locations}
        selection = tk.Toplevel(root)
        selection.title("Select a Location")
        ttk.Label(selection, text="Multiple matches found, please choose one:").pack(pady=5)
        selected_var = tk.StringVar(selection)
        dropdown = ttk.Combobox(selection, textvariable=selected_var, values=list(options.keys()), state="readonly")
        dropdown.pack(pady=10)
        result = {'lat': None, 'lon': None}

        def confirm():
            choice = selected_var.get()
            loc = options.get(choice)
            if loc:
                result['lat'], result['lon'] = loc.latitude, loc.longitude
            selection.destroy()

        ttk.Button(selection, text="Confirm", command=confirm).pack(pady=5)
        selection.wait_window()
        return result['lat'], result['lon']
    return locations[0].latitude, locations[0].longitude


def get_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("features", [])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to retrieve alerts: {e}")
        return []


def get_nationwide_alerts():
    url = "https://api.weather.gov/alerts/active"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("features", [])
    except Exception as e:
        return []


def show_alerts():
    city = city_entry.get()
    lat, lon = get_coordinates(city)

    if not lat or not lon:
        messagebox.showwarning("Unknown City", "Could not find the specified city.")
        return

    alerts = get_alerts(lat, lon)
    display_alerts(alerts)


def speak_alert(title, desc):
    if mute_audio:
        return
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        full_message = f"Weather Alert: {title}. {desc}"
        engine.say(full_message)
        engine.runAndWait()
        engine.stop()
        del engine
    except Exception as e:
        print(f"TTS error: {e}")


def show_alert_map(lat, lon):
    try:
        m = folium.Map(location=[lat, lon], zoom_start=7)
        FloatImage("https://tilecache.rainviewer.com/v2/radar/nowcast/512/{z}/{x}/{y}/2/1_1.png", bottom=10, left=70).add_to(m)
        folium.Marker([lat, lon], popup="Alert Location").add_to(m)
        map_path = os.path.abspath("alert_map.html")
        m.save(map_path)
        map_frame.load_url(f"file://{map_path}")
    except Exception as e:
        print(f"Error generating map: {e}")


def display_alerts(alerts):
    output_area.delete(1.0, tk.END)
    if not alerts:
        output_area.insert(tk.END, "✅ No active alerts found.")
    else:
        for alert in alerts:
            title = alert['properties']['event']
            desc = alert['properties']['description'] or "No description provided."
            output_area.insert(tk.END, f"\n⚠️ {title}\n{desc}\n{'-'*40}\n")
            notification.notify(
                title=f"Weather Alert: {title}",
                message=desc,
                timeout=10
            )
            if not mute_audio:
                try:
                    pygame.mixer.music.load("tornado_alert.mp3")
                    pygame.mixer.music.play()
                    time.sleep(10)
                    pygame.mixer.music.stop()
                except Exception as e:
                    print(f"Sound error: {e}")
                speak_alert(title, desc)
            area = alert['properties'].get('areaDesc', '')
            if 'geocode' in alert['properties'] and 'UGC' in alert['properties']['geocode']:
                try:
                    coords = alert['geometry']['coordinates'][0][0] if alert.get('geometry') else None
                    if coords:
                        lat = coords[1]
                        lon = coords[0]
                        show_alert_map(lat, lon)
                except:
                    pass


def monitor_nationwide_alerts():
    global monitoring
    seen_alerts = set()
    while monitoring:
        alerts = get_nationwide_alerts()
        new_alerts = [a for a in alerts if a['id'] not in seen_alerts]
        for alert in new_alerts:
            seen_alerts.add(alert['id'])
        if new_alerts:
            display_alerts(new_alerts)
        time.sleep(refresh_interval)


def toggle_monitoring():
    global monitoring
    if not monitoring:
        messagebox.showinfo("Warning", "Enabling nationwide monitoring may result in a large number of notifications.")
        monitoring = True
        monitor_btn.config(text="Stop Monitoring")
        threading.Thread(target=monitor_nationwide_alerts, daemon=True).start()
    else:
        monitoring = False
        monitor_btn.config(text="Start Nationwide Monitoring")


def toggle_mute():
    global mute_audio
    mute_audio = not mute_audio
    mute_btn.config(text="Unmute" if mute_audio else "Mute")


def set_refresh_interval():
    global refresh_interval
    try:
        interval = simpledialog.askinteger("Refresh Interval", "Enter refresh interval in seconds:", minvalue=10, maxvalue=3600)
        if interval:
            refresh_interval = interval
    except:
        pass

# Tkinter GUI
root = tk.Tk()
root.title("Weather Alerts - NOAA/SPC")
root.geometry("700x900")

frame = tk.Frame(root)
frame.pack(pady=10)

label = tk.Label(frame, text="Enter your city:")
label.pack(side=tk.LEFT)

city_entry = tk.Entry(frame, width=30)
city_entry.pack(side=tk.LEFT, padx=5)

btn = tk.Button(frame, text="Check Alerts", command=show_alerts)
btn.pack(side=tk.LEFT)

refresh_btn = tk.Button(root, text="Refresh Alerts", command=show_alerts)
refresh_btn.pack(pady=5)

monitor_btn = tk.Button(root, text="Start Nationwide Monitoring", command=toggle_monitoring)
monitor_btn.pack(pady=5)

mute_btn = tk.Button(root, text="Mute", command=toggle_mute)
mute_btn.pack(pady=5)

interval_btn = tk.Button(root, text="Set Refresh Interval", command=set_refresh_interval)
interval_btn.pack(pady=5)

tornado_btn = tk.Button(root, text="Play Tornado Alert Sound", command=play_tornado_sound)
tornado_btn.pack(pady=5)

output_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=15)
output_area.pack(padx=10, pady=10)

map_frame = HtmlFrame(root, horizontal_scrollbar="auto")
map_frame.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()
