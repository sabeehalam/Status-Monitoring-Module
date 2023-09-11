import machine
import utime

class DebounceButton:
    def __init__(self, pin, debounce):
        self.pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.last_state = self.pin.value()
        self.last_change = utime.ticks_ms()
        self.debounce_duration = debounce
        self.press_count = 0

    def isPressed(self):
        current_state = self.pin.value()
        current_time = utime.ticks_ms()
        if current_state != self.last_state:
            if utime.ticks_diff(current_time, self.last_change) > self.debounce_duration:
                self.last_state = current_state
                self.last_change = current_time
#                 return current_state == 0
                if current_state == 0:
                    self.press_count = 1
                    return True
        elif (current_state == self.last_state and current_state == 0):
            self.press_count = 0
            return True
        else:
            return False
    
    def value(self):
        return self.pin.value()
    
    def checkPressCount(self):
        return self.press_count

