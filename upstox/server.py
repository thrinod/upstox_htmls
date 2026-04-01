from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

port = 8080
print(f"Starting server on port {port}...")
print(f"Access the application at: http://YOUR_PUBLIC_IP:{port}/index.html")

# 🔥 CHANGE HERE
httpd = HTTPServer(('0.0.0.0', port), CORSRequestHandler)

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nShutting down server...")
    httpd.server_close()
