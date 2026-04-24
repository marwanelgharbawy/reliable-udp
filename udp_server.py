import socket
import threading
from reliable_udp import ReliableUDP

# same process data as tcp_server.py
def process(data):
    if data.startswith('A'):
        return ''.join(sorted(data[1:], reverse=True))
    elif data.startswith('C'):
        return ''.join(sorted(data[1:]))
    elif data.startswith('D'):
        return data[1:].upper()
    else:
        return data

def start_server():
    print("Starting server...")
    
    host = '127.0.0.1'
    port = 8080
    
    server = ReliableUDP(host, port, is_server=True)
    
    print("Waiting for client connection...")
    client_address = server.accept()
    
    while True:
        # block until data is received from the client
        data_bytes, address = server.receive()
        
        if not data_bytes:
            print("No data received. Closing connection.")
            break
        
        print(f"Data received from {address}")
        
        # data must be in utf-8 since UDP sends/receives bytes
        data = data_bytes.decode('utf-8')
        response = process(data)
        # encode back to bytes before sending
        server.sendto(response.encode('utf-8'), address)

if __name__ == "__main__":
    start_server()