#Convert two bytes to a single 2 byte address
def formDecAddress(high_byte, low_byte):
    address = (high_byte << 8) | low_byte
    return address
    
# Check whether a bit is set or not
def isSet(x, n):
    return x & 1 << n != 0

# Separate a single number into two separate bytes
def separateNumber(number):
    MSB = number >> 8
    LSB = number & 0xFF
    return MSB, LSB


def checkCoils(gpio_b):
    coil_values = (gpio_b & 0b0000000110000000)
    return coil_values

def checkDiscreteInputs(gpio_b):
    discrete_input_values = (gpio_b & 0b0000011000000000)
    return discrete_input_values 