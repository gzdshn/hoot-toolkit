
from http.server import HTTPServer, SimpleHTTPRequestHandler
def start_local_server(directory: str, port: int):
    class LocalHTTPRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

    httpd = HTTPServer(('localhost', port), LocalHTTPRequestHandler)
    httpd.serve_forever()
