import socket
import struct
import random

# flags
FLAG_SYN = 0b00000001
FLAG_ACK = 0b00000010
FLAG_FIN = 0b00000100
FLAG_DATA = 0b00001000
# SYNACK is SYN | ACK

# simulation parameters
PACKET_LOSS_PROB = 0.3
DATA_CORRUPTION_PROB = 0.3
TIMEOUT_SECONDS = 1

# unsigned int for seq_num (4 bytes)
# unsigned int for ack_num (4 bytes)
# unsigned char for 3 flags (1 byte)
# unsigned short for checksum (2 bytes)
HEADER_FORMAT = "!I I B H" # seq_num, ack_num, flags, checksum

class ReliableUDP:
    def __init__(self, host, port, is_server=False):
        
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
        
        self.seq_num = 0
        self.ack_num = 0
        
        self.expected_seq_num = 0
        
        # simulation paramteres: packet loss probabilites and data corruption
        self.sock.settimeout(TIMEOUT_SECONDS) 
        self.packet_loss_prob = PACKET_LOSS_PROB
        self.data_corruption_prob = DATA_CORRUPTION_PROB
        
        # buffer for unprocessed packets
        self.unprocessed_packets = []
        
        # if not server, no need to bind
        if is_server:
            self.sock.bind((self.host, self.port))
            print(f"Server listening on {self.host}:{self.port}")
            
    # takes data as bytes and address as (host, port)
    def sendto(self, data, address=None):
        if address is None:
            address = (self.host, self.port)
            
        packet = self._create_packet(self.seq_num, 0, FLAG_DATA, data)
        
        # while loop to retransmit whenever timeout occurs (ACK not received)
        while True:
            
            if self._simulate_packet_loss():
                print("Dropping packet to simulate loss.")
                pass # do nothing
            else:
                # simulate checksum corruption
                print(f"Sending packet with seq_num {self.seq_num}.")
                packet_to_send = self._simulate_false_checksum(packet)
                self.sock.sendto(packet_to_send, address)
                
            # wait for the correct ACK to be received 
            while True:
                
                try:
                    ack_packet, _ = self.sock.recvfrom(8192)
                    print(f"ACK received from {address}.")

                    # receive ACK packet, parse it and verify checksum and ACK number
                    parsed = self._parse_packet(ack_packet)
                    
                    if parsed:
                        recv_seq, recv_ack, flags, recv_checksum, data = parsed
                        
                        temp_header = struct.pack(HEADER_FORMAT, recv_seq, recv_ack, flags, 0)
                        calc_checksum = self._calculate_checksum(temp_header + data)
                        
                        # compare checksum and ACK number for verification
                        # if verified, toggle 0 and 1 for seq_num (stop and wait protocol)
                        if calc_checksum == recv_checksum:
                            
                            if recv_ack == self.seq_num and flags & FLAG_ACK:
                                
                                if flags & FLAG_SYN:
                                    print("Received SYNACK. Ignoring.")
                                    continue
                                
                                print(f"ACK number {recv_ack} verified. Packet delivery successful.")
                                self.seq_num = 1 - self.seq_num
                                # self.expected_seq_num = 1 - self.expected_seq_num # fix?
                                return
                            
                            # if it's data flag, ACK again and discard it since we need ACK packets
                            elif flags & FLAG_DATA:
                                print(f"Duplicate data intercepted. Re-ACKing and discarding payload.")
                                
                                # send ACK packet with ACK flag set and ACK number equal to received seq_num
                                dup_ack = self._create_packet(0, recv_seq, FLAG_ACK)
                                
                                if not self._simulate_packet_loss():
                                    self.sock.sendto(dup_ack, address)
                                    
                                self.unprocessed_packets.append((ack_packet, address))
                                
                                # stay in the inner while loop to wait for ACK
                                continue
                        else:
                            print(f"Incorrect ACK number received. ACK packet discarded.")
                        
                # if timeout occurs, resend packet
                except socket.timeout:
                    print("Timeout while waiting for ACK. Retransmitting.")
                    break
    
    def receive(self):
        while True:
            # if there's an unprocessed packet in the buffer, process it first before receiving new packets
            if self.unprocessed_packets:
                packet, address = self.unprocessed_packets.pop(0)
            else:
                try:
                    packet, address = self.sock.recvfrom(8192) 
                except socket.timeout:
                    continue
                
            parsed = self._parse_packet(packet)
            
            if parsed:
                seq_num, ack_num, flags, recv_checksum, data = parsed
                
                # ignore control packets
                if not (flags & FLAG_DATA) and not (flags & FLAG_FIN):
                    continue
                
                print(f"Packet received with seq_num {seq_num}.")
                
                temp_header = struct.pack(HEADER_FORMAT, seq_num, ack_num, flags, 0)
                calc_checksum = self._calculate_checksum(temp_header + data)
                
                # two checks required: checksum then sequence number
                # otherwise wait for next packet
                
                if calc_checksum == recv_checksum:
                    
                    # ignore ACK packets, receiver is the one that's supposed to send them
                    # before, it caused an infinite loop of ACKs
                    if flags & FLAG_ACK:
                        print("Ignoring ACK packet received at receiver.")
                        continue
                    
                    # send ACK packet with ACK flag set and ACK number equal to received seq_num
                    ack_packet = self._create_packet(0, seq_num, FLAG_ACK)
                    
                    # simulate ACK packet loss
                    if self._simulate_packet_loss():
                        print(f"ACK for seq_num {seq_num} lost. No ACK sent.")
                        pass # do nothing
                    else:
                        self.sock.sendto(ack_packet, address)
                        
                    # if FIN is received, close connection
                    if flags & FLAG_FIN:
                        print(f"FIN received from {address}. Closing connection.")
                        return b'', address # empty data
                    
                    # if it's the expected sequence number
                    if seq_num == self.expected_seq_num:
                        self.expected_seq_num = 1 - self.expected_seq_num # toggle expected sequence number
                        print(f"Expected sequence number updated to {self.expected_seq_num}.")
                        print(f"Packet received from {address} with seq_num {seq_num}. ACK sent.")
                        return data, address
                    else:
                        print(f"Duplicate packet received from {address} (seq_num {seq_num}). ACK re-sent. Discarding payload.")
                else:
                    print(f"Packet received from {address} with seq_num {seq_num} with invalid checksum. Discarded.")
            
    def connect(self, server_address):
        syn_packet = self._create_packet(0, 0, FLAG_SYN)
        
        while True:
            
            # send SYN packet to server
            if not self._simulate_packet_loss():
                self.sock.sendto(syn_packet, server_address)
                print(f"SYN packet sent to {server_address}.")
                
            try:
                # receive SYNACK packet from server
                response, _ = self.sock.recvfrom(8192)
                parsed = self._parse_packet(response)
                
                if parsed:
                    seq, ack, flags, checksum, data = parsed
                    temp_header = struct.pack(HEADER_FORMAT, seq, ack, flags, 0)
                    
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    # SYNACK: both SYN and ACK bits are set
                    if calc_checksum == checksum and flags & FLAG_SYN and flags & FLAG_ACK:
                        
                        # send ACK packet to server
                        # add 1 to seq_num of client, no matter what it is (it's 0 by default)
                        ack_packet = self._create_packet(1, seq + 1, FLAG_ACK)
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
                    temp_header = struct.pack(HEADER_FORMAT, seq, ack, flags, 0)
                    
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    if calc_checksum == checksum:
                        # check for SYN flag only
                        if flags & FLAG_SYN and not flags & FLAG_ACK: 
                            client_address = address
                            client_seq = seq
                            
                            # send SYNACK: SYN + ACK flags
                            synack_packet = self._create_packet(0, client_seq + 1, FLAG_SYN | FLAG_ACK)
                            if not self._simulate_packet_loss():
                                self.sock.sendto(synack_packet, client_address)
                                print(f"SYNACK packet sent to {client_address}.")
                                
                       # receive final ACK from client
                       # if connection was actually established but ACK from client was lost
                        elif (flags & FLAG_ACK or flags & FLAG_DATA) and client_address == address: 
                            self.expected_seq_num = 1
                            self.seq_num = 1
                            print(f"Connection established with {client_address}")
                            
                            # this case is when ACK was lost but connection was actually established for client
                            # in that case, server is still waiting for ACK but it was lost
                            # when a data packet is sent from client, it will be buffered in the unprocessed_packets 
                            # and when receiev() is called, it will be processed and ACKed
                            if flags & FLAG_DATA:
                                print("Buffering early DATA packet from handshake.")
                                self.unprocessed_packets.append((packet, address))
                            
                            return client_address
                    else:
                        print(f"Packet received from {address} with seq_num {seq} with invalid checksum. Discarded.")
            except socket.timeout:
                # special case: retransmit SYNACK if timeout occurs while waiting for final ACK
                if client_address:
                    synack_packet = self._create_packet(0, client_seq + 1, FLAG_SYN | FLAG_ACK)
                    if not self._simulate_packet_loss():
                        self.sock.sendto(synack_packet, client_address)
                        print(f"Timeout waiting for final ACK. Retransmitting SYNACK to {client_address}.")
                continue
            
    def close(self, address=None):
        if address is None:
            address = (self.host, self.port)
            
        fin_packet = self._create_packet(self.seq_num, 0, FLAG_FIN)
        
        while True:
            if not self._simulate_packet_loss():
                self.sock.sendto(fin_packet, address)
                print(f"FIN packet sent to {address}.")
            try:
                ack_packet, _ = self.sock.recvfrom(8192)
                parsed = self._parse_packet(ack_packet)
                
                if parsed:
                    recv_seq, recv_ack, flags, recv_checksum, data = parsed
                    temp_header = struct.pack(HEADER_FORMAT, recv_seq, recv_ack, flags, 0)
                    calc_checksum = self._calculate_checksum(temp_header + data)
                    
                    # when ACK is received, connection can be closed
                    if calc_checksum == recv_checksum and (flags & FLAG_ACK):
                        print("Connection closed.")
                        self.sock.close()
                        return
            except socket.timeout:
                print("Timeout while waiting for ACK. Retransmitting FIN packet.")
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
            
            print("Modifying checksum to simulate data corruption.")
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
        temp_header = struct.pack(HEADER_FORMAT, seq_num, ack_num, flags, 0)
        checksum = self._calculate_checksum(temp_header + data)
        header = struct.pack(HEADER_FORMAT, seq_num, ack_num, flags, checksum)
        
        return header + data

    def _parse_packet(self, packet):
        header_size = struct.calcsize(HEADER_FORMAT)
        
        # if packet is too short to contain a valid header, then it's invalid
        if len(packet) < header_size:
            return None 
            
        # parse header and data
        header = packet[:header_size]
        data = packet[header_size:]
        
        # unpack using the same format as packing to get header data
        seq_num, ack_num, flags, recv_checksum = struct.unpack(HEADER_FORMAT, header)
        
        return seq_num, ack_num, flags, recv_checksum, data