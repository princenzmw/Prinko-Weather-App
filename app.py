
# -*- coding: utf-8 -*-
"""
Tkinter Weather App — OpenWeatherMap

Requirements:
- Python 3.9+
- requests
- Pillow (PIL)

Features:
- Enter a city and fetch current weather (temp °C, condition) with icon
- Error handling for invalid city / network issues
- Background color adapts to weather (sunny/clear=yellow, cloudy=gray, rainy=blue)
- Resizable window, centered layout using grid weights
- Short comments throughout the code

Setup:
- Put your OpenWeatherMap API key in the environment variable OWM_API_KEY
  or create a .env file beside this script with: OWM_API_KEY=your_key_here

Author: M365 Copilot
"""

import io
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests

API_URL = "https://api.openweathermap.org/data/2.5/weather"
ICON_URL = "https://openweathermap.org/img/wn/{icon}@2x.png"


def load_api_key() -> str:
    """Load API key from env var or .env file in current directory."""
    key = os.getenv("OWM_API_KEY")
    if key:
        return key
    # Fallback: read .env in current dir
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('OWM_API_KEY='):
                        return line.split('=', 1)[1].strip()
        except Exception:
            pass
    return ''


class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TK Weather — OpenWeatherMap")
        self.geometry("560x380")
        self.minsize(460, 320)
        self.resizable(True, True)

        # Keep a reference to the last PhotoImage to avoid garbage collection
        self._icon_photo = None

        # Configure a centered, responsive grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Main frame to center content
        self.main = ttk.Frame(self, padding=20)
        self.main.grid(row=0, column=0, sticky="nsew")
        for r in range(6):
            self.main.rowconfigure(r, weight=1)
        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)

        # Title label
        self.title_lbl = ttk.Label(self.main, text="Weather Now", font=("Segoe UI", 18, "bold"))
        self.title_lbl.grid(row=0, column=0, columnspan=2, sticky="n", pady=(0, 10))

        # City entry + button in a sub-frame for better centering
        entry_frame = ttk.Frame(self.main)
        entry_frame.grid(row=1, column=0, columnspan=2)
        self.city_var = tk.StringVar()
        self.city_entry = ttk.Entry(entry_frame, textvariable=self.city_var, width=28, font=("Segoe UI", 11))
        self.city_entry.grid(row=0, column=0, padx=(0, 8))
        self.city_entry.bind('<Return>', lambda e: self.fetch_weather())
        self.fetch_btn = ttk.Button(entry_frame, text="Get Weather", command=self.fetch_weather)
        self.fetch_btn.grid(row=0, column=1)

        # Output area: temperature, condition, icon
        self.temp_var = tk.StringVar(value="— °C")
        self.cond_var = tk.StringVar(value="—")

        self.temp_lbl = ttk.Label(self.main, textvariable=self.temp_var, font=("Segoe UI", 24, "bold"))
        self.temp_lbl.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        self.cond_lbl = ttk.Label(self.main, textvariable=self.cond_var, font=("Segoe UI", 14))
        self.cond_lbl.grid(row=3, column=0, columnspan=2)

        self.icon_lbl = ttk.Label(self.main)
        self.icon_lbl.grid(row=4, column=0, columnspan=2)

        # Status label for errors / info
        self.status_var = tk.StringVar(value="Enter a city and press Enter or click Get Weather.")
        self.status_lbl = ttk.Label(self.main, textvariable=self.status_var, foreground="#444")
        self.status_lbl.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        # Default theme
        self.set_theme("Default")

        # Focus the entry initially
        self.city_entry.focus_set()

    def set_theme(self, condition_main: str):
        """Adjust background color depending on weather condition.
        - Clear → sunny yellow
        - Clouds → gray
        - Rain/Drizzle/Thunderstorm → blue
        Else keep a neutral light background
        """
        cond = (condition_main or '').lower()
        if 'clear' in cond:
            bg = '#fff7b2'  # sunny yellow (soft)
        elif 'cloud' in cond:
            bg = '#e6e6e6'  # gray
        elif any(k in cond for k in ['rain', 'drizzle', 'thunder']):
            bg = '#cfe8ff'  # blue-ish
        else:
            bg = '#f5f7fb'  # neutral

        # Apply background to root and non-ttk widgets; for ttk, set style map
        self.configure(bg=bg)
        for w in (self.main,):
            try:
                w.configure(style='Bg.TFrame')
            except tk.TclError:
                pass
        # Create/override a style with the computed background
        style = ttk.Style(self)
        style.configure('Bg.TFrame', background=bg)
        style.configure('Bg.TLabel', background=bg)
        # Apply to select labels that should blend
        self.title_lbl.configure(style='Bg.TLabel')
        self.temp_lbl.configure(style='Bg.TLabel')
        self.cond_lbl.configure(style='Bg.TLabel')
        self.status_lbl.configure(style='Bg.TLabel')

    def fetch_weather(self):
        """Start a background thread to call the API so UI stays responsive."""
        city = self.city_var.get().strip()
        if not city:
            self.status_var.set("Please enter a city name.")
            return
        api_key = load_api_key()
        if not api_key:
            messagebox.showerror("Missing API Key", "Set environment variable OWM_API_KEY or create a .env file with OWM_API_KEY=your_key")
            return

        self.status_var.set("Fetching weather…")
        self.fetch_btn.configure(state=tk.DISABLED)

        def worker():
            try:
                params = {"q": city, "appid": api_key, "units": "metric"}
                resp = requests.get(API_URL, params=params, timeout=10)
                # Raise for transport errors (HTTP 4xx/5xx will not raise unless we call raise_for_status)
                data = resp.json()
                # Handle API-level errors (e.g. invalid city)
                if resp.status_code != 200 or str(data.get('cod')) != '200':
                    msg = data.get('message', 'Unable to fetch weather data.')
                    raise ValueError(f"API error: {msg}")

                # Extract fields
                main = data.get('main', {})
                weather_list = data.get('weather', [])
                condition = weather_list[0] if weather_list else {}
                temp_c = main.get('temp')
                cond_main = condition.get('main', '')
                cond_desc = condition.get('description', '').title()
                icon = condition.get('icon', '')

                # Download icon (optional)
                icon_img = None
                if icon:
                    try:
                        icon_url = ICON_URL.format(icon=icon)
                        ic_resp = requests.get(icon_url, timeout=10)
                        ic_resp.raise_for_status()
                        icon_img = Image.open(io.BytesIO(ic_resp.content))
                    except Exception:
                        icon_img = None

                # Update UI on main thread
                def update_ui():
                    self.temp_var.set(f"{temp_c:.1f} °C" if isinstance(temp_c, (int, float)) else "— °C")
                    self.cond_var.set(cond_desc or cond_main or "—")
                    self.set_theme(cond_main or cond_desc)
                    if icon_img:
                        # Resize to a reasonable size (maintain quality)
                        resized = icon_img.resize((100, 100), Image.LANCZOS)
                        self._icon_photo = ImageTk.PhotoImage(resized)
                        self.icon_lbl.configure(image=self._icon_photo)
                    else:
                        self.icon_lbl.configure(image='')
                    self.status_var.set(f"Updated for {city}")
                    self.fetch_btn.configure(state=tk.NORMAL)
                self.after(0, update_ui)

            except ValueError as ve:
                def show_err():
                    self.status_var.set(str(ve))
                    messagebox.showerror("City Error", str(ve))
                    self.fetch_btn.configure(state=tk.NORMAL)
                self.after(0, show_err)

            except requests.RequestException as re:
                def show_net():
                    self.status_var.set("Network error — please check your internet and try again.")
                    messagebox.showerror("Network Error", f"{re}")
                    self.fetch_btn.configure(state=tk.NORMAL)
                self.after(0, show_net)

            except Exception as e:
                def show_generic():
                    self.status_var.set("Unexpected error occurred.")
                    messagebox.showerror("Error", f"{e}")
                    self.fetch_btn.configure(state=tk.NORMAL)
                self.after(0, show_generic)

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = WeatherApp()
    app.mainloop()


if __name__ == '__main__':
    main()
