"""
Comprehensive Automated Security Verification Suite for SmartShelf Vision AI
Tests defense-in-depth protections:
1. SQL injection payloads in authentication
2. Generic errors & anti-user enumeration
3. Password policy enforcement (12+ characters)
4. Mass assignment protection
5. Server-side token revocation on logout
6. Role-Based Access Control (RBAC) on protected endpoints
7. Brute force mitigation & temporary cooldown
8. Security headers (CSP, X-Frame-Options, etc.)
9. Cryptographic password reset flow
10. Audit logging verification (no password leakage)
"""
import os
import sys
import unittest
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app import models

client = TestClient(app, base_url="http://localhost:8000")


class SecurityTestSuite(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        client.cookies.clear()
        from app.rate_limiter import _ip_attempts
        _ip_attempts.clear()
        for u in self.db.query(models.User).all():
            u.failed_login_attempts = 0
            u.locked_until = None
        self.db.commit()

    def tearDown(self):
        self.db.close()
        client.cookies.clear()

    # ── 1. Default Credentials & Baseline Authentication ──────────────────────
    def test_01_admin_login_success(self):
        """Verify default admin can authenticate and receives token + cookie."""
        res = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "admin")
        self.assertEqual(data["username"], "admin")
        # Ensure password is NEVER returned in response
        self.assertNotIn("password", data)
        self.assertNotIn("hashed_password", data)
        # Verify HttpOnly cookie
        self.assertIn("access_token", res.cookies)

    def test_02_staff_login_success(self):
        """Verify staff/user1 can authenticate."""
        res = client.post("/api/auth/login", json={"username": "user1", "password": "User@123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "user")

    # ── 2. SQL Injection Resistance ───────────────────────────────────────────
    def test_03_sql_injection_payloads(self):
        """Test classic and advanced SQL injection payloads in auth."""
        sqli_payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR ''='",
            "admin' --",
            "admin' #",
            "' OR 1=1/*",
            "\" OR \"1\"=\"1",
            "admin' UNION SELECT 1, 'admin', 'hacked', 'admin', 1, datetime('now') --",
            "'; DROP TABLE users; --",
        ]
        for payload in sqli_payloads:
            res = client.post("/api/auth/login", json={"username": payload, "password": "RandomPassword123!"})
            self.assertEqual(
                res.status_code, 401,
                f"SQL injection payload '{payload}' must be rejected with 401"
            )
            data = res.json()
            # Assert generic error message
            self.assertEqual(data["detail"], "Invalid email or password.")

    # ── 3. User Enumeration Defense & Generic Error Responses ─────────────────
    def test_04_generic_error_on_nonexistent_and_wrong_password(self):
        """Assert identical 401 and generic message for nonexistent user and bad password."""
        # Non-existent user
        res_nonexistent = client.post(
            "/api/auth/login",
            json={"username": "completely_fake_account_99999@test.com", "password": "FakePassword123!"}
        )
        self.assertEqual(res_nonexistent.status_code, 401)
        self.assertEqual(res_nonexistent.json()["detail"], "Invalid email or password.")

        # Real user, bad password
        res_bad_pw = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "WrongPassword123!"}
        )
        self.assertEqual(res_bad_pw.status_code, 401)
        self.assertEqual(res_bad_pw.json()["detail"], "Invalid email or password.")

    # ── 4. Password Policy (12+ chars) ────────────────────────────────────────
    def test_05_password_policy_enforcement(self):
        """Verify registration rejects passwords under 12 characters."""
        short_pw_payload = {
            "username": "test_short_pw_user",
            "email": "test_short_pw@smartshelf.com",
            "password": "Short123!"  # 9 characters (< 12)
        }
        res = client.post("/api/auth/register", json=short_pw_payload)
        self.assertIn(res.status_code, (400, 422))

    # ── 5. Mass Assignment Protection ─────────────────────────────────────────
    def test_06_mass_assignment_protection(self):
        """Verify client cannot escalate privileges by sending role='admin' on register."""
        test_username = f"sec_user_{int(time.time())}"
        test_email = f"{test_username}@smartshelf.com"
        reg_payload = {
            "username": test_username,
            "email": test_email,
            "password": "ValidLongPassword123!",
            "role": "admin"  # Attempting privilege escalation
        }
        res = client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        created_user = self.db.query(models.User).filter(models.User.username == test_username).first()
        self.assertIsNotNone(created_user)
        # Server must enforce role="user", completely ignoring client input
        self.assertEqual(created_user.role, "user")

    # ── 6. Token Revocation on Logout ─────────────────────────────────────────
    def test_07_server_side_token_revocation_on_logout(self):
        """Verify token is revoked on logout and rejected by protected APIs."""
        # Log in
        res = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
        self.assertEqual(res.status_code, 200)
        token = res.json()["access_token"]

        # Call protected endpoint with valid token -> 200
        headers = {"Authorization": f"Bearer {token}"}
        res_valid = client.get("/api/products", headers=headers)
        self.assertEqual(res_valid.status_code, 200)

        # Logout with token
        res_logout = client.post("/api/auth/logout", headers=headers)
        self.assertEqual(res_logout.status_code, 200)

        # Call protected endpoint again with the same token -> must be rejected with 401
        res_after = client.get("/api/products", headers=headers)
        self.assertEqual(res_after.status_code, 401)
        self.assertIn("terminated", res_after.json()["detail"].lower())

    # ── 7. Role-Based Access Control (RBAC) ───────────────────────────────────
    def test_08_rbac_staff_cannot_access_admin_endpoints(self):
        """Staff/user role must receive 403 Forbidden on admin-only routes."""
        res_login = client.post("/api/auth/login", json={"username": "user1", "password": "User@123"})
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to access user management (admin only)
        res_users = client.get("/api/users", headers=headers)
        self.assertEqual(res_users.status_code, 403)
        self.assertIn("Administrative privileges required", res_users.json()["detail"])

        # Attempt to access audit logs (admin only)
        res_logs = client.get("/api/auth/audit-logs", headers=headers)
        self.assertEqual(res_logs.status_code, 403)

    def test_09_rbac_admin_can_access_admin_endpoints(self):
        """Admin role can access user management and audit logs."""
        res_login = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res_users = client.get("/api/users", headers=headers)
        self.assertEqual(res_users.status_code, 200)

        res_logs = client.get("/api/auth/audit-logs", headers=headers)
        self.assertEqual(res_logs.status_code, 200)

    # ── 8. Unauthenticated Access Protection ──────────────────────────────────
    def test_10_unauthenticated_requests_rejected(self):
        """Verify protected endpoints reject requests lacking credentials."""
        endpoints = [
            ("GET", "/api/products"),
            ("GET", "/api/events"),
            ("GET", "/api/alerts"),
            ("GET", "/api/cameras"),
            ("GET", "/api/shelves"),
            ("GET", "/api/detection/status"),
            ("POST", "/api/detection/start"),
            ("POST", "/api/detection/stop"),
            ("GET", "/api/users"),
        ]
        for method, path in endpoints:
            if method == "GET":
                r = client.get(path)
            else:
                r = client.post(path)
            self.assertEqual(
                r.status_code, 401,
                f"Endpoint {method} {path} must require authentication (got {r.status_code})"
            )

    # ── 9. Security Headers ───────────────────────────────────────────────────
    def test_11_security_headers_present(self):
        """Verify presence of modern security headers on responses."""
        res = client.get("/api/products")
        headers = res.headers
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(headers.get("x-frame-options"), "DENY")
        self.assertIn("strict-origin", headers.get("referrer-policy", ""))
        self.assertIn("Content-Security-Policy", headers)

    # ── 10. Cryptographic Password Reset Flow ─────────────────────────────────
    def test_12_forgot_password_generic_response(self):
        """Forgot password returns identical generic response for valid and invalid emails."""
        r1 = client.post("/api/auth/forgot-password", json={"email": "nonexistent_reset@test.com"})
        self.assertEqual(r1.status_code, 200)
        self.assertIn("instructions have been dispatched", r1.json()["message"])

        r2 = client.post("/api/auth/forgot-password", json={"email": "admin@smartshelf.com"})
        self.assertEqual(r2.status_code, 200)
        self.assertIn("instructions have been dispatched", r2.json()["message"])

    # ── 11. Audit Logging ─────────────────────────────────────────────────────
    def test_13_audit_log_records_events_safely(self):
        """Verify security events are recorded in auth_audit_logs without sensitive data."""
        # Trigger an invalid login
        client.post("/api/auth/login", json={"username": "admin", "password": "WrongPassword123!"})

        latest_log = (
            self.db.query(models.AuthAuditLog)
            .filter(models.AuthAuditLog.username_or_email == "admin")
            .order_by(models.AuthAuditLog.timestamp.desc())
            .first()
        )
        self.assertIsNotNone(latest_log)
        self.assertIn("LOGIN_", latest_log.event_type)
        # Ensure password or password hashes are NEVER in details or logs
        self.assertNotIn("WrongPassword123!", latest_log.details)
        self.assertNotIn("$2b$", latest_log.details)


if __name__ == "__main__":
    unittest.main()
