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

    # TEST GET REQUEST
    print("\n --- Sending GET Request --- ")
    get_request = "GET /index.html HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"
    client.sendto(get_request.encode('utf-8'), server_address)
    
    response, _ = client.receive()
    print(f"Response from Server:\n{response.decode('utf-8', errors='ignore')}")

    # TEST POST REQUEST
    print("\n --- Sending POST Request --- ")
    post_body = "This data was sent via Reliable UDP"
    post_request = (
        f"POST /upload.txt HTTP/1.0\r\n"
        f"Host: 127.0.0.1\r\n"
        f"Content-Length: {len(post_body)}\r\n"
        f"\r\n"
        f"{post_body}"
    )
    client.sendto(post_request.encode('utf-8'), server_address)
    
    response, _ = client.receive()
    print(f"Response from Server:\n{response.decode('utf-8')}")
    
    # while True:
    #     message = input("Client: ")
        
    #     # to prevent forcibly closing the client
    #     if message == 'quit':
    #         break
            
    #     # encode to utf-8 to send bytes to the server address
    #     client.sendto(message.encode('utf-8'), server_address)
        
    #     # block until response and decode it from bytes
    #     response_bytes, _ = client.receive()
        
    #     # server disconnect
    #     if not response_bytes:
    #         print("Server closed connection.")
    #         break
        
    #     response = response_bytes.decode('utf-8')
        
    #     print(f"Server: {response}")
        
    client.close()

if __name__ == "__main__":
    start_client()