import sqlite3
import os

def migrate_db(db_path):
    if not os.path.exists(db_path):
        return
    print(f"Migrating database at: {db_path}")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # 1. Create cameras table if not exists
    cur.execute('''
    CREATE TABLE IF NOT EXISTS cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR,
        location VARCHAR,
        source VARCHAR,
        camera_type VARCHAR,
        status VARCHAR,
        created_at DATETIME
    )''')

    # 2. Create shelves table if not exists
    cur.execute('''
    CREATE TABLE IF NOT EXISTS shelves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR UNIQUE,
        category VARCHAR,
        camera_id INTEGER,
        roi_x1 FLOAT,
        roi_y1 FLOAT,
        roi_x2 FLOAT,
        roi_y2 FLOAT,
        capacity INTEGER,
        current_count INTEGER,
        status VARCHAR,
        created_at DATETIME
    )''')

    # 3. Add columns to products if not exists
    prod_cols = [c[1] for c in cur.execute('PRAGMA table_info(products)').fetchall()]
    for col_name, col_def in [
        ('expected_stock', 'INTEGER DEFAULT 20'),
        ('shelf_id', 'INTEGER'),
        ('class_id', 'INTEGER'),
        ('sku', 'VARCHAR DEFAULT ""'),
        ('notification_state', 'VARCHAR DEFAULT "NORMAL"')
    ]:
        if col_name not in prod_cols:
            cur.execute(f'ALTER TABLE products ADD COLUMN {col_name} {col_def}')
            print(f'Added {col_name} to products')

    # 4. Add columns to events if not exists
    evt_cols = [c[1] for c in cur.execute('PRAGMA table_info(events)').fetchall()]
    for col_name, col_def in [
        ('event_id', 'VARCHAR'),
        ('event_type', 'VARCHAR DEFAULT "PRODUCT_REMOVED"'),
        ('product_id', 'INTEGER'),
        ('tracking_id', 'INTEGER'),
        ('camera_id', 'INTEGER'),
        ('shelf_id', 'INTEGER'),
        ('status', 'VARCHAR DEFAULT "VERIFIED"'),
        ('metadata_json', 'TEXT DEFAULT "{}"')
    ]:
        if col_name not in evt_cols:
            cur.execute(f'ALTER TABLE events ADD COLUMN {col_name} {col_def}')
            print(f'Added {col_name} to events')

    # 5. Add columns to alerts if not exists
    alt_cols = [c[1] for c in cur.execute('PRAGMA table_info(alerts)').fetchall()]
    for col_name, col_def in [
        ('severity', 'VARCHAR DEFAULT "WARNING"'),
        ('alert_type', 'VARCHAR DEFAULT "LOW_STOCK"'),
        ('shelf_id', 'INTEGER'),
        ('tracking_id', 'INTEGER')
    ]:
        if col_name not in alt_cols:
            cur.execute(f'ALTER TABLE alerts ADD COLUMN {col_name} {col_def}')
            print(f'Added {col_name} to alerts')

    # 6. Add security columns to users if not exists
    user_cols = [c[1] for c in cur.execute('PRAGMA table_info(users)').fetchall()]
    for col_name, col_def in [
        ('failed_login_attempts', 'INTEGER DEFAULT 0'),
        ('locked_until', 'DATETIME'),
        ('password_reset_token', 'VARCHAR'),
        ('password_reset_expires', 'DATETIME'),
        ('last_login_at', 'DATETIME'),
        ('updated_at', 'DATETIME')
    ]:
        if col_name not in user_cols:
            cur.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_def}')
            print(f'Added {col_name} to users')

    # 7. Create auth_audit_logs table if not exists
    cur.execute('''
    CREATE TABLE IF NOT EXISTS auth_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        event_type VARCHAR,
        username_or_email VARCHAR,
        ip_address VARCHAR,
        user_agent VARCHAR,
        details TEXT
    )''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_audit_event_type ON auth_audit_logs(event_type)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON auth_audit_logs(timestamp)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON auth_audit_logs(username_or_email)')

    # 8. Create revoked_tokens table if not exists
    cur.execute('''
    CREATE TABLE IF NOT EXISTS revoked_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jti VARCHAR UNIQUE,
        revoked_at DATETIME,
        expires_at DATETIME
    )''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_revoked_tokens_jti ON revoked_tokens(jti)')

    # 9. Create notification_logs table if not exists
    cur.execute('''
    CREATE TABLE IF NOT EXISTS notification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notification_id VARCHAR,
        user_id INTEGER,
        product_id INTEGER,
        product_name VARCHAR,
        alert_type VARCHAR DEFAULT "LOW_STOCK",
        recipient VARCHAR NOT NULL,
        status VARCHAR DEFAULT "PENDING",
        created_at DATETIME,
        sent_at DATETIME,
        error_message TEXT,
        retry_count INTEGER DEFAULT 0
    )''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_notif_id ON notification_logs(notification_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_notif_product ON notification_logs(product_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_notif_alert_type ON notification_logs(alert_type)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_notif_recipient ON notification_logs(recipient)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_notif_status ON notification_logs(status)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_notif_created_at ON notification_logs(created_at)')

    con.commit()
    con.close()
    print(f"Database migration completed for: {db_path}")

def migrate():
    backend_db = os.path.join(os.path.dirname(__file__), "inventory.db")
    root_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inventory.db"))
    
    migrate_db(backend_db)
    if os.path.exists(root_db) and os.path.abspath(backend_db) != os.path.abspath(root_db):
        migrate_db(root_db)

if __name__ == "__main__":
    migrate()
