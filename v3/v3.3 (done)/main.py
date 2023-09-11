import ustruct
from machine import UART, Pin
import time
import gc
from button import DebounceButton
import const
import validate
import vars_regs
import handle_request
import num
import crc_calc

def main():
    try:
        loaded_parameters = vars_regs.loadVariables()
        coil_single, discrete_input_single, input_register, holding_register, reg_lengths = vars_regs.assignParams(loaded_parameters)
        # Initialize output pins for coils and buttons 
        button_1 = DebounceButton(Pin.PB_09, holding_register[0x05])# 2nd value is debounce duration
        button_2 = DebounceButton(Pin.PB_10, holding_register[0x05])# 2nd value is debounce duration
        coil_2 = Pin(Pin.PB_08, Pin.OUT, Pin.PULL_DOWN)
        coil_1 = Pin(Pin.PB_07, Pin.OUT, Pin.PULL_DOWN)
        relay_time_counter = 0 # for activity check (resets when data is sent)
        relay_status = 0 # for activity check (resets when data is sent)
        last_message_time = time.time() # for activity check (resets when data is sent)
        TIME_NOW = time.time()
        TIME_ACTIVE = 0
        
        # Initialize UART
        uart = UART(1)
        uart.init(baudrate = holding_register[0x01], bits=holding_register[0x02],\
            stop=holding_register[0x03], parity=holding_register[0x04])
    
        while True:
            # Wait for Modbus request
            response_data = 0
            
            # Check if there's any data available for reading on UART
            # If available read it
            if uart.any():
                data = uart.read()
                last_message_time = time.time()
                
                if relay_status == 1:
                    coil_1.value(0)
                    relay_status = 0
                    
                print("Data from uart: ", data)
                # If anything was read from UART, validate and parse it from validateResponse() and send it to handleRequest()
                if data is not None:
                    # Send the received command for validation checks. If no error is found, return None else return the exception response
                    response_error = validate.validateResponse(data, holding_register, reg_lengths)
                    
                    if response_error is None:
                        # Compute the response for the command from master
                        response_data, coil_single, discrete_input_single, input_register, holding_register = handle_request.handleRequest(\
                                          data, coil_single, discrete_input_single, input_register, holding_register) # Initial part of response
                        crc = crc_calc.reverseCRC(crc_calc.crc16(response_data)) # Compute the CRC for response and reverse it 
                        response = bytearray(response_data) # Convert response to a bytearray
                        response.extend(crc) # Append the CRC 
                        print("Response = ", response)
                        uart.write(response) # Write response to the UART
                        # Change coil state on register update
                        if(data[1] == const.WRITE_SINGLE_COIL):
                            vars_regs.coilPinOutChange(coil_1, coil_2, coil_single)           
                    else:
                        crc_rev = crc_calc.crc16(response_error)
                        crc = crc_calc.reverseCRC(crc_rev)
#                         print("crc: ", crc)
                        response_error_bytes = bytearray(response_error)
                        response_error_bytes.extend(crc)
#                         print("Response Error = ", response_error_bytes)
                        uart.write(response_error_bytes)
                        response = None                
                             
            # Calculate the time active and separate it to two for register
            if relay_status != 1 and (time.time() - last_message_time)> 15:
                relay_status = 1
            
            #check relay status and change coil value accordingly
            if(relay_status == 1):
                coil_1.value(1)
            
            #Calculate the time the device has been active for
            TIME_NOW, TIME_ACTIVE= vars_regs.calculateTimeActive(TIME_NOW, TIME_ACTIVE)
            msb_time_active, lsb_time_active = num.separateNumber(TIME_ACTIVE)
            #Update the time active field in the holding register
            input_register = vars_regs.updateInputRegisterTimeActive(msb_time_active, lsb_time_active, input_register)
            
            # Check and update the tregisters based on button presses(for button 1).
            if button_1.isPressed():
                BUTTON_COUNTER_1 = vars_regs.button1Change(button_1, discrete_input_single, BUTTON_COUNTER_1)
                BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB = num.separateNumber(BUTTON_COUNTER_1)
                input_register = vars_regs.updateInputRegisterButton1(BUTTON_COUNTER_1_MSB, BUTTON_COUNTER_1_LSB, input_register)
            elif (not button_1.isPressed()):
                discrete_input_single &= 0b11111110      
            else : pass
            
            # Check and update the tregisters based on button presses(for button 1).
            if button_2.isPressed():
                BUTTON_COUNTER_2 = vars_regs.button2Change(button_2, discrete_input_single, BUTTON_COUNTER_2)
                BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB = num.separateNumber(BUTTON_COUNTER_2)
                input_register = vars_regs.updateInputRegisterButton2(BUTTON_COUNTER_2_MSB, BUTTON_COUNTER_2_LSB, input_register)
            elif (not button_2.isPressed()):
                discrete_input_single &= 0b11111101      
            else : pass
            
            vars_regs.updateJSON(holding_register, input_register)
            gc.collect()
    except KeyboardInterrupt as e:
        print("No more modbus")
    
# Run the main function when the script is executed
if __name__ == "__main__":
    main() 


