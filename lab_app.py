from flask import Flask, request, render_template, Response
from functools import wraps
import time
import datetime
import sqlite3
import paho.mqtt.client as mqtt
import logging
from config import Config

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurazione dell'app Flask
app = Flask(__name__)
app.config.from_object(Config)
app.debug = Config.DEBUG

# Funzione per connettersi e pubblicare il messaggio MQTT
def send_mqtt_message(message):
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(Config.MQTT_BROKER, Config.MQTT_PORT)
        mqtt_client.publish(Config.MQTT_TOPIC_RELAY, message)
        mqtt_client.disconnect()
        logger.info(f"MQTT message sent: {message}")
    except Exception as e:
        logger.error(f"Failed to send MQTT message: {e}")
        raise

# AUTENTICAZIONE HTTP BASIC per le route di controllo del relay
# Le credenziali si configurano tramite le variabili d'ambiente
# AUTH_USERNAME / AUTH_PASSWORD (vedi README.md / .env.example).
def check_auth(username, password):
    """Verifica le credenziali rispetto a quelle configurate via env.
    Se non sono configurate, nega sempre l'accesso (fail closed)."""
    expected_user = Config.AUTH_USERNAME
    expected_pass = Config.AUTH_PASSWORD
    if not expected_user or not expected_pass:
        logger.warning("AUTH_USERNAME/AUTH_PASSWORD non configurate: accesso negato")
        return False
    return username == expected_user and password == expected_pass

def authenticate():
    return Response(
        "Accesso non autorizzato: credenziali richieste per controllare il relay.",
        401,
        {'WWW-Authenticate': 'Basic realm="Lab App - Relay Control"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# T1 CONTROL
T1_status = "OFF"  # Stato iniziale del relay

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/T1_on/", methods=['POST'])
@requires_auth
def T1_on():
    global T1_status
    send_mqtt_message("ON")  # Pubblica il comando MQTT
    T1_status = "ON"
    return render_template('index.html', T1_status=T1_status)

@app.route("/T1_off/", methods=['POST'])
@requires_auth
def T1_off():
    global T1_status
    send_mqtt_message("OFF")  # Pubblica il comando MQTT
    T1_status = "OFF"
    return render_template('index.html', T1_status=T1_status)

# Rotta per visualizzare le foto del laboratorio
@app.route("/lab_photos")
def lab_photos():
    return render_template('lab_photos.html')

# Rotta per visualizzare i dati di temperatura e umidità dal database
@app.route("/lab_temp")
def lab_temp():
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        curs = conn.cursor()
        curs.execute("SELECT temp, hum FROM temphum ORDER BY datetime DESC LIMIT 1")
        result_tuple = curs.fetchall()
        conn.close()

        if result_tuple:
            temperature = result_tuple[0][0]
            humidity = result_tuple[0][1]

            if humidity is not None and temperature is not None:
                return render_template("lab_temp.html", temp=temperature, hum=humidity)

        return render_template("no_sensor.html")
    except Exception as e:
        logger.error(f"Error reading temperature data: {e}")
        return render_template("no_sensor.html")

# Rotta per filtrare e mostrare i dati del database
@app.route("/lab_env_db", methods=['GET'])
def lab_env_db():
    temp_result_tuple, hum_result_tuple, from_date_str, to_date_str = get_records()
    return render_template("lab_env_db.html", temp=temp_result_tuple, hum=hum_result_tuple, from_date=from_date_str,
                           to_date=to_date_str, temp_items=len(temp_result_tuple), hum_items=len(hum_result_tuple))

# Funzione per recuperare i record dal database
def get_records():
    from_date_str = request.args.get('from', time.strftime("%Y-%m-%d 00:00"))
    to_date_str = request.args.get('to', time.strftime("%Y-%m-%d %H:%M"))
    range_h_form = request.args.get('range_h', '')  # Questo restituirà una stringa se il campo range_h esiste nella richiesta

    range_h_int = "nan"  # Inizializza questa variabile con "not a number"

    try:
        range_h_int = int(range_h_form)
    except ValueError:
        print("range_h_form non è un numero")

    if not validate_date(from_date_str):  # Valida la data prima di inviarla al database
        from_date_str = time.strftime("%Y-%m-%d 00:00")
    if not validate_date(to_date_str):
        to_date_str = time.strftime("%Y-%m-%d %H:%M")  # Valida la data prima di inviarla al database

    # Se range_h è definito, sovrascrive i valori di from_date e to_date
    if isinstance(range_h_int, int):
        time_now = datetime.datetime.now()
        time_from = time_now - datetime.timedelta(hours=range_h_int)
        time_to = time_now
        from_date_str = time_from.strftime("%Y-%m-%d %H:%M")
        to_date_str = time_to.strftime("%Y-%m-%d %H:%M")

    try:
        conn = sqlite3.connect(Config.DB_PATH)
        curs = conn.cursor()
        curs.execute("SELECT datetime, temp FROM temphum WHERE datetime BETWEEN ? AND ?", (from_date_str, to_date_str))
        temp_result_tuple = curs.fetchall()
        curs.execute("SELECT datetime, hum FROM temphum WHERE datetime BETWEEN ? AND ?", (from_date_str, to_date_str))
        hum_result_tuple = curs.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        temp_result_tuple = []
        hum_result_tuple = []

    return [temp_result_tuple, hum_result_tuple, from_date_str, to_date_str]

# Funzione per validare il formato della data
def validate_date(d):
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M')
        return True
    except ValueError:
        return False



# uWSGI to start the application


