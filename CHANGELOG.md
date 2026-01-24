# Changelog

## [2026-01-24] Refactoring: Centralizzazione configurazione e gestione errori

### Obiettivo
Migliorare la manutenibilità, sicurezza e robustezza dell'applicazione attraverso configurazione centralizzata e logging strutturato.

### File Nuovi

**config.py**
- Classe `Config` centralizzata per tutte le configurazioni
- Supporto variabili d'ambiente (DB_PATH, MQTT_BROKER, SECRET_KEY, etc.)
- Valori di default per sviluppo locale
- Elimina hardcoded values sparsi nel codice

**.env.example**
- Template documentato per configurazione locale
- Guida per deployment su diversi ambienti
- Non contiene credenziali reali (sicurezza)

### File Modificati

**lab_app.py**
- ✓ Importato `logging` e `Config`
- ✓ Sostituito `app.debug = True` con `Config.DEBUG` (sicurezza)
- ✓ Aggiunto try/except a `send_mqtt_message()` con logging errori
- ✓ Aggiunto try/except a `lab_temp()` per gestire errori DB
- ✓ Aggiunto try/except a `get_records()` per gestire errori query
- ✓ Tutti i valori hardcoded sostituiti con `Config.*`
- ✓ Logging strutturato per debugging migliore

**env_log.py**
- ✓ Importato `logging` e `Config`
- ✓ Aggiunto try/except a `log_values()` per errori DB
- ✓ Aggiunto try/except a `on_message()` per errori parsing MQTT
- ✓ Validazione payload MQTT (controllo formato)
- ✓ Logging di connessione/errori broker MQTT
- ✓ Tutti i valori hardcoded sostituiti con `Config.*`

**requirements.txt**
- ✓ Versioni specifiche per Flask (1.1.4) e dipendenze core
- ✓ paho-mqtt downgrade a 1.6.1 (compatibilità Python 3.7)
- ✓ Commenti ASCII per compatibilità encoding
- ✓ Organizzato per categoria (core, MQTT, hardware, utilities)

**.gitignore**
- ✓ Aggiunto `.env` (protezione credenziali)
- ✓ Aggiunto file IDE (.vscode/, .idea/, *.swp)
- ✓ Aggiunto Python cache (*.pyc, *.pyo, __pycache__)
- ✓ Aggiunto `.claude/` (directory tool Claude Code)

### Benefici
1. **Sicurezza**: Debug mode configurabile, no hardcoded secrets
2. **Manutenibilità**: Config centralizzato, facile da modificare
3. **Robustezza**: Error handling previene crash, logging aiuta debug
4. **Portabilità**: Facile deployment su ambienti diversi via .env

### Test
- ✓ Homepage funzionante
- ✓ Controllo relay testato (con sostituzione hardware)
- ✓ Temperatura e database aggiornati correttamente
- ✓ Query database con filtri funzionanti

### Co-Authored-By
Claude Sonnet 4.5 <noreply@anthropic.com>
