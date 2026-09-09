import os

# Configurazione base
class Config:
    # Flask
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    DB_PATH = os.environ.get('DB_PATH', '/var/www/lab_app/lab_app.db')

    # MQTT
    MQTT_BROKER = os.environ.get('MQTT_BROKER', 'localhost')
    MQTT_PORT = int(os.environ.get('MQTT_PORT', '1883'))
    MQTT_TOPIC_RELAY = os.environ.get('MQTT_TOPIC_RELAY', 'esp/relay/thermo_z01')
    MQTT_TOPIC_TEMPHUM = os.environ.get('MQTT_TOPIC_TEMPHUM', 'esp/dht/TempHum_z01')

    # Data retention
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', '90'))

    # MQTT logging interval (seconds)
    MQTT_SLEEP_INTERVAL = int(os.environ.get('MQTT_SLEEP_INTERVAL', '600'))

    # HTTP Basic Auth credentials protecting the relay control routes
    # (/T1_on/, /T1_off/). If either is unset, those routes deny all
    # requests by default (fail closed) instead of falling back to a
    # guessable default.
    AUTH_USERNAME = os.environ.get('AUTH_USERNAME')
    AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD')
