"""
run.py  — Start the Smart Shelf application
Usage:  python run.py
"""
from database import init_db
from seed import seed
from app import app, socketio

if __name__ == "__main__":
    init_db()
    seed()
    print("=" * 60)
    print("  Smart Shelf — Inventory Vision System")
    print("  Open browser: http://localhost:5000")
    print("  Admin login : admin / Admin@123")
    print("  Staff login : staff / Staff@123")
    print("=" * 60)
    socketio.run(app, debug=True, host="0.0.0.0", port=5000,
                 use_reloader=False, allow_unsafe_werkzeug=True)

