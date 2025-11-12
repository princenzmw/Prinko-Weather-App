# Prinko Weather App

A clean, beginner-friendly **Python desktop weather app** built with **Tkinter**, using the **OpenWeatherMap** API to show the current **temperature (°C)**, **condition**, and the official **weather icon** for any city.

## ✨ Features
- Text field to enter city name
- Displays **temperature in °C**, **condition** (e.g., Cloudy), and an **icon**
- **Error messages** for invalid city / network issues
- **Background color changes** by weather: Clear → yellow, Clouds → gray, Rain/Drizzle/Thunder → blue
- **Centered, resizable window** using responsive grid
- Clear inline **comments** and a simple structure
- Uses **`requests`** for the API call and **Pillow** (`PIL`) to load the icon

## 📦 Requirements
- Python **3.9+**
- Packages: `requests`, `Pillow`

Install:
```bash
pip install -r requirements.txt
```

## 🔑 OpenWeatherMap API Key
1. Create a free account at https://openweathermap.org/api
2. Find your API key in your profile (may take a few minutes after signup).
3. Provide the key to the app **either** by:
   - Setting the environment variable `OWM_API_KEY`, **or**
   - Creating a file named `.env` next to `app.py` with the line:
     ```
     OWM_API_KEY=your_key_here
     ```

> The app reads `OWM_API_KEY` from the environment first; if missing, it tries `.env` in the project folder.

## ▶️ Run the App
```bash
python app.py
```
Then type a city (e.g., `Nairobi`) and press **Enter** or click **Get Weather**.

## 🧪 Try these endpoints
Internally the app calls:
```
GET https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric
```
It also downloads the icon from:
```
https://openweathermap.org/img/wn/{icon}@2x.png
```

## 🖼 UI Behavior
- **Sunny / Clear** → background becomes **soft yellow**
- **Cloudy** → **light gray**
- **Rain / Drizzle / Thunderstorm** → **light blue**
- Layout stays **centered** and the window is **resizable**.

## 🛡 Error Handling
- Invalid cities: shows a dialog with the API message (e.g., *city not found*)
- Network/timeout: shows a dialog and status message
- Unknown exceptions are caught and displayed

## 🧰 Project Structure
```
.
├─ app.py              # Tkinter app (all-in-one, documented)
├─ requirements.txt    # requests, Pillow
├─ .env.example        # sample env file (copy to .env)
└─ README.md
```

## ⚙️ Configuration
- **Env var**: `OWM_API_KEY` (required)
- Optional: `.env` file if you prefer not to set an environment variable globally

## 📝 Notes
- Free OpenWeatherMap accounts are rate limited; if the API returns an error, try again in a bit.
- Icons are fetched live and cached in-memory for the current view only.

## 🗒 License
MIT — use freely for learning and demos.