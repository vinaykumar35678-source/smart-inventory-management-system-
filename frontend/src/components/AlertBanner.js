import React, { useState } from "react";
import { AlertTriangle, X } from "lucide-react";

function AlertBanner({ alerts = [] }) {
    const [dismissed, setDismissed] = useState(new Set());

    const visible = alerts.filter(
        (a) => !a.is_resolved && !dismissed.has(a.id)
    );

    if (visible.length === 0) return null;

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
            {visible.slice(0, 3).map((alert) => (
                <div
                    key={alert.id}
                    style={{
                        background: "var(--warning-subtle)",
                        border: "1px solid var(--warning-border)",
                        borderLeft: "4px solid var(--warning)",
                        borderRadius: "var(--radius-md)",
                        padding: "12px 16px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 12,
                        boxShadow: "var(--shadow-xs)",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{
                            width: 32,
                            height: 32,
                            borderRadius: "var(--radius-sm)",
                            background: "#FEF3C7",
                            color: "var(--warning)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0
                        }}>
                            <AlertTriangle size={18} />
                        </div>
                        <div>
                            <div
                                style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    color: "#92400E",
                                }}
                            >
                                Inventory Alert
                            </div>
                            <div style={{ fontSize: "0.8125rem", color: "#78350F", marginTop: 2 }}>
                                {alert.message}
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={() => setDismissed((prev) => new Set([...prev, alert.id]))}
                        style={{
                            background: "transparent",
                            border: "none",
                            cursor: "pointer",
                            color: "#92400E",
                            padding: 4,
                            borderRadius: "var(--radius-xs)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                        }}
                        title="Dismiss"
                    >
                        <X size={16} />
                    </button>
                </div>
            ))}
            {visible.length > 3 && (
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", textAlign: "center" }}>
                    +{visible.length - 3} additional unresolved alerts. View all in Alerts manager.
                </div>
            )}
        </div>
    );
}

export default AlertBanner;
