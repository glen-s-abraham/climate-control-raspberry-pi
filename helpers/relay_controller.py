import RPi.GPIO as GPIO

# Relay pins
RELAY_PINS = {'relay1': 17, 'relay2': 18}


class RelayController:
    def __init__(self, relay_pins):
        GPIO.setmode(GPIO.BCM)
        for pin in relay_pins.values():
            GPIO.setup(pin, GPIO.OUT)

    def set_relay_state(self, relay_name, state):
        """
        Set the relay to the given state ('ON' or 'OFF').

        Parameters
        ----------
        relay_name : str
            The name of the relay to control ('relay1' or 'relay2').
        state : str
            The state to set the relay to ('ON' or 'OFF').
        """
        GPIO.output(RELAY_PINS[relay_name], GPIO.HIGH if state == 'ON' else GPIO.LOW)

    def cleanup(self):
        GPIO.cleanup()
