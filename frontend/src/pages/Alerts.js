import React, { useEffect, useState, useCallback } from "react";
import api from "../api";
import { AlertTriangle, CheckCircle2, Clock, Check, Loader2 } from "lucide-react";

function Alerts() {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("all"); // all | unresolved | resolved
    const [resolving, setResolving] = useState(null);

    const fetchAlerts = useCallback(async () => {
        try {
            const res = await api.get("/alerts");
            setAlerts(res.data);
        } catch (e) {
            console.error("Failed to fetch alerts:", e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAlerts();
        const iv = setInterval(fetchAlerts, 8000);
        return () => clearInterval(iv);
    }, [fetchAlerts]);

    const resolve = async (id) => {
        setResolving(id);
        try {
            await api.post(`/alerts/${id}/resolve`);
            fetchAlerts();
        } catch (e) {
            console.error("Failed to resolve alert:", e);
        } finally {
            setResolving(null);
        }
    };

    const filtered = alerts.filter((a) => {
        if (filter === "unresolved") return !a.is_resolved;
        if (filter === "resolved") return a.is_resolved;
        return true;
    });

    const unresolvedCount = alerts.filter((a) => !a.is_resolved).length;

    const formatDate = (ts) => {
        if (!ts) return "";
        return new Date(ts).toLocaleString("en-US", {
            month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
        });
    };

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>System Alerts &amp; Incidents</h1>
                    <p>Real-time low-stock alerts, safety stock thresholds, and security anomaly notifications</p>
                </div>
                {unresolvedCount > 0 && (
                    <span className="badge badge-warning" style={{ fontSize: "0.8125rem", padding: "4px 10px" }}>
                        <span className="status-dot warning" />
                        <span>{unresolvedCount} Active Alerts</span>
                    </span>
                )}
            </div>

            {/* Filter Tabs */}
            <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
                {[
                    { key: "all", label: `All Alerts (${alerts.length})` },
                    { key: "unresolved", label: `Active (${unresolvedCount})` },
                    { key: "resolved", label: `Resolved (${alerts.length - unresolvedCount})` },
                ].map(({ key, label }) => (
                    <button
                        key={key}
                        className="btn btn-sm"
                        onClick={() => setFilter(key)}
                        style={{
                            background: filter === key ? "var(--primary-subtle)" : "var(--surface-bg)",
                            color: filter === key ? "var(--primary)" : "var(--text-secondary)",
                            borderColor: filter === key ? "var(--primary-border)" : "var(--border-color)",
                            fontWeight: filter === key ? 600 : 500
                        }}
                    >
                        {label}
                    </button>
                ))}
            </div>

            {loading ? (
                <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 60, flexDirection: "column", gap: 12 }}>
                    <Loader2 className="animate-spin" size={32} style={{ color: "var(--primary)" }} />
                    <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Loading system alerts...</p>
                </div>
            ) : filtered.length === 0 ? (
                <div className="card empty-state" style={{ padding: 48 }}>
                    <CheckCircle2 size={36} style={{ color: "var(--success)" }} />
                    <h3>No alerts in this view</h3>
                    <p>All monitored product shelves and inventory levels are operating within nominal thresholds.</p>
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {filtered.map((alert) => {
                        const isResolved = alert.is_resolved;
                        return (
                            <div
                                key={alert.id}
                                style={{
                                    background: isResolved ? "var(--surface-bg)" : "var(--warning-subtle)",
                                    border: `1px solid ${isResolved ? "var(--border-color)" : "var(--warning-border)"}`,
                                    borderLeft: `4px solid ${isResolved ? "var(--success)" : "var(--warning)"}`,
                                    borderRadius: "var(--radius-md)",
                                    padding: "16px 20px",
                                    display: "flex",
                                    alignItems: "flex-start",
                                    justifyContent: "space-between",
                                    gap: 16,
                                    boxShadow: "var(--shadow-xs)"
                                }}
                            >
                                <div style={{ display: "flex", gap: 14, flex: 1, alignItems: "flex-start" }}>
                                    <div style={{
                                        width: 36,
                                        height: 36,
                                        borderRadius: "var(--radius-md)",
                                        background: isResolved ? "var(--success-subtle)" : "#FEF3C7",
                                        color: isResolved ? "var(--success)" : "var(--warning)",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        flexShrink: 0
                                    }}>
                                        {isResolved ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 4 }}>
                                            <span style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--text-primary)" }}>
                                                {alert.product_name}
                                            </span>
                                            <span className={`badge ${isResolved ? "badge-success" : "badge-warning"}`}>
                                                {isResolved ? "Resolved" : "Active Incident"}
                                            </span>
                                        </div>
                                        <p style={{ fontSize: "0.875rem", color: isResolved ? "var(--text-secondary)" : "#92400E", marginBottom: 6 }}>
                                            {alert.message}
                                        </p>
                                        <div style={{ display: "flex", gap: 16, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                                <Clock size={12} />
                                                <span>Triggered: {formatDate(alert.timestamp)}</span>
                                            </span>
                                            {isResolved && alert.resolved_at && (
                                                <span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--success)" }}>
                                                    <Check size={12} />
                                                    <span>Resolved: {formatDate(alert.resolved_at)}</span>
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                {!isResolved && (
                                    <button
                                        className="btn btn-sm btn-secondary"
                                        onClick={() => resolve(alert.id)}
                                        disabled={resolving === alert.id}
                                        style={{ flexShrink: 0 }}
                                    >
                                        {resolving === alert.id ? (
                                            <Loader2 className="animate-spin" size={13} />
                                        ) : (
                                            <Check size={13} />
                                        )}
                                        <span>Resolve</span>
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

export default Alerts;
