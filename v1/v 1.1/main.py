import ustruct
from machine import UART, Pin
import array
import time
import gc
from button_debounce import DebounceButton

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

# Define slave address
SLAVE_ADDRESS = 0x01

# Define UART parameters
UART_BAUD_RATE = 9600
UART_DATA_BITS = 0x08
UART_STOP_BITS = 0x01
UART_PARITY    = None

#Counter variables for push buttons
DEBOUNCE_DURATION = 150
BUTTON_COUNTER_1  = 0
BUTTON_COUNTER_2  = 0
MSB_BUTTON_1, LSB_BUTTON_1 = 0, 0
MSB_BUTTON_2, LSB_BUTTON_2 = 0, 0

#variables for time
TIME_START  = time.time()
TIME_ACTIVE = 0
TIME_ACTIVE_MSB, TIME_ACTIVE_LSB = 0, 0
TIME_NOW    = 0 

coil_single = 0b0 # Starting address for relay 1 and 2 
discrete_input_single = 0b0 #For button/ relay status in future

holding_registers = {
    0x00: SLAVE_ADDRESS, #slave id
    0x01: UART_BAUD_RATE, #baud rate constant
    0x02: UART_DATA_BITS, # data bits
    0x03: UART_STOP_BITS, #stop bits
    0x04: UART_PARITY, #parity bits
    0x05: DEBOUNCE_DURATION, #debounce duration
    0x06: 0, # Button 1 counter MSB
    0x07: 0, # Button 1 counter LSB
    0x08: 0, # Button 2 counter MSB
    0x09: 0, # Button 2 counter LSB
    0x0A: 0, # Time Active MSB
    0x0B: 0, # Time Active LSB
    }

input_registers = {
    0x00: 0,  # Read only integers for button count 1 (msb)
    0x01: 0,  # Read-Only Integers for button count 1 (lsb)
    0x02: 0,  # Read-Only Integers for button count 2 (msb)
    0x03: 0,  # Read-Only Integers for button count 2 (msb)
    0x04: 0,  # Read-Only Use for epoch (msb)
    0x05: 0,  # Read-Only Use for epoch (lsb)
    }

REG_LENGTHS = {
    0x01: 8,
    0x02: 8,
    0x03: len(holding_registers),
    0x04: len(input_registers),
    0x05: 8,
    0x06: len(holding_registers) 
    }

def create_exception_resp(request, exc_code):
    # Build Modbus exception response
    resp = ustruct.pack(">BBB", request[0], EXCEPTION_CODE, exc_code)
    return resp
 
#Create a 16-bit CRC calculator for the modbus command 
def crc16(buf):
    crc = 0xFFFF  
    for pos in range(len(buf)):
        crc ^= buf[pos]  # XOR byte into least sig. byte of crc
        
        for i in range(8, 0, -1):  # Loop over each bit
            if crc & 0x0001:  # If the LSB is set
                crc >>= 1  # Shift right and XOR 0xA001
                crc ^= 0xA001
            else:  # Else LSB is not set
                crc >>= 1  # Just shift right 
    return crc

#Convert two bytes to a single 2 byte address
def formDecAddress(high_byte, low_byte):
    address = (high_byte << 8) | low_byte
    return address

#Swap bytes for CRC 
def reverseCRC(crc):
    crc_low, crc_high = divmod(crc, 0x100)
#     print("crc ordered", crc)
    return ustruct.pack(">BB", crc_high, crc_low)

#check whether a bit is set or not
def isSet(x, n):
    return x & 1 << n != 0

# Separate a single number into two separate bytes
def separateNumber(number):
    MSB = number >> 8
    LSB = number & 0xFF
    return MSB, LSB

# Calculate the time active and separate it to two for register
def calculateTimeActive():
    global TIME_NOW
    global TIME_ACTIVE
    if (time.time() != TIME_NOW):
        TIME_NOW =  time.time()
        TIME_ACTIVE += 1
        return separateNumber(TIME_ACTIVE)
    else: return separateNumber(TIME_ACTIVE)
    
# Change the corresponding variable according to the writeHoldingRegister function
def changeCorrespondingVariable(start_register, values):
    global holding_registers
    global SLAVE_ADDRESS
    global UART_BAUD_RATE
    global UART_DATA_BITS
    global UART_STOP_BITS
    global UART_PARITY
    global DEBOUNCE_DURATION
    global MSB_BUTTON_1
    global MSB_BUTTON_2
    global LSB_BUTTON_1
    global LSB_BUTTON_2
    global BUTTON_COUNTER_1
    global BUTTON_COUNTER_2
    global TIME_ACTIVE_MSB
    global TIME_ACTIVE_LSB
    global TIME_ACTIVE
    
