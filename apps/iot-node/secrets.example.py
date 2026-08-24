# Copiar este archivo como secrets.py y completar los valores reales.
# secrets.py está en .gitignore — nunca subir al repositorio.

WIFI_SSID   = "NombreDeRedWifi"
WIFI_PASS   = "contraseña_wifi"

# IP del host donde corre Mosquitto (mismo host que Docker Compose en desarrollo)
MQTT_SERVER = "192.168.x.x"
MQTT_USER   = "usuario"
MQTT_PASS   = "clave"

# Topic debe coincidir con MQTT_TOPIC_ATTENDANCE en .env
TOPIC = b"attendance/checkin"

# True durante desarrollo para ver logs en la REPL
DEBUG = True
