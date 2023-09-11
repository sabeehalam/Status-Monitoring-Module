import ustruct
from machine import UART, Pin
import time
import json
from button import DebounceButton
import num

# Set default config to file in JSON
def setDefaultConfig():
    variables = {"SLAVE_ADDRESS": 1, "UART_BAUD_RATE":9600, "UART_DATA_BITS":8,"UART_STOP_BITS":1, "UART_PARITY":None, "DEBOUNCE_DURATION":150,"BUTTON_COUNTER_1":0, "BUTTON_COUNTER_2":0, "TIME_ACTIVE":0}
    json_object = json.dumps(variables)
    with open("variables.json", "w") as file:
#         file.write(json_object)
        json.dump(json_object, file)
    print(json_object, "is saved")

def loadVariables():
    try:
        with open("variables.json", "r") as file:
            loaded_vars = json.load(file)
            loaded_vars = json.loads(loaded_vars)
            return loaded_vars
    except (OSError, TypeError, ValueError, AttributeError) as error:
        print("Didnt find JSON file")
        setDefaultConfig()
        with open("variables.json", "r") as file:
            loaded_vars = json.load(file)
            loaded_vars = json.loads(loaded_vars)
            return loaded_vars

def assignParams(loaded_parameters):
    print("Before declaration: ", loaded_parameters)
    MSB_BUTTON_1, LSB_BUTTON_1 = num.separateNumber(loaded_parameters["BUTTON_COUNTER_1"])
    MSB_BUTTON_2, LSB_BUTTON_2 = num.separateNumber(loaded_parameters["BUTTON_COUNTER_2"])

    #variables for time
    TIME_START  = time.time()
    TIME_ACTIVE = 0
    TIME_ACTIVE_MSB, TIME_ACTIVE_LSB = 0,0
    TIME_NOW    = 0

    coil_single = 0b00 # Starting address for relay 1 and 2 
    discrete_input_single = 0b00 #For button/ relay status
    
    if loaded_parameters["UART_PARITY"] == 0:
       loaded_parameters["UART_PARIRT"] = None 
    
    holding_register = {
        0x00: loaded_parameters['SLAVE_ADDRESS'], #slave id
        0x01: loaded_parameters["UART_BAUD_RATE"], #baud rate constant
        0x02: loaded_parameters["UART_DATA_BITS"], # data bits
        0x03: loaded_parameters["UART_STOP_BITS"], #stop bits
        0x04: loaded_parameters["UART_PARITY"], #parity bits
        0x05: loaded_parameters["DEBOUNCE_DURATION"], #debounce duration
        0x06: 0, # Write only Button 1 counter MSB 
        0x07: 0, # Write only Button 1 counter LSB
        0x08: 0, # Write only Button 2 counter MSB
        0x09: 0, # Write only Button 2 counter LSB
        0x0A: 0, # Write only Time Active MSB
        0x0B: 0, # Write only Time Active LSB
        }

    input_register = {
        0x00: MSB_BUTTON_1,  # Read only integers for button count 1 (msb)
        0x01: LSB_BUTTON_1,  # Read-Only Integers for button count 1 (lsb)
        0x02: MSB_BUTTON_2,  # Read-Only Integers for button count 2 (msb)
        0x03: LSB_BUTTON_2,  # Read-Only Integers for button count 2 (msb)
        0x04: TIME_ACTIVE_MSB,  # Read-Only Use for future epoch (msb)
        0x05: TIME_ACTIVE_LSB,  # Read-Only Use for future epoch (lsb)
        }

    reg_lengths = {
        0x01: 8,
        0x02: 8,
        0x03: len(holding_register),
        0x04: len(input_register),
        0x05: 8,
        0x06: len(holding_register),
        0x07: 0,
        0x08: 0
        }
    
    print("After declaration: ", holding_register)
    return coil_single, discrete_input_single, input_register, holding_register, reg_lengths

# Change the corresponding variable according to the writeHoldingRegister function
def changeCorrespondingVariable(start_register, values, input_register, holding_register):
    
