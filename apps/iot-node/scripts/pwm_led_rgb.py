from machine import Pin, PWM
import time

# PWM para cada color
red = PWM(Pin(9))
green = PWM(Pin(8))
blue = PWM(Pin(12))

red.freq(1000)
green.freq(1000)
blue.freq(1000)


def set_color(r, g, b):
    red.duty_u16(int(r * 65535))
    green.duty_u16(int(g * 65535))
    blue.duty_u16(int(b * 65535))


# Iniciar con todos apagados
set_color(0, 0, 0)

while True:
    # Rojo
    set_color(1, 0, 0)
    print("Rojo")
    time.sleep(2)

    # Amarillo (rojo + poco verde)
    set_color(1, 0.01, 0)
    print("Amarillo")
    time.sleep(2)

    # Verde (baja intensidad)
    set_color(0, 0.1, 0)
    print("Verde")
    time.sleep(2)

    # Verde (alta intensidad)
    set_color(0, 1, 0)
    print("Verde")
    time.sleep(2)

    # Azul
    set_color(0, 0, 1)
    print("Azul")
    time.sleep(2)

    # Azul
    set_color(0, 0.05, 1)
    print("Otro")
    time.sleep(2)
