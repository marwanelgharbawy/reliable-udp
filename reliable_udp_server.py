import os
from ReliableUDP import ReliableUDP

# MIME type detection
def get_content_type(filename):
    if filename.endswith(".html"):
        return "text/html"
    elif filename.endswith(".txt"):
        return "text/plain"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        return "image/jpeg"
    elif filename.endswith(".png"):
        return "image/png"
    else:
        return "application/octet-stream"

def handle_request(request_data):
    #Parse HTTP request and return (response_data, status_code)
    try:

        # \r\n signals the end of a specific header field
        request_str = request_data.decode('utf-8')
        lines = request_str.split('\r\n')

        # if the request is empty, return a 400 Bad Request error
        # \r\n\r\n marks the end of the headers and the beginning of the body (data)
        if not lines:
            return b"HTTP/1.0 400 Bad Request\r\nConnection: close\r\n\r\n", 400

        # parse request line: Method, Path, Version
        request_line = lines[0].split()
        if len(request_line) < 3:
            return b"HTTP/1.0 400 Bad Request\r\nConnection: close\r\n\r\n", 400
            
        method, path, version = request_line
        # if the path is just / => default to index.html (home)
        filename = path.lstrip('/') if path != '/' else 'index.html'

        # parse headers into dictionary
        headers = {}
        for line in lines[1:]:
            if line == "":
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # extract body properly using Content-Length
        body = ""
        if "\r\n\r\n" in request_str:
            body_start = request_str.index("\r\n\r\n") + 4
            content_length = int(headers.get("Content-Length", 0))
            body = request_str[body_start:body_start + content_length]

        # GET method
        if method == 'GET':
            if os.path.exists(filename) and os.path.isfile(filename):
                with open(filename, 'rb') as f:  # rb => binary mode
                    content = f.read()

                content_type = get_content_type(filename)

                header = (
                    f"HTTP/1.0 200 OK\r\n"
                    f"Content-Length: {len(content)}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )

                return header.encode('utf-8') + content, 200
            else:
                return (
                    b"HTTP/1.0 404 NOT FOUND\r\n"
                    b"Content-Length: 14\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                    b"File Not Found"
                ), 404

        # POST method
        elif method == 'POST':
            try:
                with open(filename, 'w') as f:
                    f.write(body)
                
                success_msg = f"File {filename} uploaded successfully."

                header = (
                    f"HTTP/1.0 200 OK\r\n"
                    f"Content-Length: {len(success_msg)}\r\n"
                    f"Content-Type: text/plain\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )

                return header.encode('utf-8') + success_msg.encode('utf-8'), 200
            except Exception:
                return (
                    b"HTTP/1.0 400 Bad Request\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                ), 400

        else:
            return (
                b"HTTP/1.0 501 Not Implemented\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            ), 501

    except Exception as e:
        print(f"Error processing request: {e}")
        return (
            b"HTTP/1.0 500 Internal Server Error\r\n"
            b"Connection: close\r\n"
            b"\r\n"
        ), 500 

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

if __name__ == "__main__":
    start_server()