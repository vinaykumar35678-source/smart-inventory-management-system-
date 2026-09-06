import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

function StatCard({ icon, label, value, subtext, color = "blue", trend }) {
    const colorClasses = {
        blue: {
            bg: "var(--primary-subtle)",
            border: "var(--primary-border)",
            text: "var(--primary)",
        },
        green: {
            bg: "var(--success-subtle)",
            border: "var(--success-border)",
            text: "var(--success)",
        },
        yellow: {
            bg: "var(--warning-subtle)",
            border: "var(--warning-border)",
            text: "var(--warning)",
        },
        red: {
            bg: "var(--danger-subtle)",
            border: "var(--danger-border)",
            text: "var(--danger)",
        },
        purple: {
            bg: "#F5F3FF",
            border: "#DDD6FE",
            text: "#7C3AED",
        },
    };

    const c = colorClasses[color] || colorClasses.blue;

    return (
        <div
            className="card"
            style={{
                padding: "20px 22px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: 12,
            }}
        >
            <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
            }}>
                <div
                    style={{
                        width: 42,
                        height: 42,
                        borderRadius: "var(--radius-md)",
                        background: c.bg,
                        border: `1px solid ${c.border}`,
                        color: c.text,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                    }}
                >
                    {icon}
                </div>

                {trend !== undefined && (
                    <div
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            padding: "2px 8px",
                            borderRadius: "var(--radius-full)",
                            color: trend >= 0 ? "var(--success)" : "var(--danger)",
                            background: trend >= 0 ? "var(--success-subtle)" : "var(--danger-subtle)",
                            border: `1px solid ${trend >= 0 ? "var(--success-border)" : "var(--danger-border)"}`,
                        }}
                    >
                        {trend >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                        <span>{Math.abs(trend)}%</span>
                    </div>
                )}
            </div>

            <div>
                <div
                    style={{
                        fontSize: "1.875rem",
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        letterSpacing: "-0.03em",
                        lineHeight: 1.1,
                    }}
                >
                    {value}
                </div>
                <div
                    style={{
                        fontSize: "0.8125rem",
                        fontWeight: 600,
                        color: "var(--text-secondary)",
                        marginTop: 6,
                    }}
                >
                    {label}
                </div>
                {subtext && (
                    <div
                        style={{
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                            marginTop: 2,
                        }}
                    >
                        {subtext}
                    </div>
                )}
            </div>
        </div>
    );
}

export default StatCard;
