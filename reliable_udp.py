import socket
import struct
import random

class ReliableUDP:
    def __init__(self, host, port, is_server=False):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
        
        # unsigned int for seq_num (4 bytes)
        # unsigned int for ack_num (4 bytes)
        # unsigned char for 3 flags (1 byte)
        # unsigned short for checksum (2 bytes)
        self.header_format = '!I I B H'
        
        self.seq_num = 0
        self.ack_num = 0
        
        self.expected_seq_num = 0
        
        # simulation paramteres: packet loss probabilites and data corruption
        self.sock.settimeout(1.0) 
        self.packet_loss_prob = 0.1
        self.data_corruption_prob = 0.1
        
        # if not server, no need to bind
        if is_server:
            self.sock.bind((self.host, self.port))
            
    # takes data as bytes and address as (host, port)
    def sendto(self, data, address=None):
        if address is None:
            address = (self.host, self.port)
            
        packet = self._create_packet(self.seq_num, 0, 0, data)
        
        while True:
            
            if self._simulate_loss():
                pass # do nothing
            else:
                # simulate checksum corruption
                packet_to_send = self._simulate_false_checksum(packet)
                self.sock.sendto(packet_to_send, address)
            
            # block until ACK is received or timeout occurs
            try:
                ack_packet, _ = self.sock.recvfrom(1024)
                
                # receive ACK packet, parse it and verify checksum and ACK number
                parsed = self._parse_packet(ack_packet)
                
                if parsed:
                    recv_seq, recv_ack, flags, recv_checksum, data = parsed
                    
                    temp_header = struct.pack(self.header_format, recv_seq, recv_ack, flags, 0)
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    # compare checksum and ACK number for verification
                    # if verified, toggle 0 and 1 for seq_num (stop and wait protocol)
                    if calc_checksum == recv_checksum and recv_ack == self.seq_num:
                        self.seq_num = 1 - self.seq_num 
                        return
                    
            # if timeout occurs, resend packet
            except socket.timeout:
                continue
    
    def receive(self):
        while True:
            try:
                packet, address = self.sock.recvfrom(1024) # block until packet is received or timeout occurs
                parsed = self._parse_packet(packet)
                
                if parsed:
                    seq_num, ack_num, flags, recv_checksum, data = parsed
                    
                    temp_header = struct.pack(self.header_format, seq_num, ack_num, flags, 0)
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    # two checks required: checksum then sequence number
                    # otherwise wait for next packet
                    
                    if calc_checksum == recv_checksum:
                        
                        # send ACK packet with ACK flag set and ACK number equal to received seq_num
                        ack_packet = self._create_packet(0, seq_num, 1)
                        
                        # simulate ACK packet loss
                        if self._simulate_loss():
                            pass # do nothing
                        else:
                            self.sock.sendto(ack_packet, address)
                        
                        # if it's the expected sequence number
                        if seq_num == self.expected_seq_num:
                            self.expected_seq_num = 1 - self.expected_seq_num # toggle expected sequence number
                            return data, address
                        # else, it's duplicate packet
            except socket.timeout:
                continue
            
    def _simulate_packet_loss(self):
        return random.random() < self.packet_loss_prob
    
    # modify the checksum to simulate data corruption
    def _simulate_false_checksum(self, packet):
        if random.random() < self.data_corruption_prob:
            
            # change type of packet to bytearray then put it back to bytes after modification
            corrupted = bytearray(packet)
            
            # The checksum starts at byte index (4 + 4 + 1)
            # target the checksum byte and toggle the whole byte
            corrupted[9] ^= 0xFF 
            
            return bytes(corrupted)
        return packet # just return normal packet 
                
        return data

    def _calculate_checksum(self, data):
        
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