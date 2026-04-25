import os
from ReliableUDP import ReliableUDP

# # same process data as tcp_server.py
# def process(data):
#     if data.startswith('A'):
#         return ''.join(sorted(data[1:], reverse=True))
#     elif data.startswith('C'):
#         return ''.join(sorted(data[1:]))
#     elif data.startswith('D'):
#         return data[1:].upper()
#     else:
#         return data

def handle_request(request_data):
    #Parse HTTP request and return (response_data, status_code)
    try:

        # \r\n signals the end of a specific header field
        request_str = request_data.decode('utf-8')
        lines = request_str.split('\r\n')

        # if the request is empty, return a 400 Bad Request error
        # \r\n\r\n marks the end of the headers and the beginning of the body (data)
        if not lines:
            return b"HTTP/1.0 400 Bad Request\r\n\r\n", 400

        # parse request line: Method, Path, Version
        request_line = lines[0].split()
        if len(request_line) < 3:
            return b"HTTP/1.0 400 Bad Request\r\n\r\n", 400
            
        method, path, version = request_line
        # if the path is just / => default to index.html (home)
        filename = path.lstrip('/') if path != '/' else 'index.html'

        # GET method
        if method == 'GET':
            if os.path.exists(filename) and os.path.isfile(filename):
                with open(filename, 'rb') as f:  # rb => binary mode
                    content = f.read()
                header = f"HTTP/1.0 200 OK\r\nContent-Length: {len(content)}\r\nContent-Type: text/html\r\n\r\n"
                return header.encode('utf-8') + content, 200
            else:
                return b"HTTP/1.0 404 NOT FOUND\r\n\r\nFile Not Found", 404

        # POST method
        elif method == 'POST':
            # find the blank line that separates headers from body
            try:
                body_index = request_str.index('\r\n\r\n') + 4   # 4 is length of \r\n\r\n
                body_content = request_str[body_index:]
                
                with open(filename, 'w') as f:
                    f.write(body_content)
                
                success_msg = f"File {filename} uploaded successfully."
                header = f"HTTP/1.0 200 OK\r\nContent-Length: {len(success_msg)}\r\n\r\n"
                return header.encode('utf-8') + success_msg.encode('utf-8'), 200
            except ValueError:
                return b"HTTP/1.0 400 Bad Request\r\n\r\n", 400

        else:
            return b"HTTP/1.0 501 Not Implemented\r\n\r\n", 501

    except Exception as e:
        print(f"Error processing request: {e}")
        return b"HTTP/1.0 500 Internal Server Error\r\n\r\n", 500

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
        response, status = handle_request(data_bytes)

        print(f"Responding with Status: {status}")
        server.sendto(response, address)
        
        # # data must be in utf-8 since UDP sends/receives bytes
        # data = data_bytes.decode('utf-8')
        # response = process(data)
        # # encode back to bytes before sending
        # server.sendto(response.encode('utf-8'), address)

if __name__ == "__main__":
    start_server()