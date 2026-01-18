#!/usr/bin/env python3

import requests
import time
import os
import sys

# --- LED Matrix Setup ---
# This block will only run on a Raspberry Pi with the rpi-rgb-led-matrix library installed.
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    is_pi = True
except ImportError:
    is_pi = False
    # Mock classes for local development
    class MockRGBMatrix:
        def Clear(self):
            print("--- Mock Matrix Cleared ---")

    class MockRGBMatrixOptions: pass
    
    class MockFont:
        def LoadFont(self, path):
            print(f"--- Mock Font Loaded: {path} ---")

    class MockGraphics:
        def __init__(self):
            self.font = MockFont()

        def Font(self):
            return self.font

        def Color(self, r, g, b):
            return (r, g, b)

        def DrawText(self, matrix, font, x, y, color, text):
            print(f"--- Drawing on Mock Matrix ---\n{text}\n--------------------------")

    RGBMatrix = MockRGBMatrix
    RGBMatrixOptions = MockRGBMatrixOptions
    graphics = MockGraphics()


# --- Matrix Configuration ---
MATRIX_ROWS = 64
MATRIX_COLS = 64
FONT_PATH = "fonts/4x6.bdf" # Path relative to the script
TEXT_COLOR = (255, 255, 255) # White

# Global matrix and font objects
matrix = None
font = None

def setup_matrix():
    """Initializes the LED matrix if running on a Pi."""
    global matrix, font
    if not is_pi:
        print("Not a Raspberry Pi. Using console output for display.")
        # In non-Pi environment, graphics.Font() returns a mock object
        font = graphics.Font()
        font.LoadFont(FONT_PATH) # Simulate loading font
        matrix = RGBMatrix() # This will be our mock matrix
        return

    print("Setting up LED matrix on Raspberry Pi...")
    options = RGBMatrixOptions()
    options.rows = MATRIX_ROWS
    options.cols = MATRIX_COLS
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat-pwm'  # Use 'adafruit-hat' for original HAT
    
    # These settings can be fine-tuned for your specific 64x64 panel
    # options.pwm_bits = 11
    # options.pwm_lsb_nanoseconds = 130
    # options.brightness = 100
    # options.gpio_slowdown = 4

    matrix = RGBMatrix(options=options)
    
    font = graphics.Font()
    # The font path must be absolute for the C++ library
    font_abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), FONT_PATH)
    font.LoadFont(font_abs_path)
    
    print("Matrix setup complete.")


def draw_text_on_matrix(text):
    """
    Draws the given text on the LED matrix.
    If not on a Pi, it prints the text to the console via the mock objects.
    """
    if matrix is None or font is None:
        print("Matrix not initialized.")
        return

    if not is_pi:
        # Our mock DrawText will handle the console output
        graphics.DrawText(matrix, font, 0, 0, TEXT_COLOR, text)
        return

    # When on the Pi, use the real matrix object
    matrix.Clear()
    lines = text.split('\n')
    y_pos = 6  # Start y-position for the first line (font height is 6)
    white_color = graphics.Color(*TEXT_COLOR)

    for line in lines:
        graphics.DrawText(matrix, font, 1, y_pos, white_color, line)
        y_pos += 7 # Move to the next line (6px font height + 1px spacing)

# --- Configuration for OpenSky --
# The values below are for a box around London, UK.
LAT_MIN = 51.2868
LAT_MAX = 51.6918
LON_MIN = -0.5103
LON_MAX = 0.3340

OPENSKY_API_URL = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lomin={LON_MIN}&lamax={LAT_MAX}&lomax={LON_MAX}"


# --- Data Fetching ---
def get_flight_data(api_url):
    """Fetches flight data from the OpenSky Network API."""
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('states', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

# --- Main Logic ---
def main():
    """Main loop to fetch data and display it."""
    setup_matrix()
    print("Airplane display script started.")

    try:
        while True:
            print("Fetching flight data...")
            flight_states = get_flight_data(OPENSKY_API_URL)

            display_text = ""
            if flight_states:
                # Filter flights and get the top ones (up to 9 for a 64x64 display with 4x6 font)
                top_flights = sorted(
                    [s for s in flight_states if s[1] and s[7]],
                    key=lambda x: x[7],
                    reverse=True
                )[:9]

                if top_flights:
                    for state in top_flights:
                        callsign = state[1].strip()[:7]  # Limit callsign length
                        altitude_m = state[7]
                        altitude_ft = int(altitude_m * 3.28084)
                        # Format to align text neatly on the display
                        display_text += f"{callsign:<7} {altitude_ft:>5}ft\n"
                else:
                    display_text = "\n\n  No flights in area"
            else:
                display_text = "\n\n      API Error"

            draw_text_on_matrix(display_text.strip())

            print("Waiting 60 seconds for next update...")
            time.sleep(60)

    except KeyboardInterrupt:
        print("\nExiting...")
        if is_pi and matrix:
            matrix.Clear() # Clear the matrix on exit
        sys.exit(0)

if __name__ == '__main__':
    main()
