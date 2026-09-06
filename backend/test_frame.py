"""Debug script: sends a real test JPEG to /detect/frame and shows full error."""
import urllib.request, json, base64, struct, zlib, sys

BASE = "http://127.0.0.1:8000/api"

# --- Login ---
data = json.dumps({"username": "admin", "password": "Admin@123"}).encode()
req = urllib.request.Request(f"{BASE}/auth/login", data=data,
                             headers={"Content-Type": "application/json"})
res = json.loads(urllib.request.urlopen(req).read())
token = res["access_token"]
print("Login OK")

# --- Build a minimal valid 4x4 white JPEG ---
# We'll use a tiny PNG and send it as JPEG mime type (OpenCV can handle both)
def make_png_bytes(w=4, h=4):
    """Build a minimal valid PNG manually."""
    def chunk(tag, data):
        c = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", c)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB, no interlace
    raw = b""
    for _ in range(h):
        raw += b"\x00" + b"\xFF\xFF\xFF" * w   # filter byte + white pixels

    idat = zlib.compress(raw)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    return png

img_bytes = make_png_bytes()
img_b64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode()

payload = json.dumps({"image": img_b64}).encode()
req2 = urllib.request.Request(
    f"{BASE}/detect/frame", data=payload,
    headers={"Content-Type": "application/json",
             "Authorization": f"Bearer {token}"}
)
try:
    res2 = json.loads(urllib.request.urlopen(req2).read())
    print("detect/frame OK:", res2)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code} ERROR:\n{body}")
except Exception as e:
    print(f"Request failed: {e}")
