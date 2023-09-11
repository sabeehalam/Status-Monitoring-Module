import ustruct
from machine import UART, Pin
import array
import time
import re
import json
import os
from button_debounce import DebounceButton
import const
import num

# Set default config to file in JSON
def setDefaultConfig():
    variables = {"SLAVE_ADDRESS": 1, "UART_BAUD_RATE":9600, "UART_DATA_BITS":8,"UART_STOP_BITS":1, "UART_PARITY":None, "DEBOUNCE_DURATION":100,"BUTTON_COUNTER_1":0, "BUTTON_COUNTER_2":0, "TIME_ACTIVE":0}
    var_string = json.dumps(variables)
    print(var_string)
    with open("variables.txt", "w") as file:
        file.write(var_string)

#load variables from a text file to a dictionary
def loadVariables():
    try:
        with open("variables.txt", "r") as file:
            load_string = file.read()
        print(load_string)
        load_string = load_string.replace("null", "None")
        loaded_vars = eval(load_string)
        return loaded_vars
    except (OSError, TypeError, ValueError, AttributeError, SyntaxError) as error:
        print("Didnt find variable file")
        setDefaultConfig()
        with open("variables.txt", "r") as file:
            load_string = file.read()
        load_string = load_string.replace("null", "None")
        loaded_vars = eval(load_string)
        return loaded_vars

loaded_vars = loadVariables()
print(loaded_vars)
print(type(loaded_vars))

# Define slave address
SLAVE_ADDRESS = loaded_vars['SLAVE_ADDRESS']

# Define UART parameters
UART_BAUD_RATE = loaded_vars["UART_BAUD_RATE"]
UART_DATA_BITS = loaded_vars["UART_DATA_BITS"]
UART_STOP_BITS = loaded_vars["UART_STOP_BITS"]
UART_PARITY    = loaded_vars["UART_PARITY"]

#Counter variables for push buttons
DEBOUNCE_DURATION = loaded_vars["DEBOUNCE_DURATION"]
BUTTON_COUNTER_1  = loaded_vars["BUTTON_COUNTER_1"]
BUTTON_COUNTER_2  = loaded_vars["BUTTON_COUNTER_2"]
MSB_BUTTON_1, LSB_BUTTON_1 = 0, 0
MSB_BUTTON_2, LSB_BUTTON_2 = 0, 0

#variables for time
TIME_START  = time.time()
TIME_ACTIVE = time.time()
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
    0x04: 0,  # Read-Only Use for future epoch (msb)
    0x05: 0,  # Read-Only Use for future epoch (lsb)
    }

REG_LENGTHS = {
    0x01: 8,
    0x02: 8,
    0x03: len(holding_registers),
    0x04: len(input_registers),
    0x05: 8,
    0x06: len(holding_registers),
    0x07: 0,
    0x08: 0
    }

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
        print("Debounce Duration: ", DEBOUNCE_DURATION)
    if(start_register == 6):
        MSB_BUTTON_1, LSB_BUTTON_1 = num.separateNumber(BUTTON_COUNTER_1)
        MSB_BUTTON_1 = values
        BUTTON_COUNTER_1 = num.formDecAddress(MSB_BUTTON_1, LSB_BUTTON_1)
    if(start_register == 7):
        MSB_BUTTON_1, LSB_BUTTON_1 = num.separateNumber(BUTTON_COUNTER_1)
        LSB_BUTTON_1 = values
        BUTTON_COUNTER_1 = num.formDecAddress(MSB_BUTTON_1, LSB_BUTTON_1)        
    if(start_register == 8):
        MSB_BUTTON_2, LSB_BUTTON_2 = num.separateNumber(BUTTON_COUNTER_2)
        MSB_BUTTON_2 = values
        BUTTON_COUNTER_2 = num.formDecAddress(MSB_BUTTON_2, LSB_BUTTON_2)         
    if(start_register == 9):
        MSB_BUTTON_2, LSB_BUTTON_2 = num.separateNumber(BUTTON_COUNTER_2)
        LSB_BUTTON_2 = values
        BUTTON_COUNTER_2 = num.formDecAddress(MSB_BUTTON_2, LSB_BUTTON_2)                 
    if(start_register == 10):
        TIME_ACTIVE_MSB, TIME_ACTIVE_LSB = num.separateNumber(TIME_ACTIVE)
        TIME_ACTIVE_MSB = values
        TIME_ACTIVE = num.formDecAddress(TIME_ACTIVE_MSB, TIME_ACTIVE_LSB)    
    if(start_register == 11):
        TIME_ACTIVE_MSB, TIME_ACTIVE_LSB = num.separateNumber(TIME_ACTIVE)
        TIME_ACTIVE_LSB = values
        TIME_ACTIVE = num.formDecAddress(TIME_ACTIVE_MSB, TIME_ACTIVE_LSB)
    
    updateJSON()

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
            BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB = num.separateNumber(BUTTON_COUNTER_1)
            updateHoldingRegisterButton1(BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB)   
        elif (not button_1.isPressed()):
            discrete_input_single &= 0b11111110      
        else : pass
    
    # If button 2 is pressed, debounce the press, change input status and update button count value in holding register
        if button_2.isPressed():
            discrete_input_single |= 0b00000010
            BUTTON_COUNTER_2 += button_2.checkPressCount()
            BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB = num.separateNumber(BUTTON_COUNTER_2)
            updateHoldingRegisterButton2(BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB)
        elif(not button_2.isPressed()):
            discrete_input_single &= 0b11111101
        else : pass

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
    
# Calculate the time active and separate it to two for register
def calculateTimeActive():
    global TIME_NOW
    global TIME_ACTIVE
    if (time.time() != TIME_NOW):
        TIME_NOW =  time.time()
        TIME_ACTIVE += 1
#         print("Time Active: ", TIME_ACTIVE)
        return num.separateNumber(TIME_ACTIVE)
    else: return num.separateNumber(TIME_ACTIVE)
    
# Update file in JSON
def updateJSON():
    global SLAVE_ADDRESS
    global UART_BAUD_RATE
    global UART_DATA_BITS
    global UART_STOP_BITS
    global UART_PARITY
    global DEBOUNCE_DURATION
    global BUTTON_COUNTER_1
    global BUTTON_COUNTER_2
    global TIME_ACTIVE
    
    variables = {"SLAVE_ADDRESS": SLAVE_ADDRESS, "UART_BAUD_RATE":UART_BAUD_RATE, "UART_DATA_BITS":UART_DATA_BITS,
                 "UART_STOP_BITS":UART_STOP_BITS, "UART_PARITY":UART_PARITY,"DEBOUNCE_DURATION":DEBOUNCE_DURATION,
                 "BUTTON_COUNTER_1":BUTTON_COUNTER_1, "BUTTON_COUNTER_2":BUTTON_COUNTER_2, "TIME_ACTIVE":TIME_ACTIVE
                 }
    
    var_string = json.dumps(variables)

    with open("variables.txt", "w") as file:
        file.write(var_string)
