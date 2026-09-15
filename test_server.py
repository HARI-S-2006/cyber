import http.server
import socketserver
import socket

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

PORT = 8000
with socketserver.TCPServer(('0.0.0.0', 8000), MyHandler) as httpd:
    print('Serving at port', 8000)
    httpd = socketserver.TCPServer(('0.0.0.0', 8000), MyHandler)
    httpd.serve_forever()