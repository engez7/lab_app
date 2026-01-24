import paho.mqtt.client as mqtt
import sqlite3
import time
import logging
from config import Config

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log_values(sensor_id, temp, hum):
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        curs = conn.cursor()
        # Elimina i record con data precedente a retention days configurato
        curs.execute(f"DELETE FROM temphum WHERE datetime < datetime('now', '-{Config.DATA_RETENTION_DAYS} days')")
        # Inserisci nuovo record
        curs.execute("INSERT INTO temphum VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), (?), (?), (?))", (sensor_id, temp, hum))
        conn.commit()
        conn.close()
        logger.info(f"Logged values - Temp: {temp}, Hum: {hum}")
    except Exception as e:
        logger.error(f"Failed to log values to database: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to broker {Config.MQTT_BROKER}")
        # Sottoscrivi al topic
        client.subscribe(Config.MQTT_TOPIC_TEMPHUM.encode(), qos=1)
    else:
        logger.error(f"Connection to broker failed with code {rc}")

def on_message(client, userdata, msg):
    if msg.topic == Config.MQTT_TOPIC_TEMPHUM:
        try:
            logger.info(f"{msg.topic} {msg.payload}")

            values = msg.payload.decode().split(",")
            if len(values) != 2:
                logger.error(f"Invalid payload format: {msg.payload}")
                return

            temperature = float(values[0])
            humidity = float(values[1])
            logger.info(f"{temperature:.2f},{humidity:.2f}")
            log_values("DHT_01", temperature, humidity)

            # Wait before return to listening status
            time.sleep(Config.MQTT_SLEEP_INTERVAL)
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

client = mqtt.Client("python_pahoMQTT_lab_app")
client.on_connect = on_connect
client.on_message = on_message

logger.info(f"Connecting to broker {Config.MQTT_BROKER}")
client.connect(Config.MQTT_BROKER)

# Esegui il loop fino a quando il programma si chiude
client.loop_forever()

