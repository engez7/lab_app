import paho.mqtt.client as mqtt
import sqlite3
import time
#import sys

MQTT_SERVER = "192.168.1.254"
MQTT_TOPIC_TEMPHUM = b"esp/dht/TempHum_z01"

def log_values(sensor_id, temp, hum):
    conn = sqlite3.connect('/var/www/lab_app/lab_app.db')
    curs = conn.cursor()
    curs.execute("INSERT INTO temphum VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), (?), (?), (?))", (sensor_id, temp, hum))
    conn.commit()
    conn.close()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker ", MQTT_SERVER)
        # Sottoscrivi al topic
        client.subscribe(MQTT_TOPIC_TEMPHUM, qos=1)
    else:
        print("Connection to broker failed with code", rc)

def on_message(client, userdata, msg):
    if msg.topic == MQTT_TOPIC_TEMPHUM:
        print(msg.topic + " " + str(msg.payload))

        values = msg.payload.split(",")
        temperature = float(values[0])
        humidity = float(values[1])
        print("{:.2f}".format(temperature) + "," + "{:.2f}".format(humidity))
        log_values("DHT_01", temperature, humidity)

        # Wait 10 minutes before return to listening status
        time.sleep(60) #Testing with 1 min...
        
        # Chiudi il programma dopo aver gestito il messaggio
        #client.disconnect()
        #sys.exit()

client = mqtt.Client("python_pahoMQTT_lab_app")
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to broker ", MQTT_SERVER)
client.connect(MQTT_SERVER)

# Esegui il loop fino a quando il programma si chiude
client.loop_forever()

