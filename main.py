#!/usr/bin/env python3
import requests
import time
import os
import sys
import math
from datetime import datetime
from collections import deque, Counter

# --- CONFIGURATION ---
MATRIX_ROWS, MATRIX_COLS = 64, 64
FONT_PATH = "fonts/4x6.bdf" 
BRIGHTNESS = 50         # 0 to 100 percent
PAGE_TIME = 10         
FETCH_INTERVAL = 60
SUMMARY_TIME = 10 
WIPE_TIME = 0.5

# Night Mode Hours (24h format)
NIGHT_START = 23 # 11 PM
NIGHT_END = 7    # 7 AM

# London Bridge Reference
HOME_LAT, HOME_LON = 51.5079, -0.0877
OPENSKY_URL = "https://opensky-network.org/api/states/all?lamin=51.35&lomin=-0.35&lamax=51.65&lomax=0.15"

CAT_MAP = {1: "LIGHT", 2: "SMALL", 3: "LARGE", 4: "HI VORTEX", 5: "HEAVY", 
           6: "HI PERF", 7: "ROTORCRAFT", 8: "GLIDER", 9: "LT-AIR", 10: "DRONE", 11: "SPACE"}

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
    options.rows, options.cols = MATRIX_ROWS, MATRIX_COLS
    options.brightness = BRIGHTNESS
    if is_pi:
        options.hardware_mapping, options.gpio_slowdown = 'adafruit-hat-pwm', 2
    matrix = RGBMatrix(options=options)
    font = graphics.Font()
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    font.LoadFont(os.path.join(curr_dir, FONT_PATH))

def is_night():
    """Checks if current time is within Night Mode hours."""
    now = datetime.now().hour
    if NIGHT_START > NIGHT_END:
        return now >= NIGHT_START or now < NIGHT_END
    return NIGHT_START <= now < NIGHT_END

def radar_wipe():
    if is_night(): return
    cx, cy = 32, 32
    green = graphics.Color(0, 255, 0)
    steps = 30
    delay = 0.016 
    
    for i in range(steps + 1):
        canvas = matrix.CreateFrameCanvas()
        angle = (i * (360 / steps))
        rad = math.radians(angle)
        ex, ey = int(cx + 45 * math.cos(rad)), int(cy + 45 * math.sin(rad))
        graphics.DrawLine(canvas, cx, cy, ex, ey, green)
        matrix.SwapOnVSync(canvas)
        time.sleep(delay)

def calculate_distance(p_lat, p_lon):
    if p_lat is None or p_lon is None: return 0
    R = 6371 
    dlat = math.radians(p_lat - HOME_LAT)
    dlon = math.radians(p_lon - HOME_LON)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(HOME_LAT)) * math.cos(math.radians(p_lat)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def draw_summary(states):
    if is_night(): return
    canvas = matrix.CreateFrameCanvas()
    c_gold, c_white, c_green, c_cyan = (graphics.Color(255, 215, 0), graphics.Color(255, 255, 255), 
                                       graphics.Color(0, 255, 0), graphics.Color(0, 255, 255))
    
    origins = [s[2] for s in states if s[2]]
    top_origins = Counter(origins).most_common(3)

    graphics.DrawText(canvas, font, 2, 10, c_gold, "AREA SUMMARY")
    graphics.DrawText(canvas, font, 2, 18, c_white, "-------------")
    graphics.DrawText(canvas, font, 2, 28, c_green, f"TOTAL: {len(states)}")
    
    y_pos = 40
    for country, count in top_origins:
        short_name = (country[:10] + "..") if len(country) > 10 else country
        graphics.DrawText(canvas, font, 2, y_pos, c_cyan, f"{short_name.upper()}: {count}")
        y_pos += 10

    matrix.SwapOnVSync(canvas)
    time.sleep(SUMMARY_TIME)

def draw_page(plane, page_num):
    if is_night(): return
    canvas = matrix.CreateFrameCanvas()
    callsign = (plane[1] or "N/A").strip()
    icao = (plane[0] or "N/A").upper()
    origin = (plane[2] or "Unknown").strip()
    on_ground = plane[8]
    cat_id = plane[17] if len(plane) > 17 else 0
    type_disp = f"TYP: {CAT_MAP[cat_id]}" if cat_id in CAT_MAP else f"ORG: {origin[:12].upper()}"
    
    c_cyan, c_white, c_gold, c_green, c_red = (graphics.Color(0, 255, 255), graphics.Color(255, 255, 255),
                                             graphics.Color(255, 215, 0), graphics.Color(0, 255, 0), graphics.Color(255, 0, 0))

    if page_num == 1:
        graphics.DrawText(canvas, font, 2, 10, c_cyan,  f"CALL: {callsign}")
        graphics.DrawText(canvas, font, 2, 21, c_white, f"ICAO: {icao}")
        graphics.DrawText(canvas, font, 2, 32, c_green, type_disp)
        status_text = "GROUND" if on_ground else "AIRBORNE"
        status_color = c_red if on_ground else c_cyan
        graphics.DrawText(canvas, font, 2, 43, status_color, f"STAT: {status_text}")
        graphics.DrawText(canvas, font, 2, 60, c_gold, "INFO 1/2")
    else:
        alt_ft, speed_kt, v_rate_fpm, dist_km = int((plane[7] or 0) * 3.28084), int((plane[9] or 0) * 1.94384), int((plane[11] or 0) * 196.85), calculate_distance(plane[6], plane[5])
        squawk = plane[14] or "----"
        graphics.DrawText(canvas, font, 2, 10, c_white, f"ALT: {alt_ft} FT")
        graphics.DrawText(canvas, font, 2, 20, c_white, f"SPD: {speed_kt} KT")
        graphics.DrawText(canvas, font, 2, 30, c_cyan,  f"DST: {dist_km:.1f} KM")
        v_label = "CLB" if v_rate_fpm > 100 else "DES" if v_rate_fpm < -100 else "LVL"
        graphics.DrawText(canvas, font, 2, 40, c_green, f"VRT: {v_label} {abs(v_rate_fpm)}")
        graphics.DrawText(canvas, font, 2, 50, c_white, f"SQW: {squawk}")
        graphics.DrawText(canvas, font, 2, 60, c_gold, "DATA 2/2")

    matrix.SwapOnVSync(canvas)
    time.sleep(PAGE_TIME)

def main():
    setup_matrix()
    flight_queue = deque()
    last_fetch = 0

    try:
        while True:
            if is_night():
                matrix.Clear()
                print(f"[{datetime.now().strftime('%H:%M')}] Night Mode Active.")
                time.sleep(60)
                continue

            if time.time() - last_fetch > FETCH_INTERVAL:
                try:
                    r = requests.get(OPENSKY_URL, timeout=10)
                    states = r.json().get('states', [])
                    if states:
                        states.sort(key=lambda p: calculate_distance(p[6], p[5]))
                        flight_queue = deque(states)
                        last_fetch = time.time()
                        radar_wipe()
                        draw_summary(states)
                except: pass

            if flight_queue:
                current_plane = flight_queue.popleft()
                radar_wipe()
                draw_page(current_plane, 1)
                draw_page(current_plane, 2)
                flight_queue.append(current_plane)
            else:
                time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()