from flask import Flask, request, render_template
import time
import datetime
import sqlite3
import paho.mqtt.client as mqtt
import threading

# Initialize the Flask application
app = Flask(__name__)
app.debug = True  # Set to False if you're not debugging

# MQTT Configuration
MQTT_BROKER = "localhost"  # MQTT Broker address (localhost in this case)
MQTT_PORT = 1883  # Default MQTT port
MQTT_TOPIC_RELAY = "esp/relay/thermo_z01"  # Topic for controlling the relay

# Create an MQTT client instance
mqtt_client = mqtt.Client()

# This function is called when the MQTT client successfully connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to MQTT broker!")
    else:
        print(f"MQTT connection error. Code: {rc}")

# This function is called when the MQTT client disconnects from the broker
def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT broker. Attempting reconnection...")
    while True:
        try:
            client.reconnect()
            print("Reconnection successful!")
            break
        except Exception as e:
            print(f"Reconnection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Assign the on_connect and on_disconnect callbacks to the MQTT client
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

# Connect to the MQTT broker with a keepalive of 48 hours
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=172800)  # 48 hours keepalive

# Function to start the MQTT client loop in a separate thread
def start_mqtt_loop():
    mqtt_client.loop_start()  # loop_start allows Flask to run in parallel with MQTT

# Start the MQTT loop in a background thread
threading.Thread(target=start_mqtt_loop, daemon=True).start()

# Flask route to display the main page
@app.route("/")
def index():
    return render_template('index.html')

# Initial state of the relay
T1_status = "OFF"

# Route to turn the relay on
@app.route("/T1_on/", methods=['POST'])
def T1_on():
    global T1_status
    mqtt_client.publish(MQTT_TOPIC_RELAY, "ON")  # Publish "ON" message to the relay topic
    T1_status = "ON"  # Update relay status
    return render_template('index.html', T1_status=T1_status)

# Route to turn the relay off
@app.route("/T1_off/", methods=['POST'])
def T1_off():
    global T1_status
    mqtt_client.publish(MQTT_TOPIC_RELAY, "OFF")  # Publish "OFF" message to the relay topic
    T1_status = "OFF"  # Update relay status
    return render_template('index.html', T1_status=T1_status)

# Route to display lab photos (example route, could be adjusted as needed)
@app.route("/lab_photos")
def lab_photos():
    return render_template('lab_photos.html')

# Route to display the latest temperature and humidity data from the database
@app.route("/lab_temp")
def lab_temp():
    conn = sqlite3.connect('/var/www/lab_app/lab_app.db')  # Connect to the SQLite database
    curs = conn.cursor()
    curs.execute("SELECT temp, hum FROM temphum ORDER BY datetime DESC LIMIT 1")  # Query the latest data
    result_tuple = curs.fetchall()
    conn.close()

    # If data exists, render the template with the latest temperature and humidity
    if result_tuple:
        temperature = result_tuple[0][0]
        humidity = result_tuple[0][1]
        if humidity is not None and temperature is not None:
            return render_template("lab_temp.html", temp=temperature, hum=humidity)

    # If no data is found, render a no data page
    return render_template("no_data.html")

# Route to show data from the temperature and humidity database (with filters)
@app.route("/lab_env_db", methods=['GET'])
def lab_env_db():
    temp_result_tuple, hum_result_tuple, from_date_str, to_date_str = get_records()  # Get filtered data
    return render_template("lab_env_db.html", temp=temp_result_tuple, hum=hum_result_tuple,
                           from_date=from_date_str, to_date=to_date_str,
                           temp_items=len(temp_result_tuple), hum_items=len(hum_result_tuple))

# Function to retrieve records based on query parameters (e.g., date range)
def get_records():
    from_date_str = request.args.get('from', time.strftime("%Y-%m-%d 00:00"))  # Default from date
    to_date_str = request.args.get('to', time.strftime("%Y-%m-%d %H:%M"))  # Default to date
    range_h_form = request.args.get('range_h', '')  # Range in hours parameter

    range_h_int = "nan"
    try:
        range_h_int = int(range_h_form)
    except ValueError:
        print("range_h_form is not a valid number")

    # If the date format is invalid, use the default dates
    if not validate_date(from_date_str):
        from_date_str = time.strftime("%Y-%m-%d 00:00")
    if not validate_date(to_date_str):
        to_date_str = time.strftime("%Y-%m-%d %H:%M")

    # If range_h_int is provided, use it to filter data for the last 'n' hours
    if isinstance(range_h_int, int):
        time_now = datetime.datetime.now()
        time_from = time_now - datetime.timedelta(hours=range_h_int)
        time_to = time_now
        from_date_str = time_from.strftime("%Y-%m-%d %H:%M")
        to_date_str = time_to.strftime("%Y-%m-%d %H:%M")

    # Query the database for temperature and humidity data within the specified date range
    conn = sqlite3.connect('/var/www/lab_app/lab_app.db')
    curs = conn.cursor()
    curs.execute("SELECT datetime, temp FROM temphum WHERE datetime BETWEEN ? AND ?", (from_date_str, to_date_str))
    temp_result_tuple = curs.fetchall()
    curs.execute("SELECT datetime, hum FROM temphum WHERE datetime BETWEEN ? AND ?", (from_date_str, to_date_str))
    hum_result_tuple = curs.fetchall()
    conn.close()

    return [temp_result_tuple, hum_result_tuple, from_date_str, to_date_str]

# Helper function to validate the date format
def validate_date(d):
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M')
        return True
    except ValueError:
        return False

# uWSGI to start the application


