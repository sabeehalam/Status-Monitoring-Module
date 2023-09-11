import ustruct

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

#Swap bytes for CRC 
def reverseCRC(crc):
    crc_low, crc_high = divmod(crc, 0x100)
#     print("crc ordered", crc)
    return ustruct.pack(">BB", crc_high, crc_low)
