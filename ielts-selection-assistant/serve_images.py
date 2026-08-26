#!/usr/bin/env python3
"""
Local Image & Telemetry Server for IELTS Selection Assistant
Serves on http://127.0.0.1:8777/ with:
- Static image streaming (assets/images/)
- Dedicated stats page & data persistence (data/stats.json)
- Full CORS support (Access-Control-Allow-Origin: *)
- Case-insensitive filename matching (e.g. travel.jpg -> Travel.jpg)
"""
import json
import os
import sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

SUBPROJECT_DIR = Path(__file__).resolve().parent
ROOT = SUBPROJECT_DIR.parent
IMAGES_DIR = ROOT / "assets" / "images"
STATS_FILE = SUBPROJECT_DIR / "data" / "stats.json"
PORT = 8777

IMAGE_INDEX = {}
if IMAGES_DIR.exists():
    for fn in os.listdir(IMAGES_DIR):
        IMAGE_INDEX[fn.lower()] = fn
        stem = Path(fn).stem.lower()
        if stem not in IMAGE_INDEX:
            IMAGE_INDEX[stem] = fn

class IELTSRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        req_path = self.path.split('?', 1)[0].split('#', 1)[0].lstrip('/')
        req_name = urllib.parse.unquote(req_path)

        if not req_name or req_name == "health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(f"IELTS Assistant Server running ({len(IMAGE_INDEX)} indexed images)".encode('utf-8'))
            return

        # Dedicated stats API
        if req_name == "api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if STATS_FILE.exists():
                self.wfile.write(STATS_FILE.read_bytes())
            else:
                self.wfile.write(b'{"summary":{"marks":0,"modalOpens":0,"inputSuccess":0},"words":{}}')
            return

        # Stats HTML page
        if req_name in ("stats", "stats.html"):
            stats_html = SUBPROJECT_DIR / "stats.html"
            if stats_html.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(stats_html.read_bytes())
                return

        # Static Images
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

    def do_POST(self):
        req_path = self.path.split('?', 1)[0].split('#', 1)[0].lstrip('/')
        if req_path == "api/stats":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode('utf-8'))
                STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
                STATS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                return
            except Exception as e:
                self.send_response(400)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
                return

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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server(port=PORT):
    server_address = ('', port)
    httpd = HTTPServer(server_address, IELTSRequestHandler)
    print(f"============================================================")
    print(f"🖼️  IELTS Selection Assistant Server running at:")
    print(f"   👉 Images API: http://127.0.0.1:{port}/")
    print(f"   📊 Stats Page: http://127.0.0.1:{port}/stats")
    print(f"   💾 Stats Sync: {STATS_FILE}")
    print(f"   🌐 Full CORS enabled for all webpages")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
