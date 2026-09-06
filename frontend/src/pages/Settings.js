import React, { useEffect, useState, useCallback } from "react";
import api from "../api";
import {
    Sliders,
    Package,
    Download,
    FileSpreadsheet,
    CheckCircle2,
    AlertCircle,
    Info,
    Server,
    Code2,
    Cpu,
    Wifi,
    Database,
    Loader2,
    Mail,
    Send,
    ShieldCheck,
    HelpCircle
} from "lucide-react";

function Settings() {
    const [products, setProducts] = useState([]);
    const [globalThreshold, setGlobalThreshold] = useState(5);
    const [applying, setApplying] = useState(false);
    const [exporting, setExporting] = useState(false);
    const [toast, setToast] = useState(null);
    const [notifStatus, setNotifStatus] = useState(null);
    const [loadingNotif, setLoadingNotif] = useState(true);
    const [sendingTest, setSendingTest] = useState(false);
    const [showGuide, setShowGuide] = useState(false);

    const showToast = (msg, type = "success") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3500);
    };

    const fetchProducts = useCallback(async () => {
        const res = await api.get("/products");
        setProducts(res.data);
    }, []);

    const fetchNotifStatus = useCallback(async () => {
        setLoadingNotif(true);
        try {
            const res = await api.get("/notifications/status");
            setNotifStatus(res.data);
        } catch (e) {
            console.error("Failed to load notification status", e);
        } finally {
            setLoadingNotif(false);
        }
    }, []);

    useEffect(() => { 
        fetchProducts(); 
        fetchNotifStatus();
    }, [fetchProducts, fetchNotifStatus]);

    const sendTestEmail = async () => {
        setSendingTest(true);
        try {
            const res = await api.post("/notifications/test");
            showToast(res.data.message || "Test email queued successfully!", "success");
        } catch (e) {
            const errMsg = e.response?.data?.detail || "Failed to trigger test email.";
            showToast(errMsg, "error");
        } finally {
            setSendingTest(false);
        }
    };

    const applyGlobalThreshold = async () => {
        setApplying(true);
        try {
            await Promise.all(
                products.map((p) =>
                    api.put(`/products/${p.id}`, { threshold: Number(globalThreshold) })
                )
            );
            showToast(`Applied threshold of ${globalThreshold} to all ${products.length} products.`);
            fetchProducts();
        } catch (e) {
            showToast("Failed to update thresholds", "error");
        } finally {
            setApplying(false);
        }
    };

    const exportExcel = async () => {
        setExporting(true);
        try {
            const res = await api.get("/export/excel", { responseType: "blob" });
            const url = URL.createObjectURL(res.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = "inventory_export.xlsx";
            a.click();
            URL.revokeObjectURL(url);
            showToast("Excel spreadsheet downloaded successfully.");
        } catch (e) {
            showToast("Failed to export Excel", "error");
        } finally {
            setExporting(false);
        }
    };

    const StatRow = ({ label, value, color }) => (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
            <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>{label}</span>
            <span style={{ fontWeight: 600, color: color || "var(--text-primary)" }}>{value}</span>
        </div>
    );

    const lowStock = products.filter((p) => p.stock <= p.threshold).length;
    const categories = [...new Set(products.map((p) => p.category))].length;

    const techStack = [
        { icon: Server, label: "FastAPI Backend", desc: "Python 3.10+ ASGI" },
        { icon: Code2, label: "React 18 Frontend", desc: "Enterprise SPA" },
        { icon: Cpu, label: "YOLO Computer Vision", desc: "Object detection & pose" },
        { icon: Wifi, label: "WebSocket Real-Time", desc: "Sub-50ms push events" },
        { icon: Database, label: "SQLite DB & SQLAlchemy", desc: "Persistent store" },
        { icon: FileSpreadsheet, label: "OpenPyXL Exporter", desc: "Audit reporting" },
    ];

    return (
        <div className="page-content">
            {/* Toast Notification */}
            {toast && (
                <div style={{
                    position: "fixed",
                    bottom: 24,
                    right: 24,
                    zIndex: 9999,
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "12px 18px",
                    borderRadius: "var(--radius-md)",
                    background: toast.type === "success" ? "var(--success-subtle)" : "var(--danger-subtle)",
                    border: `1px solid ${toast.type === "success" ? "var(--success-border)" : "var(--danger-border)"}`,
                    color: toast.type === "success" ? "var(--success)" : "var(--danger)",
                    boxShadow: "var(--shadow-md)",
                    fontWeight: 500,
                    fontSize: "0.875rem"
                }}>
                    {toast.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                    <span>{toast.msg}</span>
                </div>
            )}

            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>Settings &amp; Administration</h1>
                    <p>Global threshold overrides, data export utilities, and architecture overview</p>
                </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {/* Threshold Settings */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <Sliders size={15} />
                            <span>Global Threshold Override</span>
                        </div>
                    </div>
                    <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 18 }}>
                        Configure the safety stock trigger level across all inventory items simultaneously.
                    </p>
                    <div className="form-group">
                        <label className="form-label">Global Minimum Stock Threshold</label>
                        <div style={{ display: "flex", gap: 10 }}>
                            <input
                                type="number"
                                className="form-input"
                                value={globalThreshold}
                                onChange={(e) => setGlobalThreshold(e.target.value)}
                                min={1}
                                style={{ flex: 1 }}
                            />
                            <button
                                className="btn btn-primary btn-sm"
                                onClick={applyGlobalThreshold}
                                disabled={applying}
                            >
                                {applying ? <Loader2 className="animate-spin" size={14} /> : null}
                                <span>{applying ? "Applying..." : "Apply to All"}</span>
                            </button>
                        </div>
                    </div>

                    <div style={{
                        marginTop: 12,
                        padding: "8px 12px",
                        background: "var(--surface-subtle)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.75rem",
                        color: "var(--text-secondary)",
                        display: "flex",
                        alignItems: "center",
                        gap: 8
                    }}>
                        <Info size={14} style={{ color: "var(--primary)", flexShrink: 0 }} />
                        <span>This action applies to all {products.length} registered items. Individual item thresholds remain customizable.</span>
                    </div>
                </div>

                {/* Email Notifications (Gmail) */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <Mail size={15} style={{ color: "var(--primary)" }} />
                            <span>Email Notifications (Gmail)</span>
                        </div>
                        {loadingNotif ? (
                            <Loader2 className="animate-spin" size={14} />
                        ) : notifStatus?.configured ? (
                            <span className="badge badge-success" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                                <CheckCircle2 size={12} />
                                <span>Gmail Configured ✓</span>
                            </span>
                        ) : (
                            <span className="badge badge-warning" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                                <AlertCircle size={12} />
                                <span>Not Configured</span>
                            </span>
                        )}
                    </div>
                    <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 14 }}>
                        Automated low-stock and out-of-stock Gmail alerts dispatched directly to the registered user's email.
                    </p>

                    <div style={{ background: "var(--surface-subtle)", borderRadius: "var(--radius-sm)", padding: "10px 14px", border: "1px solid var(--border-subtle)", marginBottom: 14 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", marginBottom: 6 }}>
                            <span style={{ color: "var(--text-secondary)" }}>SMTP Gateway:</span>
                            <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                                {notifStatus ? `${notifStatus.smtp_host}:${notifStatus.smtp_port}` : "smtp.gmail.com:587"}
                            </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", marginBottom: 6 }}>
                            <span style={{ color: "var(--text-secondary)" }}>Configured Sender:</span>
                            <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                                {notifStatus?.sender_masked || "Not configured"}
                            </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem" }}>
                            <span style={{ color: "var(--text-secondary)" }}>Registered Recipient:</span>
                            <span style={{ fontWeight: 600, color: "var(--primary)" }}>
                                {notifStatus?.registered_recipient || "Authenticated User"}
                            </span>
                        </div>
                    </div>

                    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                        <button
                            className="btn btn-primary btn-sm"
                            onClick={sendTestEmail}
                            disabled={sendingTest || !notifStatus?.configured}
                            title={!notifStatus?.configured ? "Configure Gmail in backend/.env first" : "Send a test email to verify credentials"}
                        >
                            {sendingTest ? <Loader2 className="animate-spin" size={14} /> : <Send size={14} />}
                            <span>{sendingTest ? "Sending Test..." : "Send Test Email"}</span>
                        </button>

                        <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setShowGuide(!showGuide)}
                            style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}
                        >
                            <HelpCircle size={14} />
                            <span>{showGuide ? "Hide Setup" : "Setup Guide"}</span>
                        </button>
                    </div>

                    {showGuide && (
                        <div style={{
                            background: "rgba(99, 102, 241, 0.05)",
                            border: "1px solid rgba(99, 102, 241, 0.2)",
                            borderRadius: "var(--radius-sm)",
                            padding: "10px 12px",
                            fontSize: "0.75rem",
                            color: "var(--text-secondary)",
                            lineHeight: 1.45,
                            marginTop: 12
                        }}>
                            <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
                                <ShieldCheck size={14} style={{ color: "var(--primary)" }} />
                                <span>Gmail App Password Setup:</span>
                            </div>
                            <ol style={{ margin: "0 0 0 16px", padding: 0 }}>
                                <li>Enable 2-Step Verification on your Google Account.</li>
                                <li>Create an App Password for <strong>Mail</strong> in Google Account &gt; Security.</li>
                                <li>Add <code>GMAIL_USERNAME</code> and <code>GMAIL_APP_PASSWORD</code> in <code>backend/.env</code>.</li>
                                <li>Restart the FastAPI backend.</li>
                            </ol>
                        </div>
                    )}
                </div>

                {/* Inventory Summary */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <Package size={15} />
                            <span>Catalog Metrics Summary</span>
                        </div>
                    </div>
                    <StatRow label="Registered Products" value={products.length} />
                    <StatRow label="Active Categories" value={categories} />
                    <StatRow label="Items Below Threshold" value={lowStock} color={lowStock > 0 ? "var(--danger)" : "var(--success)"} />
                    <StatRow label="Nominal Stock Items" value={products.length - lowStock} color="var(--success)" />
                </div>

                {/* Data Export */}
                <div className="card" style={{ gridColumn: "1 / -1" }}>
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <FileSpreadsheet size={15} />
                            <span>Spreadsheet Data Export</span>
                        </div>
                    </div>
                    <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 18 }}>
                        Generate and download a comprehensive Excel workbook (.xlsx) containing current inventory levels, prices, threshold markers, and compliance status.
                    </p>

                    <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
                        <button
                            className="btn btn-primary"
                            onClick={exportExcel}
                            disabled={exporting}
                        >
                            {exporting ? <Loader2 className="animate-spin" size={15} /> : <Download size={15} />}
                            <span>{exporting ? "Generating Report..." : "Export to Excel (.xlsx)"}</span>
                        </button>
                        <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                            Downloads <strong>inventory_export.xlsx</strong> with {products.length} inventory records.
                        </span>
                    </div>

                    {/* Preview Table */}
                    {products.length > 0 && (
                        <div style={{ marginTop: 22 }}>
                            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: 8 }}>
                                Dataset Preview (Sample):
                            </div>
                            <div className="table-container">
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Product</th>
                                            <th>Category</th>
                                            <th>Stock</th>
                                            <th>Threshold</th>
                                            <th>Price</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {products.slice(0, 5).map((p) => (
                                            <tr key={p.id}>
                                                <td style={{ fontWeight: 600 }}>{p.name}</td>
                                                <td><span className="badge badge-info">{p.category}</span></td>
                                                <td><strong>{p.stock}</strong></td>
                                                <td>{p.threshold}</td>
                                                <td>₹{p.price?.toFixed(2)}</td>
                                                <td>
                                                    <span className={`badge ${p.stock <= p.threshold ? "badge-danger" : "badge-success"}`}>
                                                        {p.stock <= p.threshold ? "Low Stock" : "Optimal"}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>

                {/* System Architecture */}
                <div className="card" style={{ gridColumn: "1 / -1" }}>
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <Info size={15} />
                            <span>System Architecture &amp; Technology Stack</span>
                        </div>
                    </div>
                    <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", lineHeight: 1.6, marginBottom: 16 }}>
                        <strong>SmartShelf Vision AI</strong> couples high-frequency optical frame sampling with YOLO neural networks and ByteTrack multi-object tracking to automatically log removals, additions, and misplaced retail items in real time.
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
                        {techStack.map(({ icon: Icon, label, desc }) => (
                            <div
                                key={label}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 12,
                                    padding: "12px 14px",
                                    background: "var(--surface-subtle)",
                                    border: "1px solid var(--border-subtle)",
                                    borderRadius: "var(--radius-md)"
                                }}
                            >
                                <div style={{
                                    width: 32,
                                    height: 32,
                                    borderRadius: "var(--radius-sm)",
                                    background: "var(--primary-subtle)",
                                    color: "var(--primary)",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    flexShrink: 0
                                }}>
                                    <Icon size={16} />
                                </div>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--text-primary)" }}>{label}</div>
                                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 1 }}>{desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Settings;
