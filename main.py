#!/usr/bin/env python3
import requests
import time
import os
import sys
import math
from collections import deque

# --- 1. CONFIGURATION ---
MATRIX_ROWS = 64
MATRIX_COLS = 64
FONT_PATH = "fonts/4x6.bdf" 
STATIC_DISPLAY_TIME = 15 
FETCH_INTERVAL = 60
OPENSKY_URL = "https://opensky-network.org/api/states/all?lamin=51.28&lomin=-0.51&lamax=51.69&lomax=0.33"

# Update these to your actual location for accurate distance!
HOME_LAT = 51.5074 
HOME_LON = -0.1278

AIRLINE_MAP = {
    "BAW": "BRITISH AIR", "EZY": "EASYJET", "RYR": "RYANAIR",
    "AFR": "AIR FRANCE", "DLH": "LUFTHANSA", "UAE": "EMIRATES",
    "VIR": "VIRGIN ATL", "KLM": "KLM ROYAL", "VLG": "VUELING"
}

# --- 2. SETUP ---
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    is_pi = True
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
    is_pi = False

matrix = None
font = None

def setup_matrix():
    global matrix, font
    options = RGBMatrixOptions()
    options.rows = MATRIX_ROWS
    options.cols = MATRIX_COLS
    if is_pi:
        options.hardware_mapping = 'adafruit-hat-pwm'
        options.gpio_slowdown = 2
    matrix = RGBMatrix(options=options)
    font = graphics.Font()
    font_path = os.path.join(os.path.dirname(__file__), FONT_PATH)
    if os.path.exists(font_path):
        font.LoadFont(font_path)

def calculate_distance(p_lat, p_lon):
    """Haversine formula to calculate distance in km."""
    if not p_lat or not p_lon: return 0
    R = 6371 
    dlat = math.radians(p_lat - HOME_LAT)
    dlon = math.radians(p_lon - HOME_LON)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(HOME_LAT)) * math.cos(math.radians(p_lat)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def draw_static_frame(plane):
    # Data Mapping
    callsign = (plane[1] or "N/A").strip()
    icao24 = plane[0].upper()
    squawk = plane[14] or "----"
    
    # Identify Airline
    prefix = callsign[:3]
    airline = AIRLINE_MAP.get(prefix, "PRIVATE/OTHER")
    
    alt_ft = int((plane[7] or 0) * 3.28084)
    speed_kt = int((plane[9] or 0) * 1.94384)
    v_rate = int((plane[11] or 0) * 196.85)
    
    # Distance
    dist_km = calculate_distance(plane[6], plane[5])

    matrix.Clear()
    c_cyan = graphics.Color(0, 255, 255)
    c_white = graphics.Color(255, 255, 255)
    c_green = graphics.Color(0, 255, 0)
    c_red = graphics.Color(255, 50, 50)
    c_gold = graphics.Color(255, 215, 0)

    if font:
        # Layout: 7 lines of data, perfectly spaced
        graphics.DrawText(matrix, font, 2, 7, c_cyan, f"CALL: {callsign}")
        graphics.DrawText(matrix, font, 2, 15, c_green, f"AIRL: {airline}")
        graphics.DrawText(matrix, font, 2, 23, c_white, f"ALT : {alt_ft} FT")
        graphics.DrawText(matrix, font, 2, 31, c_white, f"SPD : {speed_kt} KT")
        
        # Vertical Rate with custom color
        v_color = c_red if v_rate < -500 else c_cyan if v_rate > 500 else c_white
        graphics.DrawText(matrix, font, 2, 39, v_color, f"VRT : {v_rate} FPM")
        
        graphics.DrawText(matrix, font, 2, 47, c_gold, f"DIST: {dist_km:.1f} KM")
        graphics.DrawText(matrix, font, 2, 55, c_white, f"SQWK: {squawk}")
        
        # Small Bottom Label
        graphics.DrawText(matrix, font, 2, 63, c_white, f"ICAO: {icao24}")

    # 30-second wait
    start_time = time.time()
    while time.time() - start_time < STATIC_DISPLAY_TIME:
        time.sleep(0.1)

def fetch_data():
    try:
        r = requests.get(OPENSKY_URL, timeout=10)
        return r.json().get('states', []) or []
    except:
        return []

def main():
    setup_matrix()
    flight_queue = deque(fetch_data())
    last_fetch = time.time()

    while True:
        if not flight_queue:
            flight_queue.extend(fetch_data())
            if not flight_queue:
                time.sleep(10)
                continue

        draw_static_frame(flight_queue.popleft())
        
        if time.time() - last_fetch > FETCH_INTERVAL:
            new_data = fetch_data()
            if new_data:
                flight_queue = deque(new_data)
                last_fetch = time.time()

if __name__ == "__main__":
    main()