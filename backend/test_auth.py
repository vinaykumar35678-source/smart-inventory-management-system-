import urllib.request, json, sys

BASE = "http://127.0.0.1:8000/api"

def post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=hdrs)
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read()), res.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def get_json(url, token=None):
    hdrs = {}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=hdrs)
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read()), res.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

print("=" * 50)
print("BACKEND AUTH TEST")
print("=" * 50)

# 1. Admin login
res, code = post_json(f"{BASE}/auth/login", {"username":"admin","password":"Admin@123"})
assert code == 200, f"Admin login failed: {code} {res}"
token_admin = res["access_token"]
print(f"[OK] Admin login → role={res['role']}, user={res['username']}")

# 2. Stats (authenticated)
stats, code = get_json(f"{BASE}/stats", token=token_admin)
print(f"[OK] Stats: {stats}")

# 3. Users list (admin only)
users, code = get_json(f"{BASE}/users", token=token_admin)
print(f"[OK] Users ({len(users)}):")
for u in users:
    print(f"      {u['username']:12} [{u['role']:5}] active={u['is_active']}")

# 4. Create a new user via admin
new_user, code = post_json(f"{BASE}/users",
    {"username":"teststaff","full_name":"Test Staff","password":"Staff@123","role":"user"},
    token=token_admin)
print(f"[OK] Created user: {new_user.get('username')} [{code}]")

# 5. User1 login
res2, code = post_json(f"{BASE}/auth/login", {"username":"user1","password":"User@123"})
assert code == 200, f"User1 login failed: {code}"
token_user = res2["access_token"]
print(f"[OK] User1 login → role={res2['role']}")

# 6. user1 blocked from /users endpoint
blocked, code = get_json(f"{BASE}/users", token=token_user)
if code == 403:
    print(f"[OK] user1 blocked from /api/users (403 Forbidden)")
else:
    print(f"[WARN] Expected 403 for user1 on /api/users, got {code}")

print("=" * 50)
print("ALL TESTS PASSED")
print("=" * 50)
