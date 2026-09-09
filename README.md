# Lab App — Termostato IoT domestico

Progetto hobbistico per il controllo remoto via web di un impianto di
riscaldamento domestico, con monitoraggio di temperatura e umidità.
Un Raspberry Pi esegue un piccolo server Flask che pubblica comandi
MQTT verso un ESP8266 collegato a un relè (che pilota la richiesta di
calore alla caldaia), mentre un secondo ESP8266 con sensore DHT22
pubblica periodicamente le letture di temperatura e umidità, che
vengono salvate in un database SQLite e mostrate a video (anche in
grafico).

Nato per un singolo ambiente ("zone 01"), è volutamente semplice: non
è un prodotto, ma un progetto personale di domotica fai-da-te.

## Cosa fa

- **Pagina web** con due pulsanti (Relay ON / Relay OFF) per accendere
  o spegnere manualmente la richiesta di calore alla caldaia.
- **Comunicazione MQTT** tra il server Flask, un ESP8266 che pilota il
  relè e un ESP8266 con sensore DHT22 che pubblica temperatura e
  umidità.
- **Storico temperatura/umidità** su database SQLite, con:
  - una pagina che mostra l'ultima lettura disponibile (`/lab_temp`,
    auto-refresh ogni 10 minuti);
  - una pagina con filtro per intervallo di date o per ultime N ore e
    relativi grafici (`/lab_env_db`, tramite Chart.js).
- **Pulizia automatica dello storico**: ad ogni nuova lettura vengono
  eliminati i record più vecchi della retention configurata
  (`DATA_RETENTION_DAYS`).
- **Galleria foto** del laboratorio/impianto (`/lab_photos`).
- **Script di supporto** (in `extraCodeAndConfFiles/`) non gestiti
  dall'app Flask ma usati sullo stesso Raspberry Pi: notifica email
  quando cambia l'IP pubblico di casa (utile con una connessione a IP
  dinamico), ed esempi di configurazione di sistema (nginx, uWSGI,
  systemd, cron, msmtp) usati nel deployment originale.

## Architettura

```
┌─────────────────────┐        MQTT        ┌──────────────────────────┐
│  ESP8266 + relè      │◄───────────────────┤  Broker MQTT (locale)     │
│  (comando caldaia)   │  esp/relay/thermo_  │                          │
└─────────────────────┘        z01          │                          │
                                             │                          │
┌─────────────────────┐        MQTT         │                          │
│  ESP8266 + DHT22      ├────────────────────►                          │
│  (temp/umidità)       │  esp/dht/TempHum_  └──────────┬───────────────┘
└─────────────────────┘        z01                     │
                                                          │ publish/subscribe
                                              ┌───────────▼──────────────┐
                                              │  Raspberry Pi             │
                                              │  ─ lab_app.py (Flask)     │
                                              │    web UI + comandi relè │
                                              │  ─ env_log.py             │
                                              │    subscriber MQTT che    │
                                              │    scrive su SQLite       │
                                              │  ─ lab_app.db (SQLite)    │
                                              └───────────────────────────┘
```

- **`lab_app.py`**: applicazione Flask. Serve la pagina principale,
  le route di controllo del relè, la pagina di temperatura corrente,
  la pagina/grafici storici e la galleria foto. Per pubblicare i
  comandi verso il relè usa `paho-mqtt` come client MQTT (connessione
  "usa e getta" ad ogni richiesta, senza restare in ascolto).
- **`env_log.py`**: processo separato e persistente (pensato per
  girare come servizio/background, es. avviato da `rc.local`) che si
  sottoscrive al topic MQTT del sensore DHT22, valida il payload
  ricevuto e scrive temperatura/umidità nel database SQLite,
  applicando la retention configurata.
- **`config.py`**: configurazione centralizzata, letta da variabili
  d'ambiente con valori di default sensati per lo sviluppo locale.
- **`wsgi_entrypoint.py`** + **`lab_app_uwsgi.ini`**: punto di ingresso
  per servire l'app in produzione con uWSGI (dietro nginx, si vedano
  gli esempi in `extraCodeAndConfFiles/configurationFiles.txt`).
- **Firmware ESP8266** (MicroPython, in
  `extraCodeAndConfFiles/micropythonESP8266/`): due varianti, una per
  il nodo relè (comando caldaia) e una per il nodo sensore DHT22.

## Hardware richiesto

- Un Raspberry Pi (o altro Linux SBC) come server, in rete locale.
- Due moduli **ESP8266** (es. Wemos D1 mini) con MicroPython:
  - uno collegato a un **relè** che comanda la richiesta di calore
    della caldaia (contatto pilotato su GPIO0/D3, LED di stato su
    GPIO2/D4);
  - uno collegato a un sensore **DHT22** per temperatura e umidità
    (dati su GPIO0/D3, LED di stato su GPIO2/D4).
- Un broker MQTT raggiungibile dalla rete locale (es. Mosquitto,
  installabile anche sullo stesso Raspberry Pi).

## Struttura del database

Il codice si aspetta una tabella SQLite `temphum` con questo schema
(non è incluso uno script di creazione: va creata manualmente al primo
avvio):

```sql
CREATE TABLE temphum (
    datetime TEXT,
    sensor_id TEXT,
    temp REAL,
    hum REAL
);
```

## Installazione

