import http.server, socketserver, sys, urllib.parse, json
class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/log':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            with open('test_results.json', 'w') as f:
                f.write(post_body.decode('utf-8'))
            self.send_response(200)
            self.end_headers()
            sys.exit(0)
httpd = socketserver.TCPServer(('127.0.0.1', 8004), H)
httpd.timeout = 20
httpd.handle_request()