#     print("Start register: ", type(start_register))
    if(start_register == 0):
        holding_register[0x00] = values
    if(start_register == 1):
        holding_register[0x01] = values
    if(start_register == 2):
        holding_register[0x02] = values
    if(start_register == 3):
        holding_register[0x03] = values
    if(start_register == 4):
        holding_register[0x04] = values
    if(start_register == 5):
        holding_register[0x05] = values
    if(start_register == 6):
        BUTTON_1_COUNTER = values
        input_register[0x00], input_register[0x01] = num.separateNumber(BUTTON_1_COUNTER)
    if(start_register == 7):
        BUTTON_1_COUNTER = values
        input_register[0x00], input_register[0x01] = num.separateNumber(BUTTON_1_COUNTER)     
    if(start_register == 8):
        BUTTON_2_COUNTER = values
        input_register[0x02], input_register[0x03] = num.separateNumber(BUTTON_2_COUNTER)       
    if(start_register == 9):
        BUTTON_2_COUNTER = values
        input_register[0x02], input_register[0x03] = num.separateNumber(BUTTON_2_COUNTER)                 
    if(start_register == 10):
        TIME_ACTIVE = values
        input_register[0x04], input_register[0x05] = num.separateNumber(TIME_ACTIVE)     
    if(start_register == 11):
        TIME_ACTIVE = values
        input_register[0x04], input_register[0x05] = num.separateNumber(TIME_ACTIVE)     
    
    updateJSON(holding_register, input_register)
    
    return input_register, holding_register

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
#     print("Coils 1: ", coil_1.value(), " and Coil 2: ", coil_2.value())

# #Function executed upon button press and further execs debounce, counter increments and updates holding registers
# def buttonChange(button_1, button_2):
#         global discrete_input_single
#         global holding_register
#         global BUTTON_COUNTER_1
#         global BUTTON_COUNTER_2 
#     
#     # If button 1 is pressed, debounce the press, change input status and update button count value in holding register
#         if button_1.isPressed():
#             discrete_input_single |= 0b00000001
#             BUTTON_COUNTER_1 += button_1.checkPressCount()
#             BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB = num.separateNumber(BUTTON_COUNTER_1)
#             updateHoldingRegisterButton1(BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB)   
#         elif (not button_1.isPressed()):
#             discrete_input_single &= 0b11111110      
#         else : pass
#     
#     # If button 2 is pressed, debounce the press, change input status and update button count value in holding register
#         if button_2.isPressed():
#             discrete_input_single |= 0b00000010
#             BUTTON_COUNTER_2 += button_2.checkPressCount()
#             BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB = num.separateNumber(BUTTON_COUNTER_2)
#             updateHoldingRegisterButton2(BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB)
#         elif(not button_2.isPressed()):
#             discrete_input_single &= 0b11111101
#         else : pass
#         
def button1Change(button_1, discrete_input_single, BUTTON_COUNTER_1):
    discrete_input_single |= 0b00000001
    BUTTON_COUNTER_1 += button_1.checkPressCount()
    return BUTTON_COUNTER_1
    
def button2Change(button_2, discrete_input_single, BUTTON_COUNTER_2):
    discrete_input_single |= 0b00000010
    BUTTON_COUNTER_2 += button_2.checkPressCount()
    return BUTTON_COUNTER_2
    
# Update the holding register for button 1
def updateInputRegisterButton1(MSB, LSB, input_register):
    input_registers[0x00] = MSB
    input_registers[0x01] = LSB
    return input_register
    
# Update the holding register for button 2
def updateInputRegisterButton2(MSB, LSB, input_register):
    input_registers[0x02] = MSB
    input_registers[0x03] = LSB
    return input_register

# Update the holding register for button 1
def updateInputRegisterTimeActive(MSB, LSB, input_register):
    input_register[0x04] = MSB
    input_register[0x05] = LSB
    return input_register

# Calculate the time active and separate it to two for register
def calculateTimeActive(TIME_NOW, TIME_ACTIVE):
    if (time.time() != TIME_NOW):
        TIME_NOW =  time.time()
        TIME_ACTIVE += 1
#         print("Time Active: ", TIME_ACTIVE)
        return TIME_NOW, TIME_ACTIVE
    else: return TIME_NOW, TIME_ACTIVE
    
# Update file in JSON
def updateJSON(holding_register, input_register):
    button_1_count = num.formDecAddress(input_register[0x00], input_register[0x01])
    button_2_count = num.formDecAddress(input_register[0x02], input_register[0x03])
    time_active = num.formDecAddress(input_register[0x04], input_register[0x05])

    if holding_register[0x04] == 0:
       holding_register[0x04] = None 
    
    variables = {"SLAVE_ADDRESS": holding_register[0x00], "UART_BAUD_RATE": holding_register[0x01], "UART_DATA_BITS":holding_register[0x02],
                 "UART_STOP_BITS": holding_register[0x03], "UART_PARITY": holding_register[0x04], "DEBOUNCE_DURATION": holding_register[0x05],
                 "BUTTON_COUNTER_1": button_1_count, "BUTTON_COUNTER_2": button_2_count, "TIME_ACTIVE": time_active
                 }
    json_object = json.dumps(variables)
    with open("variables.json", "w") as file:
        json.dump(json_object, file)