#     print("Start register: ", type(start_register))
    if(start_register == 0):
        SLAVE_ADDRESS = values
    if(start_register == 1):
        UART_BAUD_RATE = values
    if(start_register == 2):
        UART_DATA_BITS = values
    if(start_register == 3):
        UART_STOP_BITS = values
    if(start_register == 4):
        UART_PARITY = values
    if(start_register == 5):
        DEBOUNCE_DURATION = values
    if(start_register == 6):
        MSB_BUTTON_1, LSB_BUTTON_1 = separateNumber(BUTTON_COUNTER_1)
        MSB_BUTTON_1 = values
        BUTTON_COUNTER_1 = formDecAddress(MSB_BUTTON_1, LSB_BUTTON_1)
    if(start_register == 7):
        MSB_BUTTON_1, LSB_BUTTON_1 = separateNumber(BUTTON_COUNTER_1)
        LSB_BUTTON_1 = values
        BUTTON_COUNTER_1 = formDecAddress(MSB_BUTTON_1, LSB_BUTTON_1)        
    if(start_register == 8):
        MSB_BUTTON_2, LSB_BUTTON_2 = separateNumber(BUTTON_COUNTER_2)
        MSB_BUTTON_2 = values
        BUTTON_COUNTER_2 = formDecAddress(MSB_BUTTON_2, LSB_BUTTON_2)         
    if(start_register == 9):
        MSB_BUTTON_2, LSB_BUTTON_2 = separateNumber(BUTTON_COUNTER_2)
        LSB_BUTTON_2 = values
        BUTTON_COUNTER_2 = formDecAddress(MSB_BUTTON_2, LSB_BUTTON_2)                 
    if(start_register == 10):
        TIME_ACTIVE_MSB, TIME_ACTIVE_LSB = separateNumber(TIME_ACTIVE)
        TIME_ACTIVE_MSB = values
        TIME_ACTIVE = formDecAddress(TIME_ACTIVE_MSB, TIME_ACTIVE_LSB)    
    if(start_register == 11):
        TIME_ACTIVE_MSB, TIME_ACTIVE_LSB = separateNumber(TIME_ACTIVE)
        TIME_ACTIVE_LSB = values
        TIME_ACTIVE = formDecAddress(TIME_ACTIVE_MSB, TIME_ACTIVE_LSB)        
        
#Validate the command from master
def validateResponse(data):
    #Print received command
#     print("Command: ", data[0:9]) 
    
# #     print and check
#     print("Slave Address: ", slave_address)
#     print("function_code: ", function_code)
#     print("start_register_high: ", start_register_high)
#     print("start_register_low: ", start_register_low)
#     print("value or count high: ", register_count_high)
#     print("value or count low: ", register_count_low)
#     print("recv_crc_1: ", recv_crc_1)
#     print("recv_crc_2: ", recv_crc_2)
    
    # Compute the received and expected CRCs
    recv_crc = (hex(formDecAddress(data[7], data[6])))[2:] #extract crc from command
    command = bytearray(data[0:6], "utf-16") # Convert command to bytearray
    expect_crc = hex(crc16(command))[2:] # Calculate crc from command
#     print(recv_crc, " vs ", expect_crc) # Compare both CRCs
    
    # Compute the start register address
    start_register = formDecAddress(data[2], data[3])

    # Check slave address
    if data[0] != SLAVE_ADDRESS:
        print("Slave error called")
        resp = create_exception_resp(data, SLAVE_ERROR)
        return resp
    
    # Check matching CRC
    if(recv_crc != expect_crc):
        print("CRC isn't matching")
        resp = create_exception_resp(data, CRC_ERROR)
        return resp
    
    # Check function code    
    if not (1 <= data[1] < 7):
        print("Wrong function code: ", data[1])
        resp = create_exception_resp(data, ILLEGAL_FUNCTION)
        return resp
    
    #Check register length to avoid wrong addressing
    register_length = REG_LENGTHS[data[1]]    
    if not (0 <= start_register <= register_length):
        print("Wrong starting address")
        resp = create_exception_resp(data, ILLEGAL_ADDRESS)
        return resp
    
    # Check function code and validate accordingly
    if(data[1] == 0x01 or data[1] == 0x02):
        if not (0 <= formDecAddress(data[4], data[5]) <= 8):
            print("Wrong bit count")
            resp = create_exception_resp(data, ILLEGAL_DATA)
            return resp
        return None

    # Check function code and validate accordingly
    if(data[1] == 0x03 or data[1] == 0x04):
        register_count = formDecAddress(data[4], data[5])
        if not (0 <= register_count and (register_count + start_register) <= register_length):
            print("Wrong register count")
            resp = create_exception_resp(data, ILLEGAL_DATA)
            return resp
        return None
    
    # Check function code and validate accordingly    
    if(data[1] == 0x05 or data[1] == 0x06):
        values = formDecAddress(data[4], data[5])    
        if not (values >= 0):
            print("Wrong value impended")
            resp = create_exception_resp(data, ILLEGAL_ADDRESS)
            return resp
        return None
    
    else: return None

