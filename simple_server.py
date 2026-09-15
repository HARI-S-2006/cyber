import http.server
import socketserver

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            super().do_GET()

PORT = 8000
with socketserver.TCPServer(('0.0.0.0', 8000), http.server.SimpleHTTPRequestHandler) as httpd:
    print('Serving at port', PORT)
    httpd.serve_forever()