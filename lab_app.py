from flask import Flask, request, render_template
import time
import datetime
import sqlite3
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.debug = True  # Set to False if you are no longer debugging

# Configurazione MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_RELAY = "esp/relay/thermo_z01"

mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

@app.route("/")
def index():
    return render_template('index.html')

# T1 CONTROL

T1_status = "OFF"  # Stato iniziale del relay

@app.route("/T1_on/", methods=['POST'])
def T1_on():
    global T1_status
    mqtt_client.publish(MQTT_TOPIC_RELAY, "ON")  # Pubblica il comando MQTT
    T1_status = "ON"
    return render_template('index.html', T1_status=T1_status)

@app.route("/T1_off/", methods=['POST'])
def T1_off():
    global T1_status
    mqtt_client.publish(MQTT_TOPIC_RELAY, "OFF")  # Pubblica il comando MQTT
    T1_status = "OFF"
    return render_template('index.html', T1_status=T1_status)

# SAME FOR T2 and PANEL... WIP!!!

@app.route("/lab_photos")
def lab_photos():
    return render_template('lab_photos.html')

@app.route("/lab_temp")
def lab_temp():
    # Retrieve values from the temphum table in lab_app.db...
    conn = sqlite3.connect('/var/www/lab_app/lab_app.db')
    curs = conn.cursor()
    curs.execute("SELECT temp, hum FROM temphum ORDER BY datetime DESC LIMIT 1")
    result_tuple = curs.fetchall()
    conn.close()

    if result_tuple:
        temperature = result_tuple[0][0]
        humidity = result_tuple[0][1]

        if humidity is not None and temperature is not None:
            return render_template("lab_temp.html", temp=temperature, hum=humidity)

    return render_template("no_data.html")  # Add no_data page

@app.route("/lab_env_db", methods=['GET'])  # Add date limits in the URL # Arguments: from=2015-03-04&to=2015-03-05
def lab_env_db():
    temp_result_tuple, hum_result_tuple, from_date_str, to_date_str = get_records()
    return render_template("lab_env_db.html", temp=temp_result_tuple, hum=hum_result_tuple, from_date=from_date_str,
                           to_date=to_date_str, temp_items=len(temp_result_tuple), hum_items=len(hum_result_tuple))

# Review this function... DB WITH UNIQUE TABLE temphum... OTHER??
def get_records():
    from_date_str = request.args.get('from', time.strftime("%Y-%m-%d 00:00"))
    to_date_str = request.args.get('to', time.strftime("%Y-%m-%d %H:%M"))
    range_h_form = request.args.get('range_h', '')  # This will return a string if field range_h exists in the request

    range_h_int = "nan"  # initialize this variable with not a number

    try:
        range_h_int = int(range_h_form)
    except ValueError:
        print("range_h_form not a number")

    if not validate_date(from_date_str):  # Validate date before sending it to the DB
        from_date_str = time.strftime("%Y-%m-%d 00:00")
    if not validate_date(to_date_str):
        to_date_str = time.strftime("%Y-%m-%d %H:%M")  # Validate date before sending it to the DB

    # If range_h is defined, we don't need the from and to times
    if isinstance(range_h_int, int):
        time_now = datetime.datetime.now()
        time_from = time_now - datetime.timedelta(hours=range_h_int)
        time_to = time_now
        from_date_str = time_from.strftime("%Y-%m-%d %H:%M")
        to_date_str = time_to.strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('/var/www/lab_app/lab_app.db')
    curs = conn.cursor()
    curs.execute("SELECT datetime, temp FROM temphum WHERE datetime BETWEEN ? AND ?", (from_date_str, to_date_str))
    temp_result_tuple = curs.fetchall()
    curs.execute("SELECT datetime, hum FROM temphum WHERE datetime BETWEEN ? AND ?", (from_date_str, to_date_str))
    hum_result_tuple = curs.fetchall()
    conn.close()

    return [temp_result_tuple, hum_result_tuple, from_date_str, to_date_str]

def validate_date(d):
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M')
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    mqtt_client.loop_start()            # Avvia il loop MQTT
    # TOLGO app.run() poiché uWSGI gestisce ascolto, non serve  attivare anche l'app...
    #app.run(host='0.0.0.0', port=8080)