# Function to handle Modbus requests
def handleRequest(data):
    global coil_single
    global discrete_input_single
    
    # Unpack slave address and function code from command
    slave_address, function_code = ustruct.unpack(">BB", data[0:2])
    
    if(function_code == 0x01 or function_code == 0x02):
        start_coil_high, start_coil_low, coil_count_high, coil_count_low, recv_crc_1, recv_crc_2 = ustruct.unpack(">BBBBBB", data[2:8])
        start_coil = formDecAddress(start_coil_high, start_coil_low) # Compute the start register address
        coil_count = formDecAddress(coil_count_high, coil_count_low)
    
    # Unpack register address and register count or value and crc for reading registers
    if(function_code == 0x03 or function_code == 0x04):
        start_register_high, start_register_low, register_count_high, register_count_low, recv_crc_1, recv_crc_2 = ustruct.unpack(">BBBBBB", data[2:8])
        start_register = formDecAddress(start_register_high, start_register_low) # Compute the start register address
        register_count = formDecAddress(register_count_high, register_count_low)
        
    # Unpack register address and register count or value and crc
    if(function_code == 0x05 or function_code == 0x06):
        start_register_high, start_register_low, value_high, value_low, recv_crc_1, recv_crc_2 = ustruct.unpack(">BBBBBB", data[2:8])
        start_register = formDecAddress(start_register_high, start_register_low) # Compute the start register address
        values = formDecAddress(value_high, value_low)

    # Handle read coil request
    if function_code == READ_COILS:
        response = ustruct.pack(">BBB", slave_address, function_code, coil_count) #Coil count is either 1 or 2 for our case
        coil_values = 0b00
        for bit_index in range(coil_count):
            if isSet(coil_single, bit_index):
                coil_values += 2 ** bit_index
        response += ustruct.pack(">B", coil_values)        
        # Send Modbus RTU response
        return response
    
    # Handle read discrete inputs request
    elif function_code == READ_DISCRETE_INPUTS:
        response = ustruct.pack(">BBB", slave_address, function_code, coil_count) #Coil count is either 1 or 2 for our case
        discrete_input_values = 0b00
        for bit_index in range(coil_count):
            if isSet(discrete_input_single, bit_index):
                discrete_input_values += 2 ** bit_index
        response += ustruct.pack(">B", discrete_input_values)      
        # Send Modbus RTU response
        return response

    # Handle read holding register request
    elif function_code == READ_HOLDING_REGISTERS: 
        response = ustruct.pack(">BBB", slave_address, function_code, (register_count * 2))
        for i in range(register_count):
            if holding_registers[(start_register + i)] == None:
                holding_registers[(start_register + i)] = 0
            response += (ustruct.pack(">H", holding_registers[(start_register + i)]))      
        # Send Modbus RTU response
        return response
    
    # Handle read holding register request
    elif function_code == READ_INPUT_REGISTERS:
        response = ustruct.pack(">BBB", slave_address, function_code, (register_count * 2))
        for i in range(register_count):
            response += (ustruct.pack(">H", input_registers[(start_register + i)]))
        # Send Modbus RTU response
        return response

    # Handle write single coil request
    elif function_code == WRITE_SINGLE_COIL:
        mask_1 = 0b00000001 << start_register
        # Extract coil value
#         print("Coil value: ", values)
#         print("Coil value: ", coil_single)
#         print("Coil mask: ", mask_1)
        if values != 0:
            coil_single |= mask_1
        else:
            mask_1 = ~mask_1
            coil_single &= mask_1
        
#         print("Coil value after: ", coil_single)
        # Send Modbus RTU response
        return data[0:6]

    # Handle write single register request
    elif function_code == WRITE_HOLDING_REGISTER:
        # Extract register value
        holding_registers[start_register] = int.from_bytes(ustruct.pack(">H", values), 'big')
        changeCorrespondingVariable(start_register, values)
        response = ustruct.pack(">BBBB", slave_address, function_code, start_register, values)
        # Send Modbus RTU response
        return data[0:6]
    
    # Unsupported function code
    else:
        return None

# Update the holding register for button 1
def updateHoldingRegisterButton1(MSB, LSB):
    global holding_registers
    holding_registers[0x06] = MSB
    holding_registers[0x07] = LSB
    
# Update the holding register for button 2
def updateHoldingRegisterButton2(MSB, LSB):
    global holding_registers
    holding_registers[0x08] = MSB
    holding_registers[0x09] = LSB
    
