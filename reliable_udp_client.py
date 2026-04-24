import socket
from ReliableUDP import ReliableUDP

def start_client():
    host = '127.0.0.1'
    port = 8080
    server_address = (host, port)
    
    # replace client will be replaced with reliable UDP class instead of python socket
    client = ReliableUDP(host, port, is_server=False)
    
    print(f"Communicating with server at {host}:{port}")
    
    # 3 way handshake
    client.connect(server_address)
    
    while True:
        message = input("Client: ")
        
        # to prevent forcibly closing the client
        if message == 'quit':
            break
            
        # encode to utf-8 to send bytes to the server address
        client.sendto(message.encode('utf-8'), server_address)
        
        # block until response and decode it from bytes
        response_bytes, _ = client.receive()
        
        # server disconnect
        if not response_bytes:
            print("Server closed connection.")
            break
        
        response = response_bytes.decode('utf-8')
        
        print(f"Server: {response}")
        
    client.close()

if __name__ == "__main__":
    start_client()