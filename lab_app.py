from flask import Flask, request, render_template
import time
import datetime
import sqlite3
import paho.mqtt.client as mqtt
import threading

# Initialize Flask app
app = Flask(__name__)
app.debug = True  # Debug mode

# MQTT Configuration
MQTT_BROKER = "localhost"  # Broker MQTT (localhost in questo caso)
MQTT_PORT = 1883  # Porta MQTT
MQTT_TOPIC_RELAY = "esp/relay/thermo_z01"  # Topic per il relay

# Crea un'istanza del client MQTT
mqtt_client = mqtt.Client()

# Callback quando il client si connette al broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connesso al broker MQTT con successo!")
        client.subscribe(MQTT_TOPIC_RELAY)  # Assicurati di risottoscrivere il topic
    else:
        print(f"Errore di connessione MQTT. Codice: {rc}")

# Callback quando il client si disconnette
def on_disconnect(client, userdata, rc):
    print(f"Disconnesso dal broker MQTT (codice: {rc}). Tentativo di riconnessione...")
    while True:
        try:
            client.reconnect()
            print("Riconnessione al broker MQTT riuscita!")
            break
        except Exception as e:
            print(f"Errore di riconnessione: {e}. Riprovo tra 5 secondi...")
            time.sleep(5)

# Associazione delle callback al client MQTT
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

# Funzione per avviare il ciclo MQTT in un thread separato
def mqtt_loop():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        print("Avvio del loop MQTT...")
        while True:
            mqtt_client.loop(timeout=1.0)  # Gestione attiva della connessione
            mqtt_client.publish("esp/ping", "ping")  # Invia un ping periodico al broker
            time.sleep(10)  # Intervallo di ping (regolabile)
    except Exception as e:
        print(f"Errore nel ciclo MQTT: {e}")
        mqtt_client.disconnect()

# Avvia il ciclo MQTT in un thread separato
mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
mqtt_thread.start()

# Flask route per mostrare la pagina principale
@app.route("/")
def index():
    return render_template('index.html')

# Stato iniziale del relay
T1_status = "OFF"

# Rotta per accendere il relay
@app.route("/T1_on/", methods=['POST'])
def T1_on():
    global T1_status
    mqtt_client.publish(MQTT_TOPIC_RELAY, "ON")
    T1_status = "ON"
    return render_template('index.html', T1_status=T1_status)

# Rotta per spegnere il relay
@app.route("/T1_off/", methods=['POST'])
def T1_off():
    global T1_status
    mqtt_client.publish(MQTT_TOPIC_RELAY, "OFF")
    T1_status = "OFF"
    return render_template('index.html', T1_status=T1_status)

# Rotta per mostrare foto del laboratorio
@app.route("/lab_photos")
def lab_photos():
    return render_template('lab_photos.html')

# Rotta per mostrare gli ultimi dati di temperatura e umidità
@app.route("/lab_temp")
def lab_temp():
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

    return render_template("no_data.html")

# Rotta per mostrare i dati filtrati dal database
@app.route("/lab_env_db", methods=['GET'])
def lab_env_db():
    temp_result_tuple, hum_result_tuple, from_date_str, to_date_str = get_records()
    return render_template("lab_env_db.html", temp=temp_result_tuple, hum=hum_result_tuple,
                           from_date=from_date_str, to_date=to_date_str,
                           temp_items=len(temp_result_tuple), hum_items=len(hum_result_tuple))

# Funzione per ottenere i record dal database in base ai filtri
def get_records():
    from_date_str = request.args.get('from', time.strftime("%Y-%m-%d 00:00"))
    to_date_str = request.args.get('to', time.strftime("%Y-%m-%d %H:%M"))
    range_h_form = request.args.get('range_h', '')

    range_h_int = "nan"
    try:
        range_h_int = int(range_h_form)
    except ValueError:
        print("range_h_form non è un numero valido")

    if not validate_date(from_date_str):
        from_date_str = time.strftime("%Y-%m-%d 00:00")
    if not validate_date(to_date_str):
        to_date_str = time.strftime("%Y-%m-%d %H:%M")

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

# Helper per validare il formato della data
def validate_date(d):
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M')
        return True
    except ValueError:
        return False

# uWSGI to start the application


