# Kuaai HRMS — Nodo IoT

Firmware MicroPython para **Raspberry Pi Pico 2W** que lee tarjetas RFID (RC522) y publica eventos de asistencia al broker MQTT del sistema Kuaai HRMS.

## Hardware requerido

| Componente | Modelo |
|---|---|
| Microcontrolador | Raspberry Pi Pico 2W |
| Lector RFID | RC522 (SPI) |
| LEDs | × 4 (verde, rojo × 2, amarillo) |
| Buzzer | Pasivo 5V |

## Pinout

### RC522 → Pico 2W

| RC522 | GPIO Pico |
|---|---|
| SDA (CS) | GP5 |
| SCK | GP6 |
| MOSI | GP7 |
| MISO | GP4 |
| RST | GP0 |
| 3.3V | 3V3 |
| GND | GND |

### LEDs y buzzer

| Señal | GPIO |
|---|---|
| LED conexión OK (verde) | GP8 |
| LED error conexión (rojo) | GP9 |
| LED envío OK (amarillo) | GP12 |
| LED error envío (rojo) | GP13 |
| Buzzer | GP15 |

## Estructura

```
iot-node/
├── boot.py              # Arranque: habilita GC
├── main.py              # Firmware principal (async)
├── secrets.py           # Credenciales locales (no versionar)
├── secrets.example.py   # Plantilla de secrets.py
├── micropython-async/   # Librería asyncio para MicroPython
├── mqtt_as.py           # Cliente MQTT async (vendorizado desde peterhinch/micropython-mqtt)
├── mfrc522.py           # Driver RC522 (vendorizado desde danjperron/micropython-mfrc522)
└── scripts/
    ├── leer_tag.py      # Utilidad: imprime UID de cualquier tarjeta
    └── control_acceso.py # Utilidad: acceso local sin MQTT
```

## Librerías externas necesarias

`mqtt_as.py` y `mfrc522.py` ya están versionados en este repo (no hace falta bajarlos
aparte). `mqtt_as.py` se vendorizó como archivo plano desde el `__init__.py` del
paquete `mqtt_as` upstream — el proyecto original migró a un paquete con soporte
MQTTv5/TLS que no usamos, así que alcanza con este archivo suelto.

## Configuración

1. Copiar `secrets.example.py` → `secrets.py`
2. Completar con SSID, contraseña WiFi, IP del broker MQTT
3. El `MQTT_SERVER` debe ser la IP de la máquina que corre Docker Compose

```python
# secrets.py
WIFI_SSID   = "MiRed"
WIFI_PASS   = "mipassword"
MQTT_SERVER = "192.168.1.100"   # IP del host Docker
MQTT_USER   = "usuario"
MQTT_PASS   = "clave"
TOPIC       = b"attendance/checkin"
DEBUG       = True
```

## Despliegue en el Pico

```bash
# Instalar herramienta de subida
pip install mpremote

# Subir todos los archivos necesarios
mpremote connect /dev/ttyACM0 cp boot.py :boot.py
mpremote connect /dev/ttyACM0 cp main.py :main.py
mpremote connect /dev/ttyACM0 cp secrets.py :secrets.py
mpremote connect /dev/ttyACM0 cp mqtt_as.py :mqtt_as.py
mpremote connect /dev/ttyACM0 cp mfrc522.py :mfrc522.py

# Reiniciar el Pico
mpremote connect /dev/ttyACM0 reset

# Ver logs en tiempo real
mpremote connect /dev/ttyACM0 repl
```

## Flujo de operación

```
Empleado acerca tarjeta al RC522
        ↓
Pico lee UID (int) → convierte a string → rfid_code
        ↓
Publica en MQTT topic "attendance/checkin":
  { "rfid_code": "37194205" }
        ↓
NestJS recibe el evento
        ↓
Busca empleado por rfid_code en PostgreSQL
        ↓
Determina tipo de registro (ENTRADA / SALIDA / INTERMEDIO)
        ↓
Persiste en attendance_records
```

## Indicadores LED

| Estado | LED |
|---|---|
| WiFi + MQTT conectado | Verde (GP8) encendido |
| Sin conexión | Rojo (GP9) encendido |
| Envío exitoso | Amarillo (GP12) parpadea + buzzer |
| Error al publicar | Rojo (GP13) encendido |
| Inicio del sistema | Todos parpadean 5 veces |

## Anti-rebote

Para evitar registros duplicados por una sola pasada de tarjeta, el firmware ignora el mismo UID durante `TIEMPO_ESPERA = 5` segundos.

## Diagnóstico

Si la Pico no se conecta, `DEBUG = True` en `secrets.py` imprime en la REPL:
- Redes WiFi detectadas (SSID + RSSI)
- Estado de la interfaz WiFi
- Intentos de conexión al broker MQTT con descripción del error
