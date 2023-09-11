import ustruct
import machine
from machine import Pin
import const
import vars_regs
import num

# Function to handle Modbus requests
def handleRequest(data, coil_single, discrete_input_single, input_register, holding_register): 
    
    # Unpack slave address and function code from command
    slave_address, function_code = ustruct.unpack(">BB", data[0:2])
    
    # Unpack register address and register count or value and crc for reading registers
    if(function_code == 0x01 or function_code == 0x02 or function_code == 0x03 or function_code == 0x04):
        start_register_high, start_register_low, register_count_high, register_count_low, recv_crc_1, recv_crc_2 = ustruct.unpack(">BBBBBB", data[2:8])
        start_register = num.formDecAddress(start_register_high, start_register_low) # Compute the start register address
        register_count = num.formDecAddress(register_count_high, register_count_low)       
    # Unpack register address and register count or value and crc
    if(function_code == 0x05 or function_code == 0x06):
        start_register_high, start_register_low, value_high, value_low, recv_crc_1, recv_crc_2 = ustruct.unpack(">BBBBBB", data[2:8])
        start_register = num.formDecAddress(start_register_high, start_register_low) # Compute the start register address
        values = num.formDecAddress(value_high, value_low)
        
    if(function_code == 0x07):
        vars_regs.setDefaultConfig()
        machine.reset()
    
    if(function_code == 0x08):
        machine.reset()

    # Handle read coil request
    if function_code == const.READ_COILS:
        response = ustruct.pack(">BBB", slave_address, function_code, register_count) #Coil count is either 1 or 2 for our case
        coil_values = 0b00
        for bit_index in range(start_register + register_count):
            if num.isSet(coil_single, start_register + bit_index):
                coil_values += 2 ** bit_index
        response += ustruct.pack(">B", coil_values)        
        # Send Modbus RTU response
        return response, coil_single, discrete_input_single, input_register, holding_register
    
    # Handle read discrete inputs request
    elif function_code == const.READ_DISCRETE_INPUTS:
        response = ustruct.pack(">BBB", slave_address, function_code, register_count) #Coil count is either 1 or 2 for our case
        discrete_input_values = 0b00
        for bit_index in range(start_register + register_count):
            if num.isSet(discrete_input_single, start_register + bit_index):
                discrete_input_values += 2 ** bit_index
        response += ustruct.pack(">B", discrete_input_values)      
        # Send Modbus RTU response
        return response, coil_single, discrete_input_single, input_register, holding_register

    # Handle read holding register request
    elif function_code == const.READ_HOLDING_REGISTERS: 
        response = ustruct.pack(">BBB", slave_address, function_code, (register_count * 2))
        for i in range(register_count):
            if holding_register[(start_register + i)] == None:
                holding_register[(start_register + i)] = 0
            response += (ustruct.pack(">H", holding_register[(start_register + i)]))      
        # Send Modbus RTU response
        return response, coil_single, discrete_input_single, input_register, holding_register
    
    # Handle read holding register request
    elif function_code == const.READ_INPUT_REGISTERS:
        response = ustruct.pack(">BBB", slave_address, function_code, (register_count * 2))
        for i in range(register_count):
            response += (ustruct.pack(">H", input_register[(start_register + i)]))
        # Send Modbus RTU response
        return response, coil_single, discrete_input_single, input_register, holding_register

    # Handle write single coil request
    elif function_code == const.WRITE_SINGLE_COIL:
        mask_1 = 0b00000001 << start_register
        if values != 0:
            print(type(coil_single))
            coil_single = coil_single | mask_1
        else:
            print(type(coil_single))
            mask_1 = ~mask_1
            coil_single = coil_single & mask_1
        
        response =  data[0:5] + b'0xff'
        # Send Modbus RTU response
        return response, coil_single, discrete_input_single, input_register, holding_register

    # Handle write single register request
    elif function_code == const.WRITE_HOLDING_REGISTER:
        # Extract register value
        holding_register[start_register] = int.from_bytes(ustruct.pack(">H", values), 'big')
        print("Changed Register:", start_register, " Values: ", values)
        input_register, holding_register = vars_regs.changeCorrespondingVariable(start_register, values, input_register, holding_register)
        response = ustruct.pack(">BBBB", slave_address, function_code, start_register, values)
        # Send Modbus RTU response
        return data[0:6], coil_single, discrete_input_single, input_register, holding_register
    
    # Unsupported function code
    else:
        return None
