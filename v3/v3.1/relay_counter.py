import ustruct
import machine
from machine import UART, Pin
import time
import const

def coilCounter(counter):
    counter += 1
    return counter

def checkCounter(counter):
    if counter >= 15:
        return 1
    else:
        return 0