```bash
git clone <url-del-tuo-fork>
cd lab_app_clean

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Nota: `requirements.txt` include alcune dipendenze specifiche per
> Raspberry Pi (es. `RPi.GPIO`, `picamera`, `rpi-ws281x`) non
> strettamente necessarie per far girare solo il server Flask; se le
> installi su un sistema diverso da un Raspberry Pi alcune di queste
> potrebbero non essere disponibili/necessarie.

### Configurazione

Copia il file di esempio e personalizzalo:

```bash
cp .env.example .env
```

Variabili principali (vedi `.env.example` per l'elenco completo):

| Variabile | Descrizione | Default |
|---|---|---|
| `FLASK_DEBUG` | Abilita il debug mode di Flask | `false` |
| `SECRET_KEY` | Chiave segreta Flask | valore di sviluppo, **da cambiare in produzione** |
| `DB_PATH` | Percorso del file SQLite | `/var/www/lab_app/lab_app.db` |
| `MQTT_BROKER` | Host del broker MQTT | `localhost` |
| `MQTT_PORT` | Porta del broker MQTT | `1883` |
| `MQTT_TOPIC_RELAY` | Topic MQTT per il comando relè | `esp/relay/thermo_z01` |
| `MQTT_TOPIC_TEMPHUM` | Topic MQTT per le letture DHT22 | `esp/dht/TempHum_z01` |
| `DATA_RETENTION_DAYS` | Giorni di storico mantenuti | `90` |
| `MQTT_SLEEP_INTERVAL` | Pausa (secondi) di `env_log.py` dopo ogni lettura salvata | `600` |
| `AUTH_USERNAME` | Username per proteggere i comandi relè | *(nessuno, obbligatorio)* |
| `AUTH_PASSWORD` | Password per proteggere i comandi relè | *(nessuno, obbligatorio)* |

### Avvio in sviluppo

```bash
export FLASK_APP=wsgi_entrypoint.py
flask run
# oppure semplicemente:
python wsgi_entrypoint.py
```

In un altro processo/terminale, avvia il logger MQTT che scrive su
database (richiede un broker MQTT raggiungibile):

```bash
python env_log.py
```

### Deploy in produzione

Il progetto è pensato per girare su un Raspberry Pi dietro **uWSGI +
nginx**. In `extraCodeAndConfFiles/` trovi esempi (genericizzati, da
adattare) di:

- `configurationFiles.txt`: configurazione nginx come reverse proxy
  verso il socket uWSGI, unit file systemd per il servizio uWSGI,
  avvio di `env_log.py` da `rc.local`, cron per il controllo dell'IP
  pubblico, esempio di configurazione `msmtp` per l'invio email.
- `extip.sh`: script cron che controlla se l'IP pubblico di casa è
  cambiato e invia una notifica email (utile con connessioni a IP
  dinamico); imposta `NOTIFY_EMAIL` con il tuo indirizzo prima di
  usarlo.
- `lab_app_uwsgi.ini`: configurazione uWSGI usata in produzione.

## Sicurezza: protezione dei comandi relè

Le route `/T1_on/` e `/T1_off/` azionano fisicamente il relè che
comanda la richiesta di calore alla caldaia: sono protette con
**HTTP Basic Auth**, con credenziali lette dalle variabili d'ambiente
`AUTH_USERNAME` e `AUTH_PASSWORD`.

- Se una delle due variabili non è impostata, le route negano sempre
  l'accesso (fail-closed): non esiste un default "aperto".
- Al primo utilizzo dei pulsanti nella pagina principale, il browser
  chiederà username e password (dialog nativo, nessuna modifica ai
  form necessaria).
- Le altre route (temperatura corrente, storico, foto) restano
  pubbliche in lettura, coerentemente con lo scopo del progetto.

Per una scala più grande o un'esposizione diretta su Internet, valuta
comunque di mettere l'app dietro HTTPS (es. reverse proxy nginx con
certificato TLS) dato che HTTP Basic Auth trasmette le credenziali in
chiaro su HTTP semplice.

## Firmware ESP8266 (MicroPython)

In `extraCodeAndConfFiles/micropythonESP8266/` trovi due firmware
MicroPython, uno per nodo:

- `main-py.thermo.txt` → nodo relè (comando caldaia).
- `main-py.dht.txt` → nodo sensore DHT22 (temperatura/umidità).

Per usarli:

1. Flasha MicroPython sull'ESP8266 (es. con `esptool.py` e il firmware
   ufficiale MicroPython per ESP8266).
2. Apri il file `.txt` corrispondente e sostituisci i placeholder con
   i tuoi valori:
   - `WIFI_SSID` / `WIFI_PASSWORD`: le credenziali della tua rete
     WiFi.
   - `CLIENT_IP`, `ROUTER_IP`, `DNS_IP`, `MQTT_SERVER`: sono impostati
     come esempio con indirizzi tipici `192.168.1.x` — vanno adattati
     alla subnet della tua rete locale (es. tramite l'IP del tuo
     router/broker MQTT).
3. Carica il file come `main.py` sull'ESP8266 (es. con `ampy`,
   `rshell` o `webrepl`), rinominandolo se necessario.
4. Collega hardware e alimenta il modulo: al boot si connette al WiFi
   e poi al broker MQTT, sottoscrivendosi/pubblicando sui topic
   configurati.

## Foto

Alcune foto del laboratorio/impianto sono incluse in `static/` e
mostrate dalla pagina `/lab_photos`.

## Licenza

Distribuito con licenza MIT, vedi [LICENSE](LICENSE).
