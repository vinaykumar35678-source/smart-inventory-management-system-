# -*- coding: utf-8 -*-
"""
seed.py  — Seed default admin user and sample products on first run.
"""
from datetime import datetime
import bcrypt
from database import Session, User, Product

def hash_password(password: str) -> str:
    pw_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')


def seed():
    db = Session()
    try:
        # ── Users ─────────────────────────────────────────────────────────
        if db.query(User).count() == 0:
            users = [
                User(
                    username="admin",
                    full_name="Administrator",
                    email="admin@smartshelf.com",
                    hashed_password=hash_password("Admin@123"),
                    role="admin",
                    is_active=True,
                    created_at=datetime.utcnow(),
                ),
                User(
                    username="staff",
                    full_name="Store Staff",
                    email="staff@smartshelf.com",
                    hashed_password=hash_password("Staff@123"),
                    role="user",
                    is_active=True,
                    created_at=datetime.utcnow(),
                ),
            ]
            for u in users:
                db.add(u)
            db.commit()
            print("[Seed] Created default admin and staff accounts.")

        # ── Products ──────────────────────────────────────────────────────
        if db.query(Product).count() == 0:
            products = [
                # Fruits
                Product(name="Apple",        stock=45, threshold=10, price=2.50,    category="Fruits",       image_url="🍎"),
                Product(name="Banana",       stock=30, threshold=8,  price=1.20,    category="Fruits",       image_url="🍌"),
                Product(name="Orange",       stock=25, threshold=8,  price=4.00,    category="Fruits",       image_url="🍊"),
                # Vegetables
                Product(name="Carrot",       stock=18, threshold=6,  price=3.00,    category="Vegetables",   image_url="🥕"),
                Product(name="Broccoli",     stock=12, threshold=5,  price=5.00,    category="Vegetables",   image_url="🥦"),
                # Dairy
                Product(name="Milk (1L)",    stock=8,  threshold=10, price=55.00,   category="Dairy",        image_url="🥛"),
                Product(name="Eggs (12)",    stock=6,  threshold=5,  price=80.00,   category="Dairy",        image_url="🥚"),
                # Food
                Product(name="Bread",        stock=15, threshold=5,  price=35.00,   category="Food",         image_url="🍞"),
                Product(name="Cake",         stock=10, threshold=4,  price=250.00,  category="Food",         image_url="🎂"),
                Product(name="Sandwich",     stock=12, threshold=5,  price=60.00,   category="Food",         image_url="🥪"),
                # Beverages
                Product(name="Bottle (Water)", stock=40, threshold=10, price=20.00, category="Beverages",    image_url="🍶"),
                Product(name="Coca Cola",      stock=24, threshold=6,  price=40.00, category="Beverages",    image_url="🥤"),
                # Snacks & Personal Care
                Product(name="Lays Chips",     stock=50, threshold=15, price=20.00, category="Food",         image_url="🥔"),
                Product(name="Biscuits",       stock=25, threshold=5,  price=20.00, category="Snacks",       image_url="🍪"),
                Product(name="Shampoo",        stock=20, threshold=5,  price=150.00, category="Personal Care",image_url="🧴"),
                Product(name="Toothpaste",     stock=30, threshold=8,  price=60.00,  category="Personal Care",image_url="🪥"),
                Product(name="Soap",           stock=45, threshold=10, price=45.00,  category="Personal Care",image_url="🧼"),
                # Electronics
                Product(name="Mobile Phone", stock=15, threshold=5,  price=8999.00, category="Electronics",  image_url="📱"),
                Product(name="Calculator",   stock=10, threshold=3,  price=499.00,  category="Electronics",  image_url="🖩"),
                Product(name="Laptop",       stock=5,  threshold=2,  price=45000.00, category="Electronics", image_url="💻"),
                # Stationery
                Product(name="Book",         stock=40, threshold=10, price=299.00,  category="Stationery",   image_url="📖"),
                Product(name="Pen",          stock=80, threshold=20, price=25.00,   category="Stationery",   image_url="🖊️"),
                Product(name="Paper Ream",   stock=20, threshold=5,  price=350.00,  category="Stationery",   image_url="📄"),
            ]
            now = datetime.utcnow()
            for p in products:
                p.created_at = now
                p.updated_at = now
                db.add(p)
            db.commit()
            print(f"[Seed] Seeded {len(products)} sample products.")
    finally:
        db.close()


if __name__ == "__main__":
    from database import init_db
    init_db()
    seed()
