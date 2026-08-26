#!/usr/bin/env python3
"""
Local Image Server for IELTS Selection Assistant
Serves assets/images/ on http://127.0.0.1:8765/ with:
- Full CORS support (Access-Control-Allow-Origin: *)
- Instant memory / direct disk streaming
- Case-insensitive filename matching (e.g. travel.jpg -> Travel.jpg)
- Cache-Control headers for instant local loading
"""
import os
import sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "assets" / "images"
PORT = 8777

IMAGE_INDEX = {}
if IMAGES_DIR.exists():
    for fn in os.listdir(IMAGES_DIR):
        IMAGE_INDEX[fn.lower()] = fn
        stem = Path(fn).stem.lower()
        if stem not in IMAGE_INDEX:
            IMAGE_INDEX[stem] = fn

class IELTSImageRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        req_name = urllib.parse.unquote(self.path.split('?', 1)[0].split('#', 1)[0].lstrip('/'))
        if not req_name or req_name == "health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(f"IELTS Image Server running ({len(IMAGE_INDEX)} indexed images)".encode('utf-8'))
            return

        clean_lower = req_name.lower()
        target_file = None
        if clean_lower in IMAGE_INDEX:
            target_file = IMAGES_DIR / IMAGE_INDEX[clean_lower]
        elif (clean_lower + '.jpg') in IMAGE_INDEX:
            target_file = IMAGES_DIR / IMAGE_INDEX[clean_lower + '.jpg']

        if target_file and target_file.is_file():
            try:
                data = target_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception:
                pass

        self.send_response(404)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_HEAD(self):
        req_name = urllib.parse.unquote(self.path.split('?', 1)[0].split('#', 1)[0].lstrip('/'))
        clean_lower = req_name.lower()
        target_file = None
        if clean_lower in IMAGE_INDEX:
            target_file = IMAGES_DIR / IMAGE_INDEX[clean_lower]
        elif (clean_lower + '.jpg') in IMAGE_INDEX:
            target_file = IMAGES_DIR / IMAGE_INDEX[clean_lower + '.jpg']

        if target_file and target_file.is_file():
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(target_file.stat().st_size))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server(port=PORT):
    server_address = ('', port)
    httpd = HTTPServer(server_address, IELTSImageRequestHandler)
    print(f"============================================================")
    print(f"🖼️  IELTS Local Image Server running at:")
    print(f"   👉 http://127.0.0.1:{port}/")
    print(f"   📁 Serving: {IMAGES_DIR} ({len(IMAGE_INDEX)} indexed images)")
    print(f"   🌐 Full CORS enabled for all webpages")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping image server...")
        httpd.server_close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
