# Define Modbus function codes
READ_COILS = const(0x01)
READ_DISCRETE_INPUTS = const(0x02)
READ_HOLDING_REGISTERS = const(0x03)
READ_INPUT_REGISTERS = const(0x04)
WRITE_SINGLE_COIL = const(0x05)
WRITE_HOLDING_REGISTER = const(0x06)

#Define exception codes for errors
EXCEPTION_CODE = const(0x84)  # Exception response offset
ILLEGAL_FUNCTION = const(0x01)
ILLEGAL_ADDRESS = const(0x02)
ILLEGAL_DATA = const(0x03)
SLAVE_ERROR = const(0x04)
CRC_ERROR = const(0x10)

#Define register address
GPIO_B_ADDRESS = const(0x40011200)