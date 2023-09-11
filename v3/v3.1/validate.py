import ustruct
from machine import UART, Pin
import array
import time
import gc
from button_debounce import DebounceButton
import const
import validate
import vars_regs
import handle_request
import num
import crc_calc

def create_exception_resp(request, exc_code):
    # Build Modbus exception response
    resp = ustruct.pack(">BBB", request[0], const.EXCEPTION_CODE, exc_code)
    return resp

#Validate the command from master
def validateResponse(data):
    #Print received command
#     print("Command: ", data[0:9]) 
    if len(data) > 8 :
        resp = create_exception_resp(data, const.ILLEGAL_LENGTH)
        return resp
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
    recv_crc = (hex(num.formDecAddress(data[7], data[6])))[2:] #extract crc from command
    command = bytearray(data[0:6], "utf-16") # Convert command to bytearray
    expect_crc = hex(crc_calc.crc16(command))[2:] # Calculate crc from command
#     print(recv_crc, " vs ", expect_crc) # Compare both CRCs
    
    # Compute the start register address
    start_register = num.formDecAddress(data[2], data[3])

    # Check slave address
    if data[0] != vars_regs.SLAVE_ADDRESS:
        print("Slave error called")
        resp = create_exception_resp(data, const.SLAVE_ERROR)
        return resp
    
    # Check matching CRC
    if(recv_crc != expect_crc):
        print("CRC isn't matching")
        resp = create_exception_resp(data, const.CRC_ERROR)
        return resp
    
    # Check function code    
    if not (1 <= data[1] <= 8):
        print("Wrong function code: ", data[1])
        resp = create_exception_resp(data, const.ILLEGAL_FUNCTION)
        return resp
    
    #Check register length to avoid wrong addressing
    register_length = vars_regs.REG_LENGTHS[data[1]]    
    if not (0 <= start_register <= register_length):
        print("Wrong starting address")
        resp = create_exception_resp(data, const.ILLEGAL_ADDRESS)
        return resp
    
    # Check function code and validate accordingly
    if(data[1] == 0x01 or data[1] == 0x02):
        if not (0 <= num.formDecAddress(data[4], data[5]) <= 8):
            print("Wrong bit count")
            resp = create_exception_resp(data, const.ILLEGAL_DATA)
            return resp
        return None

    # Check function code and validate accordingly
    if(data[1] == 0x03 or data[1] == 0x04):
        register_count = num.formDecAddress(data[4], data[5])
        if not (0 <= register_count and (register_count + start_register) <= register_length):
            print("Wrong register count")
            resp = create_exception_resp(data, const.ILLEGAL_DATA)
            return resp
        return None
    
    # Check function code and validate accordingly    
    if(data[1] == 0x05 or data[1] == 0x06):
        values = num.formDecAddress(data[4], data[5])    
        if not (values >= 0):
            print("Wrong value impended")
            resp = create_exception_resp(data, const.ILLEGAL_ADDRESS)
            return resp
        return None
    
    else: return None
