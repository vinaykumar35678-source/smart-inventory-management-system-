import urllib.request, json

BASE = "http://127.0.0.1:8000/api"

def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())

# Login
data = json.dumps({"username": "admin", "password": "Admin@123"}).encode()
req = urllib.request.Request(f"{BASE}/auth/login", data=data, headers={"Content-Type": "application/json"})
res = json.loads(urllib.request.urlopen(req).read())
token = res["access_token"]
print("Login OK\n")

# Products
products = get(f"{BASE}/products", token)
print(f"Total products: {len(products)}")
cats = {}
for p in products:
    cats.setdefault(p["category"], []).append(p["name"])
    print(f"  [{p['category']:14}] {p['name']:22} stock={p['stock']:3}  price={p['price']}")

print("\nCategories:", list(cats.keys()))

# Simulate frame detection (1x1 black JPEG)
import base64, struct
# Minimal valid JPEG bytes (1x1 white pixel)
jpeg_b64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAT8AVP/Z"
data2 = json.dumps({"image": f"data:image/jpeg;base64,{jpeg_b64}"}).encode()
req2 = urllib.request.Request(
    f"{BASE}/detect/frame", data=data2,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
)
try:
    res2 = json.loads(urllib.request.urlopen(req2).read())
    print(f"\n/detect/frame OK: persons_detected={res2.get('persons_detected',0)}, items={len(res2.get('detected',[]))}")
    for d in res2.get("detected", []):
        print(f"  {d}")
except urllib.error.HTTPError as e:
    print(f"\n/detect/frame ERROR {e.code}: {e.read().decode()}")
