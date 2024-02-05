import json
import os
import ssl
import time
import traceback

import adafruit_requests
import board
import busio
import microcontroller
import socketpool
import wifi
from adafruit_datetime import datetime
from adafruit_max1704x import MAX17048
from adafruit_scd4x import SCD4X
from adafruit_scd30 import SCD30
from adafruit_sgp30 import Adafruit_SGP30 as SGP30
# from adafruit_esp32s2tft import ESP32S2TFT

DEVICE_ID = os.getenv("DEVICE_ID")
SUPABASE_POST_URL = os.getenv("SUPABASE_POST_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# This controls how often your device sends data to the database
LOOP_TIME_S = 60

# esp32s2tft = ESP32S2TFT(default_bg=0xFFFF00, scale=2, use_network=False)

# Prepare to use the internet 💫
def initialize_wifi_connection():
    # This is inside a function so that we can call it later if we need to reestablish
    # the connection.
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
    )


initialize_wifi_connection()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())


def initialize_sensors():
    """Initialize connections to each possible sensor, if connected"""
    i2c = busio.I2C(board.SCL, board.SDA)
    
    try:
        co2_sensor = SCD4X(i2c)
        co2_sensor.start_periodic_measurement()
    except Exception:
        print("No CO2 sensor found")
        co2_sensor = None

    try:
        gas_sensor = SGP30(i2c)
        # gas_sensor.set_iaq_baseline(0x8973, 0x8AAE)
        # gas_sensor.set_iaq_relative_humidity(celsius=22.1, relative_humidity=44)
    except Exception:
        print("No gas sensor found")
        gas_sensor = None

    try:
        battery_sensor = MAX17048(i2c)
    except Exception:
        print("No battery sensor found")
        battery_sensor = None

    return co2_sensor, battery_sensor, gas_sensor


def post_to_db(sensor_data: dict):
    """Store sensor data in our supabase DB"""
    if not DEVICE_ID:
        raise Exception("Please set a unique device id!")

    print("Posting to DB")
    try:
        response = requests.post(
            url=SUPABASE_POST_URL,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            data=json.dumps(
                {
                    "device_id": DEVICE_ID,
                    "content": sensor_data,
                }
            ),
        )
    except socketpool.SocketPool.gaierror as e:
        print(f"ConnectionError: {e}. Restarting networking.")
        initialize_wifi_connection()
        # Attempt to store some diagnostic data about this error
        sensor_data.update(
            {"network_reset": True, "network_stacktrace": traceback.format_exception(e)}
        )
        print("Recursively retrying post with saved stacktrace.")
        response = post_to_db(sensor_data)

    # PostgREST only sends response to a POST when something is wrong
    error_details = response.content
    if error_details:
        print("Received response error code", error_details)
        print(response.headers)
        raise Exception(error_details)
    else:
        print("Post complete")


def collect_data( co2_sensor, battery_sensor, gas_sensor):
    """Get the latest data from the sensors, display it, and record it in the cloud."""
    # Python3 kwarg-style dict concatenation syntax doesn't seem to work in CircuitPython,
    # so we have to use mutation and update the dict as we go along
    all_sensor_data = {}

    if battery_sensor:
        all_sensor_data.update(
            {
                "battery_v": battery_sensor.cell_voltage,
                "battery_pct": battery_sensor.cell_percent,
            }
        )

    if co2_sensor and co2_sensor.data_ready:
        all_sensor_data.update(
            {
                "co2_ppm": co2_sensor.CO2,
                "temperature_c": co2_sensor.temperature,
                "humidity_relative": co2_sensor.relative_humidity,
            }
        )

    if gas_sensor:
        all_sensor_data.update(
            {
                "eco2_ppm": gas_sensor.eCO2,
                "tvoc_ppb": gas_sensor.TVOC,
            }
        )

    print(all_sensor_data)
    post_to_db(all_sensor_data)


(
    co2_sensor,
    battery_sensor,
    gas_sensor
) = initialize_sensors()

# esp32s2tft.add_text(
#     text="ESP32-S2", text_position=(10, 10), text_scale=2, text_color=0xFF00FF
# )

while True:
    try:
        collect_data( co2_sensor, battery_sensor, gas_sensor)
    except (RuntimeError, OSError) as e:
        # Sometimes this is invalid PM2.5 checksum or timeout
        print(f"{type(e)}: {e}")
        if str(e) == "pystack exhausted":
            # This happens when our recursive retry logic fails.
            print("Unable to recover from an error. Rebooting in 10s.")
            time.sleep(10)
            microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
            microcontroller.reset()

    time.sleep(LOOP_TIME_S)
