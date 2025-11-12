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

Author: Prince NZAMUWE
"""

import io
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from ttkthemes import ThemedTk

API_URL = "https://api.openweathermap.org/data/2.5/weather"
ICON_URL = "https://openweathermap.org/img/wn/{icon}@2x.png"
GEOCODE_URL = "http://api.openweathermap.org/geo/1.0/direct"


def load_api_key() -> str:
    """Load API key from env var or .env file in current directory."""
    key = os.getenv("OWM_API_KEY")
    if key:
        return key
    # Fallback: read .env in current dir
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("OWM_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return ""


class WeatherApp(ThemedTk):
    def __init__(self):
        super().__init__(theme="arc")  # Modern theme
        self.title("Prinko Weather — OpenWeatherMap")
        self.geometry("600x450")
        self.minsize(500, 400)
        self.resizable(True, True)

        # Keep a reference to the last PhotoImage to avoid garbage collection
        self._icon_photo = None

        # Configure a centered, responsive grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Main frame to center content
        self.main = ttk.Frame(self, padding=25)
        self.main.grid(row=0, column=0, sticky="nsew")
        for r in range(10):
            self.main.rowconfigure(r, weight=1)
        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)

        # Title label
        self.title_lbl = ttk.Label(
            self.main, text="Prinko Weather", font=("Segoe UI", 20, "bold")
        )
        self.title_lbl.grid(row=0, column=0, columnspan=2, sticky="n", pady=(0, 15))

        # City entry + button in a sub-frame for better centering
        entry_frame = ttk.Frame(self.main)
        entry_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        self.city_var = tk.StringVar()
        self.city_entry = ttk.Entry(
            entry_frame, textvariable=self.city_var, width=30, font=("Segoe UI", 12)
        )
        self.city_entry.grid(row=0, column=0, padx=(0, 10))
        self.city_entry.bind("<Return>", lambda e: self.fetch_weather())
        self.fetch_btn = ttk.Button(
            entry_frame, text="Get Weather", command=self.fetch_weather
        )
        self.fetch_btn.grid(row=0, column=1)

        # Unit toggle button
        self.unit_var = tk.StringVar(value="C")
        self.unit_btn = ttk.Button(
            entry_frame, textvariable=self.unit_var, width=3, command=self.toggle_units
        )
        self.unit_btn.grid(row=0, column=2, padx=(10, 0))

        # Autocomplete listbox (hidden initially)
        self.suggestions_box = tk.Listbox(self.main, height=5, font=("Segoe UI", 10))
        self.suggestions_box.bind("<<ListboxSelect>>", self._on_suggestion_select)
        self.suggestions_box.bind("<Double-Button-1>", self._on_suggestion_click)
        self.suggestions_box.bind(
            "<Return>", self._on_suggestion_select
        )  # Enter to select
        self.suggestions_box.bind("<Up>", self._navigate_suggestions)
        self.suggestions_box.bind("<Down>", self._navigate_suggestions)
        self.suggestions_visible = False

        # Progress bar for loading
        self.progress = ttk.Progressbar(self.main, mode="indeterminate")
        self.progress.grid(row=2, column=0, columnspan=2, pady=(5, 10), sticky="ew")
        self.progress.grid_remove()  # Hide initially

        # Output area: temperature, condition, icon
        self.temp_var = tk.StringVar(value="— °C")
        self.cond_var = tk.StringVar(value="—")
        self.details_var = tk.StringVar(
            value="Humidity: —% | Wind: — km/h | Feels like: — °C"
        )

        self.temp_lbl = ttk.Label(
            self.main, textvariable=self.temp_var, font=("Segoe UI", 28, "bold")
        )
        self.temp_lbl.grid(row=3, column=0, columnspan=2, pady=(10, 5))

        self.cond_lbl = ttk.Label(
            self.main, textvariable=self.cond_var, font=("Segoe UI", 16)
        )
        self.cond_lbl.grid(row=4, column=0, columnspan=2)

        self.details_lbl = ttk.Label(
            self.main,
            textvariable=self.details_var,
            font=("Segoe UI", 12),
            foreground="#555",
        )
        self.details_lbl.grid(row=5, column=0, columnspan=2, pady=(5, 10))

        self.icon_lbl = ttk.Label(self.main)
        self.icon_lbl.grid(row=6, column=0, columnspan=2)

        # Forecast button
        self.forecast_btn = ttk.Button(
            self.main, text="5-Day Forecast", command=self.fetch_forecast
        )
        self.forecast_btn.grid(row=7, column=0, columnspan=2, pady=(15, 5))

        # Status label for errors / info
        self.status_var = tk.StringVar(
            value="Enter a city and press Enter or click Get Weather."
        )
        self.status_lbl = ttk.Label(
            self.main,
            textvariable=self.status_var,
            foreground="#444",
            font=("Segoe UI", 10),
        )
        self.status_lbl.grid(row=8, column=0, columnspan=2, pady=(10, 0))

        # Default theme
        self.update_theme("Default")

        # Bind key release for autocomplete
        self.city_entry.bind("<KeyRelease>", self._on_keyrelease)
        self.city_entry.bind("<FocusOut>", lambda e: self._hide_suggestions())
        self._after_id = None

        # Focus the entry initially
        self.city_entry.focus_set()

    def toggle_units(self):
        """Toggle between Celsius and Fahrenheit."""
        self.unit_var.set("F" if self.unit_var.get() == "C" else "C")
        # Refetch if there's a city
        if self.city_var.get().strip():
            self.fetch_weather()

    def update_theme(self, condition_main: str):
        """Adjust background color depending on weather condition.
        - Clear → sunny yellow
        - Clouds → gray
        - Rain/Drizzle/Thunderstorm → blue
        Else keep a neutral light background
        """
        cond = (condition_main or "").lower()
        if "clear" in cond:
            bg = "#fff7b2"  # sunny yellow (soft)
        elif "cloud" in cond:
            bg = "#e6e6e6"  # gray
        elif any(k in cond for k in ["rain", "drizzle", "thunder"]):
            bg = "#cfe8ff"  # blue-ish
        else:
            bg = "#f5f7fb"  # neutral

        # Apply background to root and non-ttk widgets; for ttk, set style map
        self.configure(bg=bg)
        for w in (self.main,):
            try:
                w.configure(style="Bg.TFrame")
            except tk.TclError:
                pass
        # Create/override a style with the computed background
        style = ttk.Style(self)
        style.configure("Bg.TFrame", background=bg)
        style.configure("Bg.TLabel", background=bg)
        # Apply to select labels that should blend
        self.title_lbl.configure(style="Bg.TLabel")
        self.temp_lbl.configure(style="Bg.TLabel")
        self.cond_lbl.configure(style="Bg.TLabel")
        self.details_lbl.configure(style="Bg.TLabel")
        self.status_lbl.configure(style="Bg.TLabel")

    def _on_keyrelease(self, event=None):
        """Debounce key events and schedule autocomplete lookup."""
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(400, self._do_autocomplete)

    def _do_autocomplete(self):
        q = self.city_var.get().strip()
        if not q or len(q) < 2:
            self._hide_suggestions()
            return

        def worker():
            try:
                params = {"q": q, "limit": 5, "appid": load_api_key()}
                resp = requests.get(GEOCODE_URL, params=params, timeout=5)
                resp.raise_for_status()
                items = resp.json()
                suggestions = []
                for it in items:
                    name = it.get("name", "")
                    state = it.get("state", "")
                    country = it.get("country", "")
                    if state:
                        label = f"{name}, {state}, {country}"
                    else:
                        label = f"{name}, {country}"
                    suggestions.append(label)
            except Exception:
                suggestions = []

            self.after(0, lambda: self._show_suggestions(suggestions))

        threading.Thread(target=worker, daemon=True).start()

    def _show_suggestions(self, items):
        self.suggestions_box.delete(0, tk.END)
        for it in items:
            self.suggestions_box.insert(tk.END, it)

        if not items:
            self._hide_suggestions()
            return

        # Position below entry
        x = self.city_entry.winfo_rootx() - self.winfo_rootx()
        y = (
            self.city_entry.winfo_rooty()
            - self.winfo_rooty()
            + self.city_entry.winfo_height()
        )
        self.suggestions_box.place(x=x, y=y, width=self.city_entry.winfo_width())
        self.suggestions_visible = True

    def _hide_suggestions(self):
        if self.suggestions_visible:
            self.suggestions_box.place_forget()
            self.suggestions_visible = False

    def _on_suggestion_select(self, event=None):
        sel = self.suggestions_box.curselection()
        if sel:
            value = self.suggestions_box.get(sel[0])
            self.city_var.set(value)
            self._hide_suggestions()
            self.fetch_weather()

    def _on_suggestion_click(self, event=None):
        self._on_suggestion_select()

    def _navigate_suggestions(self, event=None):
        """Handle Up/Down arrow navigation in suggestions."""
        if not self.suggestions_visible:
            return
        current = self.suggestions_box.curselection()
        if event.keysym == "Up":
            new_index = (current[0] - 1) % self.suggestions_box.size() if current else 0
        elif event.keysym == "Down":
            new_index = (current[0] + 1) % self.suggestions_box.size() if current else 0
        self.suggestions_box.selection_clear(0, tk.END)
        self.suggestions_box.selection_set(new_index)
        self.suggestions_box.activate(new_index)
        self.suggestions_box.see(new_index)

    def fetch_forecast(self):
        """Fetch 5-day forecast for the current city."""
        city = self.city_var.get().strip()
        if not city:
            self.status_var.set("Please enter a city name first.")
            return
        api_key = load_api_key()
        if not api_key:
            messagebox.showerror("Missing API Key", "API key required.")
            return

        self.status_var.set("Fetching forecast…")
        self.forecast_btn.configure(state=tk.DISABLED)

        def worker():
            try:
                params = {"q": city, "appid": api_key, "units": "metric"}
                resp = requests.get(
                    "https://api.openweathermap.org/data/2.5/forecast",
                    params=params,
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if resp.status_code != 200 or str(data.get("cod")) != "200":
                    raise ValueError("Forecast not available.")

                # Parse forecast (next 5 days, every 3 hours, take daily max)
                forecast = {}
                for item in data.get("list", []):
                    dt = item["dt_txt"][:10]  # YYYY-MM-DD
                    temp = item["main"]["temp"]
                    if dt not in forecast or temp > forecast[dt]:
                        forecast[dt] = temp

                forecast_text = "\n".join(
                    [f"{k}: {v:.1f}°C" for k, v in list(forecast.items())[:5]]
                )
                self.after(
                    0, lambda: messagebox.showinfo("5-Day Forecast", forecast_text)
                )

            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Forecast Error", error_msg))
            finally:
                self.after(0, lambda: self.forecast_btn.configure(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def fetch_weather(self):
        """Start a background thread to call the API so UI stays responsive."""
        self._hide_suggestions()  # Hide autocomplete suggestions
        city = self.city_var.get().strip()
        if not city:
            self.status_var.set("Please enter a city name.")
            return
        api_key = load_api_key()
        if not api_key:
            messagebox.showerror(
                "Missing API Key",
                "Set environment variable OWM_API_KEY or create a .env file with OWM_API_KEY=your_key",
            )
            return

        self.status_var.set("Fetching weather…")
        self.fetch_btn.configure(state=tk.DISABLED)
        self.progress.grid()  # Show progress bar
        self.progress.start()

        unit = "metric" if self.unit_var.get() == "C" else "imperial"

        def worker():
            try:
                params = {"q": city, "appid": api_key, "units": unit}
                resp = requests.get(API_URL, params=params, timeout=10)
                data = resp.json()
                if resp.status_code != 200 or str(data.get("cod")) != "200":
                    msg = data.get("message", "Unable to fetch weather data.")
                    raise ValueError(f"API error: {msg}")

                # Extract fields
                main = data.get("main", {})
                weather_list = data.get("weather", [])
                wind = data.get("wind", {})
                condition = weather_list[0] if weather_list else {}
                temp_c = main.get("temp")
                feels_like = main.get("feels_like")
                humidity = main.get("humidity")
                wind_speed = wind.get("speed", 0)
                cond_main = condition.get("main", "")
                cond_desc = condition.get("description", "").title()
                icon = condition.get("icon", "")

                # Download icon
                icon_img = None
                if icon:
                    try:
                        icon_url = ICON_URL.format(icon=icon)
                        ic_resp = requests.get(icon_url, timeout=10)
                        ic_resp.raise_for_status()
                        icon_img = Image.open(io.BytesIO(ic_resp.content))
                    except Exception:
                        pass

                # Update UI
                def update_ui():
                    temp_symbol = "°C" if unit == "metric" else "°F"
                    wind_symbol = "km/h" if unit == "metric" else "mph"
                    self.temp_var.set(
                        f"{temp_c:.1f} {temp_symbol}"
                        if isinstance(temp_c, (int, float))
                        else f"— {temp_symbol}"
                    )
                    self.cond_var.set(cond_desc or cond_main or "—")
                    self.details_var.set(
                        f"Humidity: {humidity}% | Wind: {wind_speed:.1f} {wind_symbol} | Feels like: {feels_like:.1f} {temp_symbol}"
                        if humidity and wind_speed and feels_like
                        else f"Humidity: —% | Wind: — {wind_symbol} | Feels like: — {temp_symbol}"
                    )
                    self.update_theme(cond_main or cond_desc)
                    if icon_img:
                        resized = icon_img.resize((120, 120), Image.LANCZOS)
                        self._icon_photo = ImageTk.PhotoImage(resized)
                        self.icon_lbl.configure(image=self._icon_photo)
                    else:
                        self.icon_lbl.configure(image="")
                    self.status_var.set(f"Updated for {city}")
                    self.progress.stop()
                    self.progress.grid_remove()
                    self.fetch_btn.configure(state=tk.NORMAL)

                self.after(0, update_ui)

            except ValueError as ve:
                error_msg = str(ve)

                def show_err():
                    self.status_var.set(error_msg)
                    messagebox.showerror("City Error", error_msg)
                    self.progress.stop()
                    self.progress.grid_remove()
                    self.fetch_btn.configure(state=tk.NORMAL)

                self.after(0, show_err)

            except requests.RequestException as re:
                error_msg = str(re)

                def show_net():
                    self.status_var.set("Network error — check internet and try again.")
                    messagebox.showerror("Network Error", error_msg)
                    self.progress.stop()
                    self.progress.grid_remove()
                    self.fetch_btn.configure(state=tk.NORMAL)

                self.after(0, show_net)

            except Exception as e:
                error_msg = str(e)

                def show_generic():
                    self.status_var.set("Unexpected error occurred.")
                    messagebox.showerror("Error", error_msg)
                    self.progress.stop()
                    self.progress.grid_remove()
                    self.fetch_btn.configure(state=tk.NORMAL)

                self.after(0, show_generic)

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = WeatherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
