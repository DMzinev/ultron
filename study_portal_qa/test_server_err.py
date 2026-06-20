import http.server, socketserver, sys
class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/error':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            with open('error_log.txt', 'a', encoding='utf-8') as f:
                f.write(post_body.decode('utf-8') + '\n')
            self.send_response(200)
            self.end_headers()
httpd = socketserver.TCPServer(('127.0.0.1', 8008), H)
print('Server started on 8008')
httpd.serve_forever()
