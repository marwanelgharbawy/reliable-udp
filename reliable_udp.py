import socket
import struct

class ReliableUDP:
    def __init__(self, host, port, is_server=False):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
        
        # unsigned int for seq_num, unsigned int for ack_num, unsigned char for 3 flags, unsigned short for checksum
        self.header_format = '!I I B H'
        
        self.sock.settimeout(1.0) 
        
        # if not server, no need to bind
        if is_server:
            self.sock.bind((self.host, self.port))
            
    def sendto(self, data, address):
        pass
    
    def recvfrom(self, buffer_size):
        pass

    def _calculate_checksum(self, data: bytes) -> int:
        
        # if number of bytes is odd, add a zero byte to make it even
        if len(data) % 2 != 0:
            data += b'\0'
            
        checksum = 0
        
        # process data in words (2 bytes)
        for i in range(0, len(data), 2):
            word = (data[i] << 8) + data[i+1]
            checksum += word
            checksum = (checksum & 0xffff) + (checksum >> 16) # add overflow bits while masking to 16 bits
            
        return ~checksum & 0xffff

    # private method
    def _create_packet(self, seq_num, ack_num, flags, data=b''):
        # packet structure: header + data
        # header: seq_num, ack_num, flags, checksum (needs to be calculated)
        temp_header = struct.pack(self.header_format, seq_num, ack_num, flags, 0)
        checksum = self._calculate_checksum(temp_header + data)
        header = struct.pack(self.header_format, seq_num, ack_num, flags, checksum)
        return header + data

    def _parse_packet(self, packet):
        header_size = struct.calcsize(self.header_format)
        
        # if packet is too short to contain a valid header, then it's invalid
        if len(packet) < header_size:
            return None 
            
        # parse header and data
        header = packet[:header_size]
        data = packet[header_size:]
        
        # unpack using the same format as packing to get header data
        seq_num, ack_num, flags, recv_checksum = struct.unpack(self.header_format, header)
        return seq_num, ack_num, flags, recv_checksum, data