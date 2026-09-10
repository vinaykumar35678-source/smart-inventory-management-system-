"""
sync_inventory_db.py — Ensure canonical products (Biscuits, Lays, Mobile, Pen)
are properly registered and synchronized across both inventory databases with correct class_ids.
"""
import sqlite3
import os
from datetime import datetime

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INV_DB = os.path.join(WORKSPACE, "inventory.db")
SMART_DB = os.path.join(WORKSPACE, "smart_shelf", "inventory.db")

PRODUCTS_TO_SYNC = [
    {
        "name": "Biscuits",
        "category": "Snacks",
        "stock": 25,
        "expected_stock": 30,
        "threshold": 5,
        "price": 2.50,
        "shelf_id": 1,
        "class_id": 6,
        "sku": "SKU-BISC-001"
    },
    {
        "name": "Lays",
        "category": "Snacks",
        "stock": 30,
        "expected_stock": 35,
        "threshold": 5,
        "price": 1.50,
        "shelf_id": 2,
        "class_id": 5,
        "sku": "SKU-LAYS-001"
    },
    {
        "name": "Mobile",
        "category": "Electronics",
        "stock": 15,
        "expected_stock": 20,
        "threshold": 3,
        "price": 299.00,
        "shelf_id": 3,
        "class_id": 12,
        "sku": "SKU-MOBL-001"
    },
    {
        "name": "Pen",
        "category": "Stationery",
        "stock": 50,
        "expected_stock": 60,
        "threshold": 10,
        "price": 1.00,
        "shelf_id": 4,
        "class_id": 16,
        "sku": "SKU-PENS-001"
    }
]

def sync_main_db():
    if not os.path.exists(INV_DB):
        print(f"[Main DB] Not found at {INV_DB}")
        return
    conn = sqlite3.connect(INV_DB)
    cur = conn.cursor()
    
    # Check if products table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    if not cur.fetchone():
        print("[Main DB] products table does not exist")
        conn.close()
        return

    now = datetime.utcnow().isoformat()
    for p in PRODUCTS_TO_SYNC:
        cur.execute("SELECT id FROM products WHERE name=?", (p["name"],))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE products 
                SET category=?, stock=?, expected_stock=?, threshold=?, price=?, shelf_id=?, class_id=?, sku=?, updated_at=?
                WHERE id=?
            """, (p["category"], p["stock"], p["expected_stock"], p["threshold"], p["price"], p["shelf_id"], p["class_id"], p["sku"], now, row[0]))
            print(f"[Main DB] Updated '{p['name']}' (ID: {row[0]}, Class: {p['class_id']})")
        else:
            cur.execute("""
                INSERT INTO products (name, stock, expected_stock, threshold, price, category, shelf_id, class_id, sku, notification_state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NORMAL', ?, ?)
            """, (p["name"], p["stock"], p["expected_stock"], p["threshold"], p["price"], p["category"], p["shelf_id"], p["class_id"], p["sku"], now, now))
            print(f"[Main DB] Inserted '{p['name']}' (Class: {p['class_id']})")

    conn.commit()
    conn.close()

def sync_smart_db():
    if not os.path.exists(SMART_DB):
        print(f"[Smart DB] Not found at {SMART_DB}")
        return
    conn = sqlite3.connect(SMART_DB)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    # smart_shelf products schema: id, name, stock, threshold, price, category, image_url, created_at, updated_at
    for p in PRODUCTS_TO_SYNC:
        # Check by name or alias
        cur.execute("SELECT id FROM products WHERE name=? OR name=?", (p["name"], f"{p['name']} Chips" if p["name"] == "Lays" else f"{p['name']} Phone"))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE products 
                SET name=?, category=?, stock=?, threshold=?, price=?, updated_at=?
                WHERE id=?
            """, (p["name"], p["category"], p["stock"], p["threshold"], p["price"], now, row[0]))
            print(f"[Smart DB] Updated '{p['name']}' (ID: {row[0]})")
        else:
            cur.execute("""
                INSERT INTO products (name, stock, threshold, price, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (p["name"], p["stock"], p["threshold"], p["price"], p["category"], now, now))
            print(f"[Smart DB] Inserted '{p['name']}'")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    sync_main_db()
    sync_smart_db()
    print("[OK] Databases synchronized successfully!")
