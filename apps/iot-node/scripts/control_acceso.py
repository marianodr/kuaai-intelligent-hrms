from machine import Pin
from mfrc522 import MFRC522
import time

lector = MFRC522(spi_id=0, sck=6, miso=4, mosi=7, cs=5, rst=0)

rojo = Pin(9, Pin.OUT)
verde = Pin(8, Pin.OUT)

TARJETA = 37194205
LLAVERO = 346298099

print("Lector activo...\n")

while True:
    lector.init()
    (stat, tag_type) = lector.request(lector.REQIDL)
    if stat == lector.OK:
        (stat, uid) = lector.SelectTagSN()
        if stat == lector.OK:
            identificador = int.from_bytes(bytes(uid), "little", False)

            if identificador == TARJETA:
                print("RFID: " + str(identificador)+" Acceso concedido")
                rojo.value(0)
                verde.value(1)
                time.sleep(2)
                verde.value(0)

            # elif identificador == LLAVERO:
            #    print("UID: "+ str(identificador)+" Acceso concedido")
            #    rojo.value(0)
            #    verde.value(1)
            #    time.sleep(2)
            #    verde.value(0)

            else:
                print("RFID: " + str(identificador) +
                      " desconocido: Acceso denegado")
                rojo.value(1)
                verde.value(0)
                time.sleep(2)
                rojo.value(0)
