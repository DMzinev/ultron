import http.server, socketserver, sys, urllib.parse
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if '/log' in self.path:
            print('BROWSER LOG:', urllib.parse.unquote(self.path.split('msg=')[1]))
            sys.stdout.flush()
            self.send_response(200)
            self.end_headers()
            return
        super().do_GET()
httpd = socketserver.TCPServer(('', 8001), Handler)
httpd.timeout = 20
httpd.handle_request()
