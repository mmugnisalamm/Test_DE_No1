import http.server
import socketserver
import requests
import socket
import select

class ProxyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.proxy_request()

    def do_POST(self):
        self.proxy_request()

    def do_CONNECT(self):
        self.handle_connect()

    def proxy_request(self):
        url = self.path
        if url.startswith('/'):
            url = url[1:]

        print(f'Proxying request to {url}')

        try:
            if self.command == 'GET':
                response = requests.get(url, headers=self.headers)
            elif self.command == 'POST':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                response = requests.post(url, data=post_data, headers=self.headers)

            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                    self.send_header(key, value)
            self.end_headers()

            self.wfile.write(response.content)
        
        except Exception as e:
            self.send_error(500, f'Error proxying request: {str(e)}')

    def handle_connect(self):
        self.send_response(200, 'Connection Established')
        self.end_headers()

        dest_host, dest_port = self.path.split(':')
        dest_port = int(dest_port)

        try:
            remote_socket = socket.create_connection((dest_host, dest_port))
        except Exception as e:
            self.send_error(500, f'Error connecting to destination: {str(e)}')
            return

        self.connection.setblocking(False)
        remote_socket.setblocking(False)

        sockets = [self.connection, remote_socket]
        while True:
            readable, writable, exceptional = select.select(sockets, [], sockets)
            if exceptional:
                break
            if self.connection in readable:
                data = self.connection.recv(8192)
                if not data:
                    break
                remote_socket.sendall(data)
            if remote_socket in readable:
                data = remote_socket.recv(8192)
                if not data:
                    break
                self.connection.sendall(data)

        remote_socket.close()
        self.connection.close()

def run(server_class=http.server.HTTPServer, handler_class=ProxyHTTPRequestHandler, port=9919):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting proxy on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
