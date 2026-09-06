"""
seed_from_ml_csv.py — Populate inventory.db with rich product & sales data from ML-Dataset.csv (inv.zip)
"""
import os
import pandas as pd
from datetime import datetime
from database import Session, Product, Event, init_db

CSV_PATH = os.path.join(os.path.dirname(__file__), "dataset", "ML-Dataset.csv")

def import_ml_dataset():
    init_db()
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] ML-Dataset.csv not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"[INFO] Loaded {len(df)} rows from ML-Dataset.csv")

    db = Session()
    try:
        products_imported = 0
        events_imported = 0

        # Group products by ProductName
        grouped = df.groupby("ProductName")

        for prod_name, group in grouped:
            category = str(group["CategoryName"].iloc[0]).strip() if "CategoryName" in group.columns else "General"
            price = float(group["PerUnitPrice"].iloc[0]) if "PerUnitPrice" in group.columns else 10.0
            
            # Compute total stock from TotalItemQuantity
            total_stock = int(group["TotalItemQuantity"].mean()) if "TotalItemQuantity" in group.columns else 20
            
            existing = db.query(Product).filter(Product.name == prod_name).first()
            if not existing:
                p = Product(
                    name=prod_name,
                    stock=max(5, total_stock),
                    threshold=5,
                    price=price,
                    category=category,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(p)
                products_imported += 1

        db.commit()

        # Import events history
        for idx, row in df.head(100).iterrows():
            prod_name = str(row["ProductName"]).strip()
            qty = int(row.get("OrderItemQuantity", 1))
            status = str(row.get("Status", "Shipped")).strip()
            event_type = "REMOVAL" if status in ["Shipped", "Delivered"] else "ADDITION"
            
            try:
                date_str = str(row.get("OrderDate", ""))
                ts = datetime.strptime(date_str, "%d-%b-%y")
            except Exception:
                ts = datetime.utcnow()

            ev = Event(
                product_name=prod_name,
                event_type=event_type,
                quantity_removed=qty if event_type == "REMOVAL" else -qty,
                confidence=0.95,
                timestamp=ts
            )
            db.add(ev)
            events_imported += 1

        db.commit()
        print(f"[SUCCESS] Imported {products_imported} unique products and {events_imported} historical transaction events into inventory.db!")

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Import failed: {exc}")
    finally:
        db.close()

if __name__ == "__main__":
    import_ml_dataset()
