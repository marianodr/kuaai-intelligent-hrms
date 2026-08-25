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

### led_error (GP13) quedaba pegado en encendido (2026-08-25)

`enviar_mensaje()` prendía `led_error` en el `except` pero nunca lo apagaba en el camino
exitoso, así que una vez que se disparaba quedaba encendido para siempre (hasta el próximo
reboot), sin reflejar el estado real del último intento de publicación. Se agregó
`led_error.off()` al confirmar un publish exitoso.

En la práctica este LED casi no se dispara: ver la sección siguiente sobre cómo `mqtt_as`
maneja los errores de red.

## mqtt_as.py: cómo maneja realmente los errores de publish (y por qué no hay cola de reintento)

Investigando el bug de arriba se encontró que el `MQTTClient.publish()` de `mqtt_as.py`
(vendorizado en este repo) **ya reintenta indefinidamente por su cuenta**:

```python
# mqtt_as.py — clase MQTTClient
async def publish(self, topic, msg, retain=False, qos=0, properties=None):
    qos_check(qos)
    while 1:
        await self._connection()          # espera a que _keep_connected() reconecte
        try:
            return await super().publish(topic, msg, retain, qos, properties)
        except OSError:
            pass                           # reintenta para siempre, nunca propaga
```

Cualquier falla de red (WiFi caída, broker caído, timeout) llega como `OSError` y se
absorbe acá — nunca sube como excepción a `main.py`. Por eso el `except Exception` de
`enviar_mensaje()` casi nunca se ejecuta: solo atraparía un bug real de software (ej.
`MemoryError`), no un corte de conectividad.

**Consecuencia:** no existe una cola de mensajes pendientes. Hay un único `publish()` que
queda colgado (`await`) reintentando hasta que la conexión vuelve. Como `main()` llama
`await enviar_mensaje(rfid_code)` **directamente dentro del loop de lectura RFID**, mientras
ese publish está colgado el firmware **no lee tarjetas nuevas** — no se pierden ni se
encolan, simplemente el lector queda "sordo" durante el corte. El LED de conexión (GP8/GP9)
sigue actualizándose bien mientras tanto porque lo maneja `_keep_connected()`, una tarea de
fondo independiente.

### Decisión (2026-08-25): no resolver esto todavía

Para el estado actual del MVP (WiFi local, cortes esperables breves y poco frecuentes) se
decidió **no** construir una cola de reintento ni desacoplar el envío de la lectura por
ahora — dejar solo el fix cosmético del LED. Quedó pendiente para cuando se necesite mayor
robustez:

1. **Desacoplar envío de lectura** — cambiar `await enviar_mensaje(...)` por
   `asyncio.create_task(enviar_mensaje(...))` en el loop principal, para que un publish
   colgado no congele la lectura de nuevas tarjetas. Riesgo: varias tarjetas pasadas durante
   un corte largo generan varios `publish()` colgados en simultáneo (a vigilar en un
   dispositivo con RAM limitada).
2. **Cola de reintento acotada** — mantener en RAM los últimos N `rfid_code` + timestamp
   pendientes y reintentarlos cuando `conn_han` confirme reconexión, con el LED de error
   reflejando "hay pendientes en cola". Es la solución más robusta, pero la que más
   superficie nueva de bugs agrega.

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
