import time
import network
import ujson
from machine import Pin
import secrets
from mqtt_as import MQTTClient, config
import uasyncio as asyncio
from mfrc522 import MFRC522
import sys


DEBUG = secrets.DEBUG


def log(msg):
    if DEBUG:
        print(msg)


# Pines LEDs y buzzer
led_connection       = Pin(8,  Pin.OUT)
led_connection_error = Pin(9,  Pin.OUT)
led_envio            = Pin(12, Pin.OUT)
led_error            = Pin(13, Pin.OUT)
leds = [led_connection, led_connection_error, led_envio, led_error]

buzzer = Pin(15, Pin.OUT)

TOPIC = secrets.TOPIC
TIEMPO_ESPERA = 5  # segundos entre lecturas del mismo UID

conectado_mqtt = False


async def parpadear(leds, veces=1, duracion=150):
    for _ in range(veces):
        for led in leds:
            led.on()
        await asyncio.sleep_ms(duracion)
        for led in leds:
            led.off()
        await asyncio.sleep_ms(duracion)


async def wifi_han(con):
    led_connection.value(con)
    led_connection_error.value(not con)
    if con:
        log("[WiFi] Conectado y broker accesible")
    else:
        log("[WiFi] Problema de conexion (WiFi o broker)")


async def conn_han(client):
    global conectado_mqtt
    conectado_mqtt = True
    log("[MQTT] Conexion exitosa con el broker")


async def enviar_mensaje(rfid_code: str):
    """Publica rfid_code como string JSON en el topic MQTT."""
    if not conectado_mqtt:
        log(f"[ERROR] No conectado a MQTT. rfid_code={rfid_code}")
        led_connection_error.on()
        return
    try:
        payload = ujson.dumps({"rfid_code": rfid_code})
        await client.publish(TOPIC, payload, qos=1)
        log(f"[MQTT] Payload enviado: {payload}")
        buzzer.on()
        await asyncio.sleep_ms(100)
        buzzer.off()
        asyncio.create_task(parpadear([led_envio]))
    except Exception as e:
        log(f"[ERROR] Fallo al publicar en MQTT: {e}")
        led_error.on()


# Configuracion WiFi/MQTT
config['ssid']         = secrets.WIFI_SSID
config['wifi_pw']      = secrets.WIFI_PASS
config['server']       = secrets.MQTT_SERVER
config['user']         = secrets.MQTT_USER
config['password']     = secrets.MQTT_PASS
config['clean']        = True
config['wifi_coro']    = wifi_han
config['connect_coro'] = conn_han

client = MQTTClient(config)

# Configurar RC522 (SPI0: sck=GP6, miso=GP4, mosi=GP7, cs=GP5, rst=GP0)
rdr = MFRC522(spi_id=0, sck=6, miso=4, mosi=7, cs=5, rst=0)

ultimo_uid   = None
tiempo_ultimo_uid = 0


async def wifi_ensure(timeout=30):
    """Intenta conectar a WiFi antes de iniciar el cliente MQTT."""
    try:
        s = network.WLAN(network.STA_IF)
        s.active(True)
        log(f"[WIFI] Interfaz activa: {s.active()}")

        try:
            await asyncio.sleep_ms(200)
            nets = s.scan()
            muestra = [(n[0].decode() if isinstance(n[0], bytes) else n[0], n[3] if len(n) > 3 else None)
                       for n in nets[:5]]
            log(f"[DIAG] {len(nets)} redes encontradas. Muestra: {muestra}")
        except Exception as e:
            log(f"[DIAG] Scan inicial falló: {e}")

        try:
            log(f"[WIFI] Conectando a '{config['ssid']}'...")
            s.connect(config['ssid'], config['wifi_pw'])
        except Exception as e:
            log(f"[WIFI] s.connect lanzó excepción: {e}")

        for i in range(timeout):
            if s.isconnected():
                log(f"[WIFI] Conectado tras {i}s. IP: {s.ifconfig()[0]}")
                return True
            await asyncio.sleep(1)

        log("[WIFI] Timeout — no se pudo conectar")
        return False
    except Exception as e:
        log(f"[WIFI] Error inesperado: {e}")
        return False


async def main():
    global ultimo_uid, tiempo_ultimo_uid

    log("[INIT] Iniciando sistema Kuaai IoT...")
    for led in leds:
        led.off()
    await parpadear(leds, veces=5, duracion=150)

    # Conectar WiFi antes de MQTT para mejor diagnóstico
    wifi_ok = await wifi_ensure(timeout=20)
    if not wifi_ok:
        log("[WIFI] Aviso: continuando de todos modos (MQTT reintentará)")

    # Conexión MQTT con reintentos
    intento = 0
    while True:
        intento += 1
        try:
            log(f"[MQTT] Intento {intento} de conexion...")
            await client.connect()
            log("[MQTT] Conexion exitosa. Iniciando loop de lecturas RFID...")
            led_connection_error.off()
            break
        except Exception as e:
            log(f"[ERROR] Intento {intento} fallido: {e}")
            s = network.WLAN(network.STA_IF)
            log(f"[DIAG] WiFi connected={s.isconnected()}")
            led_connection_error.on()
            await asyncio.sleep(3)

    # Loop principal: lectura RFID
    while True:
        rdr.init()
        stat, tag_type = rdr.request(rdr.REQIDL)
        if stat == rdr.OK:
            stat, raw_uid = rdr.SelectTagSN()
            if stat == rdr.OK:
                uid_int = int.from_bytes(bytes(raw_uid), "little", False)
                rfid_code = str(uid_int)  # VARCHAR en la BD → siempre string
                tiempo_actual = time.time()

                if (uid_int != ultimo_uid) or (tiempo_actual - tiempo_ultimo_uid > TIEMPO_ESPERA):
                    log(f"[RFID] Detectado: {rfid_code}")
                    ultimo_uid = uid_int
                    tiempo_ultimo_uid = tiempo_actual
                    await enviar_mensaje(rfid_code)

        await asyncio.sleep_ms(100)


try:
    asyncio.run(main())
except Exception as e:
    log(f"[FATAL] Error en asyncio.run(): {e}")
    sys.print_exception(e)
finally:
    asyncio.new_event_loop()
