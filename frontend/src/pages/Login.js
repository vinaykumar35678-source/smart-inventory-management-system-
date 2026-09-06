import React, { useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import {
    Boxes,
    Eye,
    EyeOff,
    AlertCircle,
    CheckCircle2,
    Loader2,
    ArrowLeft
} from "lucide-react";

function Login() {
    const { login } = useAuth();

    // Mode: 'login' | 'forgot_password'
    const [viewMode, setViewMode] = useState("login");

    // Login form states
    const [identifier, setIdentifier] = useState("");
    const [password, setPassword] = useState("");
    const [rememberMe, setRememberMe] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [loginLoading, setLoginLoading] = useState(false);
    const [loginError, setLoginError] = useState("");

    // Forgot password states
    const [resetEmail, setResetEmail] = useState("");
    const [resetLoading, setResetLoading] = useState(false);
    const [resetMessage, setResetMessage] = useState("");
    const [resetError, setResetError] = useState("");

    // ── Login Submit Handler ───────────────────────────────────────────────────
    const handleLoginSubmit = async (e) => {
        e.preventDefault();
        setLoginError("");

        const cleanIdentifier = identifier.trim();
        if (!cleanIdentifier || !password) {
            setLoginError("Please enter both your email or username and password.");
            return;
        }

        if (cleanIdentifier.length > 254 || password.length > 128) {
            setLoginError("Invalid input length. Please check your credentials.");
            return;
        }

        setLoginLoading(true);

        try {
            const res = await api.post("/auth/login", {
                username_or_email: cleanIdentifier,
                password: password,
                remember_me: rememberMe
            });

            // Hand off safe user session to context
            login(res.data);
        } catch (err) {
            // Never expose technical tracebacks or schema errors to users (Generic Login Errors)
            const status = err.response?.status;
            if (status === 401 || status === 403 || status === 400 || status === 422) {
                setLoginError("Invalid email or password.");
            } else {
                setLoginError("Unable to connect to the authentication service. Please try again later.");
            }
        } finally {
            setLoginLoading(false);
        }
    };

    // ── Forgot Password Submit Handler ─────────────────────────────────────────
    const handleForgotPasswordSubmit = async (e) => {
        e.preventDefault();
        setResetError("");
        setResetMessage("");

        const cleanEmail = resetEmail.trim();
        if (!cleanEmail) {
            setResetError("Please enter your registered email address.");
            return;
        }

        setResetLoading(true);

        try {
            const res = await api.post("/auth/forgot-password", {
                email: cleanEmail
            });
            // Generic security response
            setResetMessage(res.data?.message || "If an account exists for this email, password reset instructions have been dispatched.");
        } catch {
            // Generic message even on server error to prevent information disclosure
            setResetMessage("If an account exists for this email, password reset instructions have been dispatched.");
        } finally {
            setResetLoading(false);
        }
    };

    // Quick demo autofill helper
    const fillCredentials = (u, p) => {
        setIdentifier(u);
        setPassword(p);
        setLoginError("");
    };

    return (
        <div style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--bg-canvas, #F8FAFC)",
            fontFamily: "var(--font-sans)",
            padding: "24px 16px"
        }}>
            <div style={{
                width: "100%",
                maxWidth: 440,
                background: "var(--bg-surface, #FFFFFF)",
                border: "1px solid var(--border-color, #E2E8F0)",
                borderRadius: "var(--radius-lg, 10px)",
                boxShadow: "var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.05))",
                padding: "36px 32px"
            }}>
                {/* ── Brand Header ────────────────────────────────────────── */}
                <div style={{ textAlign: "center", marginBottom: 28 }}>
                    <div style={{
                        width: 48,
                        height: 48,
                        background: "var(--primary-light, #EFF6FF)",
                        border: "1px solid #BFDBFE",
                        borderRadius: "var(--radius-md, 8px)",
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "var(--primary, #2563EB)",
                        marginBottom: 12
                    }}>
                        <Boxes size={26} />
                    </div>

                    <h1 style={{
                        fontSize: "1.25rem",
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                        color: "var(--text-primary, #0F172A)",
                        margin: "0 0 4px 0"
                    }}>
                        SMARTSHELF
                    </h1>

                    <p style={{
                        fontSize: "0.8125rem",
                        color: "var(--text-secondary, #475569)",
                        margin: 0,
                        fontWeight: 500
                    }}>
                        Vision AI Inventory System
                    </p>
                </div>

                {/* ── View 1: Main Login Form ─────────────────────────────── */}
                {viewMode === "login" && (
                    <>
                        <form onSubmit={handleLoginSubmit} noValidate aria-labelledby="login-heading">
                            <h2 id="login-heading" className="sr-only" style={{ display: "none" }}>
                                Sign In
                            </h2>

                            {/* Email / Username Field */}
                            <div className="form-group" style={{ marginBottom: 18 }}>
                                <label
                                    htmlFor="login-identifier"
                                    className="form-label"
                                    style={{
                                        display: "block",
                                        fontSize: "0.8125rem",
                                        fontWeight: 600,
                                        color: "var(--text-primary, #0F172A)",
                                        marginBottom: 6
                                    }}
                                >
                                    Email / Username
                                </label>
                                <input
                                    id="login-identifier"
                                    name="identifier"
                                    type="text"
                                    className="form-input"
                                    placeholder="Enter your email or username"
                                    value={identifier}
                                    onChange={(e) => setIdentifier(e.target.value)}
                                    maxLength={254}
                                    autoComplete="username"
                                    disabled={loginLoading}
                                    required
                                    autoFocus
                                    style={{
                                        width: "100%",
                                        padding: "10px 12px",
                                        fontSize: "0.875rem",
                                        borderRadius: "var(--radius-md, 8px)",
                                        border: "1px solid var(--border-color, #E2E8F0)",
                                        background: "var(--bg-surface, #FFFFFF)",
                                        color: "var(--text-primary, #0F172A)",
                                        boxSizing: "border-box"
                                    }}
                                />
                            </div>

                            {/* Password Field */}
                            <div className="form-group" style={{ marginBottom: 18 }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                                    <label
                                        htmlFor="login-password"
                                        className="form-label"
                                        style={{
                                            fontSize: "0.8125rem",
                                            fontWeight: 600,
                                            color: "var(--text-primary, #0F172A)"
                                        }}
                                    >
                                        Password
                                    </label>
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        aria-label={showPassword ? "Hide password" : "Show password"}
                                        style={{
                                            background: "none",
                                            border: "none",
                                            padding: 0,
                                            color: "var(--text-secondary, #475569)",
                                            fontSize: "0.75rem",
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: 4,
                                            cursor: "pointer"
                                        }}
                                    >
                                        {showPassword ? (
                                            <>
                                                <EyeOff size={14} />
                                                <span>Hide password</span>
                                            </>
                                        ) : (
                                            <>
                                                <Eye size={14} />
                                                <span>Show password</span>
                                            </>
                                        )}
                                    </button>
                                </div>

                                <input
                                    id="login-password"
                                    name="password"
                                    type={showPassword ? "text" : "password"}
                                    className="form-input"
                                    placeholder="Enter your password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    maxLength={128}
                                    autoComplete="current-password"
                                    disabled={loginLoading}
                                    required
                                    style={{
                                        width: "100%",
                                        padding: "10px 12px",
                                        fontSize: "0.875rem",
                                        borderRadius: "var(--radius-md, 8px)",
                                        border: "1px solid var(--border-color, #E2E8F0)",
                                        background: "var(--bg-surface, #FFFFFF)",
                                        color: "var(--text-primary, #0F172A)",
                                        boxSizing: "border-box"
                                    }}
                                />
                            </div>

                            {/* Options: Remember Me & Forgot Password */}
                            <div style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                marginBottom: 20,
                                fontSize: "0.8125rem"
                            }}>
                                <label style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8,
                                    cursor: "pointer",
                                    color: "var(--text-secondary, #475569)"
                                }}>
                                    <input
                                        type="checkbox"
                                        id="remember-me"
                                        checked={rememberMe}
                                        onChange={(e) => setRememberMe(e.target.checked)}
                                        disabled={loginLoading}
                                        style={{ width: 15, height: 15, cursor: "pointer" }}
                                    />
                                    <span>Remember me</span>
                                </label>

                                <button
                                    type="button"
                                    onClick={() => {
                                        setViewMode("forgot_password");
                                        setLoginError("");
                                        setResetMessage("");
                                    }}
                                    style={{
                                        background: "none",
                                        border: "none",
                                        padding: 0,
                                        color: "var(--primary, #2563EB)",
                                        cursor: "pointer",
                                        fontSize: "0.8125rem",
                                        fontWeight: 500
                                    }}
                                >
                                    Forgot Password?
                                </button>
                            </div>

                            {/* Generic Error Banner */}
                            {loginError && (
                                <div
                                    role="alert"
                                    style={{
                                        background: "#FEF2F2",
                                        border: "1px solid #FCA5A5",
                                        borderRadius: "var(--radius-sm, 6px)",
                                        padding: "10px 14px",
                                        marginBottom: 18,
                                        color: "#DC2626",
                                        fontSize: "0.8125rem",
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 8
                                    }}
                                >
                                    <AlertCircle size={16} style={{ flexShrink: 0 }} />
                                    <span>{loginError}</span>
                                </div>
                            )}

                            {/* Submit Button with Busy State */}
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={loginLoading}
                                aria-busy={loginLoading}
                                style={{
                                    width: "100%",
                                    padding: "11px 16px",
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    background: "var(--primary, #2563EB)",
                                    color: "#FFFFFF",
                                    border: "none",
                                    borderRadius: "var(--radius-md, 8px)",
                                    cursor: loginLoading ? "not-allowed" : "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    gap: 8,
                                    transition: "background 0.15s ease"
                                }}
                            >
                                {loginLoading ? (
                                    <>
                                        <Loader2 className="animate-spin" size={16} />
                                        <span>Signing in...</span>
                                    </>
                                ) : (
                                    <span>Sign In</span>
                                )}
                            </button>
                        </form>

                        {/* Demo Credentials Quick Chips */}
                        <div style={{
                            marginTop: 24,
                            padding: "12px 14px",
                            background: "var(--bg-subtle, #F1F5F9)",
                            borderRadius: "var(--radius-md, 8px)",
                            fontSize: "0.75rem",
                            border: "1px solid var(--border-subtle, #F1F5F9)"
                        }}>
                            <div style={{
                                fontWeight: 600,
                                color: "var(--text-primary, #0F172A)",
                                marginBottom: 6
                            }}>
                                Quick Demo Credentials:
                            </div>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                                <button
                                    type="button"
                                    onClick={() => fillCredentials("admin", "Admin@123")}
                                    style={{
                                        background: "var(--bg-surface, #FFFFFF)",
                                        border: "1px solid var(--border-color, #E2E8F0)",
                                        borderRadius: "var(--radius-sm, 6px)",
                                        padding: "4px 8px",
                                        fontSize: "0.75rem",
                                        cursor: "pointer",
                                        color: "var(--text-secondary, #475569)"
                                    }}
                                >
                                    Admin (<code>admin</code> / <code>Admin@123</code>)
                                </button>
                                <button
                                    type="button"
                                    onClick={() => fillCredentials("user1", "User@123")}
                                    style={{
                                        background: "var(--bg-surface, #FFFFFF)",
                                        border: "1px solid var(--border-color, #E2E8F0)",
                                        borderRadius: "var(--radius-sm, 6px)",
                                        padding: "4px 8px",
                                        fontSize: "0.75rem",
                                        cursor: "pointer",
                                        color: "var(--text-secondary, #475569)"
                                    }}
                                >
                                    Staff (<code>user1</code> / <code>User@123</code>)
                                </button>
                            </div>
                        </div>
                    </>
                )}

                {/* ── View 2: Forgot Password Form ────────────────────────── */}
                {viewMode === "forgot_password" && (
                    <form onSubmit={handleForgotPasswordSubmit} noValidate aria-labelledby="reset-heading">
                        <div style={{ marginBottom: 18 }}>
                            <button
                                type="button"
                                onClick={() => {
                                    setViewMode("login");
                                    setResetError("");
                                    setResetMessage("");
                                }}
                                style={{
                                    background: "none",
                                    border: "none",
                                    padding: 0,
                                    color: "var(--text-secondary, #475569)",
                                    fontSize: "0.8125rem",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: 6,
                                    cursor: "pointer",
                                    marginBottom: 12
                                }}
                            >
                                <ArrowLeft size={14} />
                                <span>Back to Sign In</span>
                            </button>

                            <h2
                                id="reset-heading"
                                style={{
                                    fontSize: "1.125rem",
                                    fontWeight: 700,
                                    color: "var(--text-primary, #0F172A)",
                                    margin: "0 0 6px 0"
                                }}
                            >
                                Reset Password
                            </h2>
                            <p style={{
                                fontSize: "0.8125rem",
                                color: "var(--text-secondary, #475569)",
                                margin: 0,
                                lineHeight: 1.5
                            }}>
                                Enter your registered account email to request secure password reset instructions.
                            </p>
                        </div>

                        {/* Reset Email Input */}
                        <div className="form-group" style={{ marginBottom: 18 }}>
                            <label
                                htmlFor="reset-email-input"
                                className="form-label"
                                style={{
                                    display: "block",
                                    fontSize: "0.8125rem",
                                    fontWeight: 600,
                                    color: "var(--text-primary, #0F172A)",
                                    marginBottom: 6
                                }}
                            >
                                Email Address
                            </label>
                            <input
                                id="reset-email-input"
                                type="email"
                                className="form-input"
                                placeholder="name@company.com"
                                value={resetEmail}
                                onChange={(e) => setResetEmail(e.target.value)}
                                maxLength={254}
                                disabled={resetLoading}
                                required
                                autoFocus
                                style={{
                                    width: "100%",
                                    padding: "10px 12px",
                                    fontSize: "0.875rem",
                                    borderRadius: "var(--radius-md, 8px)",
                                    border: "1px solid var(--border-color, #E2E8F0)",
                                    background: "var(--bg-surface, #FFFFFF)",
                                    color: "var(--text-primary, #0F172A)",
                                    boxSizing: "border-box"
                                }}
                            />
                        </div>

                        {/* Feedback Messages */}
                        {resetError && (
                            <div
                                role="alert"
                                style={{
                                    background: "#FEF2F2",
                                    border: "1px solid #FCA5A5",
                                    borderRadius: "var(--radius-sm, 6px)",
                                    padding: "10px 14px",
                                    marginBottom: 18,
                                    color: "#DC2626",
                                    fontSize: "0.8125rem",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8
                                }}
                            >
                                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                                <span>{resetError}</span>
                            </div>
                        )}

                        {resetMessage && (
                            <div
                                role="status"
                                style={{
                                    background: "#F0FDF4",
                                    border: "1px solid #86EFAC",
                                    borderRadius: "var(--radius-sm, 6px)",
                                    padding: "10px 14px",
                                    marginBottom: 18,
                                    color: "#16A34A",
                                    fontSize: "0.8125rem",
                                    display: "flex",
                                    alignItems: "flex-start",
                                    gap: 8,
                                    lineHeight: 1.4
                                }}
                            >
                                <CheckCircle2 size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                                <span>{resetMessage}</span>
                            </div>
                        )}

                        {/* Submit Button */}
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={resetLoading}
                            style={{
                                width: "100%",
                                padding: "11px 16px",
                                fontSize: "0.875rem",
                                fontWeight: 600,
                                background: "var(--primary, #2563EB)",
                                color: "#FFFFFF",
                                border: "none",
                                borderRadius: "var(--radius-md, 8px)",
                                cursor: resetLoading ? "not-allowed" : "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 8
                            }}
                        >
                            {resetLoading ? (
                                <>
                                    <Loader2 className="animate-spin" size={16} />
                                    <span>Sending reset link...</span>
                                </>
                            ) : (
                                <span>Send Reset Instructions</span>
                            )}
                        </button>
                    </form>
                )}

                {/* Footer Security Notice */}
                <div style={{
                    marginTop: 24,
                    textAlign: "center",
                    fontSize: "0.75rem",
                    color: "var(--text-muted, #94A3B8)"
                }}>
                    Protected by SmartShelf Enterprise Security · Rate-Limited &amp; Encrypted
                </div>
            </div>
        </div>
    );
}

export default Login;
