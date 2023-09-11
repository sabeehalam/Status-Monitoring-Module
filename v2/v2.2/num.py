#Convert two bytes to a single 2 byte address
def formDecAddress(high_byte, low_byte):
    address = (high_byte << 8) | low_byte
    return address
    
#check whether a bit is set or not
def isSet(x, n):
    return x & 1 << n != 0

# Separate a single number into two separate bytes
def separateNumber(number):
    MSB = number >> 8
    LSB = number & 0xFF
    return MSB, LSB
