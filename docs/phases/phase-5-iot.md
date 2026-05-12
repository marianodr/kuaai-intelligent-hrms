# Fase 5 — Nodo IoT (Raspberry Pi Pico 2W)

## Hardware

| Componente | Modelo |
|---|---|
| Microcontrolador | Raspberry Pi Pico 2W |
| Lector RFID | RC522 (interfaz SPI) |
| Feedback visual | 4 LEDs (GP8, GP9, GP12, GP13) |
| Feedback sonoro | Buzzer pasivo (GP15) |

## Librerías externas (deben subirse al Pico)

| Librería | Propósito |
|---|---|
| `mfrc522.py` | Driver SPI para el lector RC522 |
| `mqtt_as.py` | Cliente MQTT asíncrono con reconexión automática |

## Estructura de archivos

```
iot-node/
├── boot.py              # Habilita GC; se ejecuta antes de main.py
├── main.py              # Firmware principal (asyncio)
├── secrets.py           # Credenciales WiFi y MQTT (no versionar)
├── secrets.example.py   # Plantilla segura para versionar
└── scripts/
    ├── leer_tag.py      # Utilidad diagnóstico: imprime UID de tarjetas
    └── control_acceso.py # Control de acceso local sin MQTT
```

## Flujo del firmware

```
boot.py → gc.enable()
        ↓
main.py → init LEDs + parpadeo 5× (señal de inicio)
        ↓
wifi_ensure() → conecta WiFi, diagnostica si falla
        ↓
MQTTClient.connect() → reintenta cada 3s hasta éxito
        ↓
Loop principal (asyncio, cada 100ms):
  rdr.request(REQIDL)
  rdr.SelectTagSN()
  uid_int = int.from_bytes(raw_uid, "little")
  rfid_code = str(uid_int)   ← string para coincidir con VARCHAR en BD
  si uid nuevo o > 5s desde último:
    publish(TOPIC, {"rfid_code": rfid_code}, qos=1)
    buzzer 100ms + parpadeo LED amarillo
```

## Payload MQTT

```json
{
  "rfid_code": "37194205"
}
```

- Topic: `attendance/checkin` (configurable en `secrets.py`)
- QoS: 1 (at-least-once, garantiza entrega)
- `rfid_code` se envía como **string** para coincidir con el tipo `VARCHAR` de la columna en PostgreSQL

## Decisiones técnicas

### mqtt_as en lugar de umqtt.simple

`umqtt.simple` (incluido en MicroPython) no maneja reconexión automática. `mqtt_as` es una librería asíncrona basada en `uasyncio` que:
- Reconecta automáticamente si se pierde WiFi o la conexión al broker
- Provee callbacks `wifi_coro` y `connect_coro` para actualizar LEDs
- Soporta QoS 1

### asyncio en lugar de polling bloqueante

El uso de `uasyncio` permite que el loop de lectura RFID (cada 100ms) coexista con la gestión de la conexión MQTT sin bloquear ninguna de las dos.

### Anti-rebote por tiempo

Para evitar múltiples registros de una sola pasada de tarjeta, el firmware ignora el mismo UID durante 5 segundos (`TIEMPO_ESPERA`). Esto es suficiente para el caso de uso real (una lectura por evento).

### Conversión de UID a string

El RC522 devuelve el UID como lista de bytes. `int.from_bytes()` lo convierte a entero (ej: `37194205`). Se convierte explícitamente a `str()` antes de serializarlo en JSON, porque `rfid_code` en PostgreSQL es `VARCHAR(100)`.

## Bug corregido en main.py original

El `main.py` original tenía `network` referenciado dentro de `wifi_ensure()` sin importarlo al nivel del módulo, lo que causaba `NameError` en runtime. Se agregó `import network` al inicio del archivo.

## Indicadores visuales

| Estado | LED activo |
|---|---|
| Inicio | Todos parpadean 5× |
| WiFi + MQTT OK | Verde (GP8) encendido |
| Sin conexión | Rojo (GP9) encendido |
| Lectura + envío OK | Amarillo (GP12) parpadea + buzzer 100ms |
| Error al publicar | Rojo (GP13) encendido |

## Cómo probarlo

### 1. Preparar el entorno

```bash
pip install mpremote
```

### 2. Verificar UID de una tarjeta

```bash
# Subir utilidad diagnóstico
mpremote connect /dev/ttyACM0 cp scripts/leer_tag.py :leer_tag.py
mpremote connect /dev/ttyACM0 run leer_tag.py
# Acercar tarjeta → imprime UID decimal
```

### 3. Cargar firmware completo

```bash
mpremote connect /dev/ttyACM0 cp boot.py :boot.py + \
  cp main.py :main.py + \
  cp secrets.py :secrets.py + \
  cp mfrc522.py :mfrc522.py + \
  cp mqtt_as.py :mqtt_as.py + \
  reset
```

### 4. Verificar en el backend

```bash
# Suscribirse al topic para ver eventos en tiempo real
mosquitto_sub -h localhost -t "attendance/checkin" -v

# Verificar que NestJS procesó el evento
curl http://localhost:3001/dashboard/today \
  -H "Authorization: Bearer $TOKEN"
```

## Pendientes para Fase 6

- Registrar el rfid_code de cada tarjeta física en la tabla `employees` de la BD
- Probar el flujo completo: tarjeta → MQTT → NestJS → PostgreSQL → dashboard
