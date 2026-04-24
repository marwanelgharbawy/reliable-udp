import socket
import struct
import random

class ReliableUDP:
    def __init__(self, host, port, is_server=False):
        
        # flags defined as bitmasks
        FLAG_SYN = 0b00000001
        FLAG_ACK = 0b00000010
        FLAG_FIN = 0b00000100
        # SYNACK is SYN | ACK
        
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
            
            if self._simulate_packet_loss():
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
                    if calc_checksum == recv_checksum and recv_ack == self.seq_num and (flags & self.FLAG_ACK):
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
                        ack_packet = self._create_packet(0, seq_num, self.FLAG_ACK)
                        
                        # simulate ACK packet loss
                        if self._simulate_packet_loss():
                            pass # do nothing
                        else:
                            self.sock.sendto(ack_packet, address)
                            
                        # if FIN is received, close connection
                        if flags & self.FLAG_FIN:
                            print(f"FIN received from {address}. Closing connection.")
                            return b'', address # empty data
                        
                        # if it's the expected sequence number
                        if seq_num == self.expected_seq_num:
                            self.expected_seq_num = 1 - self.expected_seq_num # toggle expected sequence number
                            return data, address
                        # else, it's duplicate packet
            except socket.timeout:
                continue
            
    def connect(self, server_address):
        syn_packet = self._create_packet(0, 0, self.FLAG_SYN)
        
        while True:
            
            # send SYN packet to server
            if not self._simulate_packet_loss():
                self.sock.sendto(syn_packet, server_address)
                
            try:
                # receive SYNACK packet from server
                response, _ = self.sock.recvfrom(1024)
                parsed = self._parse_packet(response)
                
                if parsed:
                    seq, ack, flags, checksum, data = parsed
                    temp_header = struct.pack(self.header_format, seq, ack, flags, 0)
                    
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    # SYNACK: both SYN and ACK bits are set
                    if calc_checksum == checksum and flags & self.FLAG_SYN and flags & self.FLAG_ACK:
                        
                        # send ACK packet to server
                        # add 1 to seq_num of client, no matter what it is (it's 0 by default)
                        ack_packet = self._create_packet(1, seq + 1, self.FLAG_ACK)
                        if not self._simulate_packet_loss():
                            self.sock.sendto(ack_packet, server_address)
                        
                        self.seq_num = 1
                        self.expected_seq_num = seq + 1
                        return
            except socket.timeout:
                continue

    def accept(self):
        client_address = None
        client_seq = 0
        
        while True:
            try:
                # block until SYN packet is received
                packet, address = self.sock.recvfrom(1024)
                parsed = self._parse_packet(packet)
                
                if parsed:
                    seq, ack, flags, checksum, data = parsed
                    temp_header = struct.pack(self.header_format, seq, ack, flags, 0)
                    
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    if calc_checksum == checksum:
                        # check for SYN flag only
                        if flags & self.FLAG_SYN and not flags & self.FLAG_ACK: 
                            client_address = address
                            client_seq = seq
                            
                            # send SYNACK: SYN + ACK flags
                            synack_packet = self._create_packet(0, client_seq + 1, self.FLAG_SYN | self.FLAG_ACK)
                            if not self._simulate_packet_loss():
                                self.sock.sendto(synack_packet, client_address)
                                
                       # receive final ACK from client
                        elif flags & self.FLAG_ACK and client_address == address: 
                            self.expected_seq_num = 1
                            self.seq_num = 1
                            print(f"Connection established with {client_address}")
                            return client_address
            except socket.timeout:
                continue
            
    def close(self, address=None):
        if address is None:
            address = (self.host, self.port)
            
        fin_packet = self._create_packet(self.seq_num, 0, self.FLAG_FIN)
        
        while True:
            if not self._simulate_packet_loss():
                self.sock.sendto(fin_packet, address)
                
            try:
                ack_packet, _ = self.sock.recvfrom(1024)
                parsed = self._parse_packet(ack_packet)
                
                if parsed:
                    recv_seq, recv_ack, flags, recv_checksum, data = parsed
                    temp_header = struct.pack(self.header_format, recv_seq, recv_ack, flags, 0)
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    # when ACK is received, connection can be closed
                    if calc_checksum == recv_checksum and (flags & self.FLAG_ACK):
                        print("Connection closed.")
                        self.sock.close()
                        return
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
        return packet # no corruption

    def _calculate_checksum(self, data):
        
        # if number of bytes is odd, add a zero byte to make it even
        if len(data) % 2 != 0:
            checksum_data = data + b'\0'
        else:
            checksum_data = data

        checksum = 0
        
        # process data in words (2 bytes)
        for i in range(0, len(checksum_data), 2):
            word = (checksum_data[i] << 8) + checksum_data[i+1]
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