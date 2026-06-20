import http.server, socketserver, sys, urllib.parse
class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if '/log' in self.path:
            print('RESULT:', urllib.parse.unquote(self.path.split('res=')[1]))
            sys.stdout.flush()
            self.send_response(200)
            self.end_headers()
            sys.exit(0)
        super().do_GET()
httpd = socketserver.TCPServer(('127.0.0.1', 8003), H)
httpd.timeout = 20
httpd.handle_request()
httpd.handle_request()
