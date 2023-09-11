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
        vars_regs.loadVariables()
        # Initialize output pins for coils and buttons 
        button_1 = DebounceButton(Pin.PB_09, vars_regs.DEBOUNCE_DURATION)
        button_2 = DebounceButton(Pin.PB_10, vars_regs.DEBOUNCE_DURATION)
        coil_2 = Pin(Pin.PB_08, Pin.OUT, Pin.PULL_DOWN)
        coil_1 = Pin(Pin.PB_07, Pin.OUT, Pin.PULL_DOWN)
        counter = 0 # for activity check (resets when data is sent)
        relay_status = 0
        last_message_time = time.time()
    
        # Initialize UART
        uart = UART(1)
        uart.init(baudrate = vars_regs.UART_BAUD_RATE, bits=vars_regs.UART_DATA_BITS,
            stop=vars_regs.UART_STOP_BITS, parity=vars_regs.UART_PARITY)
    
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
                    response_error = validate.validateResponse(data)
                    
                    if response_error is None:
                        # Compute the response for the command from master
                        response_data = handle_request.handleRequest(data) # Initial part of response
                        crc = crc_calc.reverseCRC(crc_calc.crc16(response_data)) # Compute the CRC for response and reverse it 
                        response = bytearray(response_data) # Convert response to a bytearray
                        response.extend(crc) # Append the CRC 
                        print("Response = ", response)
                        uart.write(response) # Write response to the UART
                        # Change coil state on register update
                        if(data[1] == const.WRITE_SINGLE_COIL):
                            vars_regs.coilPinOutChange(coil_1, coil_2, vars_regs.coil_single)
                                 
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
                
            msb_time, lsb_time = vars_regs.calculateTimeActive()
            vars_regs.updateHoldingRegisterTimeActive(msb_time, lsb_time)
            # Check buttons and update on press
            vars_regs.buttonChange(button_1, button_2)
            vars_regs.updateInputRegister()
            vars_regs.updateJSON()
            gc.collect()
                
    except KeyboardInterrupt as e:
        print("No more modbus")
    
# Run the main function when the script is executed
if __name__ == "__main__":
    main() 