# Update the holding register for button 1
def updateHoldingRegisterTimeActive(MSB, LSB):
    global holding_registers
    holding_registers[0x0A] = MSB
    holding_registers[0x0B] = LSB
    
# Update the input register
def updateInputRegister():
    global input_registers
    global holding_registers
    input_registers[0x00] = holding_registers[0x06]
    input_registers[0x01] = holding_registers[0x07]
    input_registers[0x02] = holding_registers[0x08]
    input_registers[0x03] = holding_registers[0x09]
    input_registers[0x04] = holding_registers[0x0A]
    input_registers[0x05] = holding_registers[0x0B]

#Read two coil bits and change pin outputs accordingly
def coilPinOutChange(coil_1, coil_2, coil_single):

    if(coil_single == 1):
        coil_1.value(1)
        coil_2.value(0)
    elif(coil_single == 2):
        coil_1.value(0)
        coil_2.value(1)
    elif(coil_single == 3):
        coil_1.value(1)
        coil_2.value(1)
    else :
        coil_1.value(0)
        coil_2.value(0)
        
    print("Coils 1: ", coil_1.value(), " and Coil 2: ", coil_2.value())

#Function executed upon button press and further execs debounce, counter increments and updates holding registers
def buttonChange(button_1, button_2):
        global discrete_input_single
        global holding_registers
        global BUTTON_COUNTER_1
        global BUTTON_COUNTER_2 
    
    # If button 1 is pressed, debounce the press, change input status and update button count value in holding register
        if button_1.isPressed():
            discrete_input_single |= 0b00000001
            BUTTON_COUNTER_1 += button_1.checkPressCount()
            BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB = separateNumber(BUTTON_COUNTER_1)
            updateHoldingRegisterButton1(BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB)   
        elif (not button_1.isPressed()):
            discrete_input_single &= 0b11111110      
        else : pass
    
    # If button 2 is pressed, debounce the press, change input status and update button count value in holding register
        if button_2.isPressed():
            discrete_input_single |= 0b00000010
            BUTTON_COUNTER_2 += button_2.checkPressCount()
            BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB = separateNumber(BUTTON_COUNTER_2)
            updateHoldingRegisterButton2(BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB)
        elif(not button_2.isPressed()):
            discrete_input_single &= 0b11111101
        else : pass

def main():
    try:
        # Initialize output pins for coils and buttons 
        button_1 = DebounceButton(Pin.PB_09, DEBOUNCE_DURATION)
        button_2 = DebounceButton(Pin.PB_10, DEBOUNCE_DURATION)
        coil_2 = Pin(Pin.PB_08, Pin.OUT, Pin.PULL_DOWN)
        coil_1 = Pin(Pin.PB_07, Pin.OUT, Pin.PULL_DOWN)
    
        # Initialize UART
        uart = UART(1)
        uart.init(baudrate = UART_BAUD_RATE, bits=UART_DATA_BITS,
            stop=UART_STOP_BITS, parity=UART_PARITY)
    
        while True:
            # Wait for Modbus request
            response_data = 0
            
            # Check if there's any data available for reading on UART
            # If available read it
            if uart.any():
                data = uart.read()
#                 print("Data from uart: ", data)
                # If anything was read from UART, validate and parse it from validateResponse() and send it to handleRequest()
                if data is not None:
                    # Send the received command for validation checks. If no error is found, return None else return the exception response
                    response_error = validateResponse(data)
                    
                    if response_error is None:
                        # Compute the response for the command from master
                        response_data = handleRequest(data) # Initial part of response
                        crc = reverseCRC(crc16(response_data)) # Compute the CRC for response and reverse it 
                        response = bytearray(response_data) # Convert response to a bytearray
                        response.extend(crc) # Append the CRC 
#                         print("Response = ", response)
                        uart.write(response) # Write response to the UART
                        # Change coil state on register update
                        if(data[1] == WRITE_SINGLE_COIL):
                            coilPinOutChange(coil_1, coil_2, coil_single)
                                 
                    else:
                        crc_rev = crc16(response_error)
                        crc = reverseCRC(crc_rev)
#                         print("crc: ", crc)
                        response_error_bytes = bytearray(response_error)
                        response_error_bytes.extend(crc)
#                         print("Response Error = ", response_error_bytes)
                        uart.write(response_error_bytes)
                        response = None
                            # Calculate the time active and separate it to two for register
            
                msb_time, lsb_time = calculateTimeActive()
                updateHoldingRegisterTimeActive(msb_time, lsb_time)
                #Check buttons and update on press
                buttonChange(button_1, button_2)
                updateInputRegister()
                gc.collect()
                
    except KeyboardInterrupt as e:
        print("No more modbus")
    
# Run the main function when the script is executed
if __name__ == "__main__":
    main()