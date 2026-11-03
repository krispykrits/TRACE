"""Serve the test client and forward its API requests to kubectl port-forward."""
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
STATIC = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/client.js': ('client.js', 'text/javascript; charset=utf-8'),
    '/redirect.html': ('redirect.html', 'text/html; charset=utf-8'),
    '/msal-browser.js': ('node_modules/@azure/msal-browser/lib/msal-browser.js', 'text/javascript; charset=utf-8'),
    '/msal-redirect-bridge.js': ('node_modules/@azure/msal-browser/lib/redirect-bridge/msal-redirect-bridge.js', 'text/javascript; charset=utf-8'),
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def respond(self, status, data, content_type='text/plain; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.headers.get('Host') != 'localhost:8765':
            return self.respond(403, b'Invalid host')
        if self.path in STATIC:
            filename, content_type = STATIC[self.path]
            try:
                self.respond(200, (ROOT / filename).read_bytes(), content_type)
            except FileNotFoundError:
                self.respond(503, b'Run npm ci in the test client directory first.')
        else:
            self.proxy()

    def do_POST(self):
        if self.headers.get('Host') != 'localhost:8765':
            return self.respond(403, b'Invalid host')
        self.proxy()

    def proxy(self):
        # Only the investigation endpoints are exposed; this is not a general proxy.
        if not re.fullmatch(r'/api/investigations(?:/[A-Za-z0-9-]+(?:/report)?)?', self.path):
            return self.respond(404, b'Not found')
        if self.command == 'POST' and self.path != '/api/investigations':
            return self.respond(405, b'Method not allowed')
        origin = self.headers.get('Origin')
        if origin and origin != 'http://localhost:8765':
            return self.respond(403, b'Invalid origin')
        authorization = self.headers.get('Authorization', '')
        if not authorization.startswith('Bearer '):
            return self.respond(401, b'Bearer token required')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.respond(400, b'Invalid content length')
        if length < 0 or length > 8192:
            return self.respond(413, b'Request too large')
        connection = HTTPConnection('127.0.0.1', 18080, timeout=30)
        try:
            connection.request(self.command, self.path[4:], body=self.rfile.read(length), headers={
                'Authorization': authorization,
                'Content-Type': 'application/json',
            })
            response = connection.getresponse()
            self.respond(response.status, response.read(), response.getheader('Content-Type', 'application/json'))
        except OSError:
            self.respond(502, b'Cannot reach the API. Check the kubectl port-forward.')
        finally:
            connection.close()

if __name__ == '__main__':
    print('Open http://localhost:8765')
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
