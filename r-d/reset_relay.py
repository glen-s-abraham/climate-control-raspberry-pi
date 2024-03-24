import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

# Relay 1
GPIO.setup(17, GPIO.OUT)
# Relay 2
GPIO.setup(18, GPIO.OUT)


GPIO.output(17, GPIO.LOW)
print('Relay 1 OFF')

GPIO.output(18, GPIO.LOW)
print('Relay 1 OFF')

