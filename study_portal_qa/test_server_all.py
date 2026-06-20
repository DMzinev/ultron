import http.server, socketserver, sys
class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path in ['/log', '/error']:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            with open('qa_results.txt', 'a', encoding='utf-8') as f:
                f.write(post_body.decode('utf-8') + '\n')
            self.send_response(200)
            self.end_headers()
httpd = socketserver.TCPServer(('127.0.0.1', 8010), H)
print('Server started on 8010')
httpd.serve_forever()
