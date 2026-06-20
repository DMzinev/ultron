import http.server, socketserver, sys
class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/log':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            with open('qa_results.txt', 'w', encoding='utf-8') as f:
                f.write(post_body.decode('utf-8'))
            self.send_response(200)
            self.end_headers()
            print('Results received. Exiting.')
            sys.exit(0)
httpd = socketserver.TCPServer(('127.0.0.1', 8005), H)
httpd.timeout = 30
print('Server started on 8005')
httpd.handle_request()
