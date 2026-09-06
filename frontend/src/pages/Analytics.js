import React, { useState, useEffect } from "react";
import api from "../api";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, CartesianGrid
} from "recharts";
import {
    TrendingUp,
    TrendingDown,
    ShieldAlert,
    PackageCheck,
    CheckCircle2,
    BarChart3,
    Layers,
    Package,
    Loader2
} from "lucide-react";

const COLORS = ["#2563EB", "#0284C7", "#16A34A", "#D97706", "#7C3AED", "#0D9488", "#DC2626"];

function Analytics() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchAnalytics = async () => {
        try {
            setLoading(true);
            const res = await api.get("/analytics");
            setData(res.data);
        } catch (err) {
            console.error("Error fetching analytics:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAnalytics();
    }, []);

    if (loading || !data) {
        return (
            <div className="page-content" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
                <div style={{ textAlign: "center", color: "var(--text-secondary)" }}>
                    <Loader2 className="animate-spin" size={32} style={{ color: "var(--primary)", margin: "0 auto 12px" }} />
                    <p style={{ fontSize: "0.875rem" }}>Aggregating system analytics...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>Inventory Intelligence &amp; Analytics</h1>
                    <p>Aggregated telemetry on stock velocity, product removals, shelf utilization, and security incidents</p>
                </div>
            </div>

            {/* Metric KPI Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>TOTAL UNITS ON SHELVES</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--primary-subtle)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <PackageCheck size={16} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.75rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {data.total_stock}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        Across {data.total_products} unique SKUs
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>CONFIRMED REMOVALS</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--danger-subtle)", color: "var(--danger)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <TrendingDown size={16} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.75rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {data.total_removals}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        Verified customer pickups
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>RESTOCKED UNITS</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--success-subtle)", color: "var(--success)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <TrendingUp size={16} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.75rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {data.total_additions}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        Replenishment confirmations
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>SECURITY INCIDENTS</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--warning-subtle)", color: "var(--warning)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <ShieldAlert size={16} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.75rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {data.suspicious_incidents_count}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        Unverified rapid zone exits
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr", gap: 20, marginBottom: 24 }}>
                {/* Most Removed Products */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <BarChart3 size={15} />
                            <span>Most Frequently Removed Products</span>
                        </div>
                    </div>
                    <div style={{ height: 270, marginTop: 8 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.top_removed_products} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                                <XAxis dataKey="product" stroke="var(--text-secondary)" fontSize={11} angle={-15} textAnchor="end" />
                                <YAxis stroke="var(--text-secondary)" fontSize={11} />
                                <Tooltip
                                    contentStyle={{
                                        background: "#FFFFFF",
                                        border: "1px solid var(--border-color)",
                                        borderRadius: 8,
                                        boxShadow: "var(--shadow-md)",
                                        fontSize: "0.8125rem"
                                    }}
                                />
                                <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Category Breakdown */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <Package size={15} />
                            <span>Stock Distribution by Category</span>
                        </div>
                    </div>
                    <div style={{ height: 270, display: "flex", alignItems: "center" }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={data.category_distribution}
                                    dataKey="stock"
                                    nameKey="category"
                                    cx="50%" cy="50%"
                                    outerRadius={85}
                                    innerRadius={50}
                                    paddingAngle={3}
                                    stroke="#FFFFFF"
                                    strokeWidth={2}
                                >
                                    {data.category_distribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        background: "#FFFFFF",
                                        border: "1px solid var(--border-color)",
                                        borderRadius: 8,
                                        boxShadow: "var(--shadow-md)",
                                        fontSize: "0.8125rem"
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                        <div style={{ minWidth: 140, display: "flex", flexDirection: "column", gap: 6, fontSize: "0.75rem" }}>
                            {data.category_distribution.map((c, i) => (
                                <div key={c.category} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS[i % COLORS.length] }} />
                                    <span style={{ color: "var(--text-secondary)" }}>{c.category}: <strong style={{ color: "var(--text-primary)" }}>{c.stock}</strong></span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Shelf Utilization & Loss Prevention Incidents */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {/* Shelf Capacity Utilization */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <Layers size={15} />
                            <span>Shelf Capacity Utilization</span>
                        </div>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 12 }}>
                        {data.shelf_utilization.map((s) => (
                            <div key={s.shelf_id}>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", marginBottom: 6 }}>
                                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{s.name} ({s.category})</span>
                                    <span style={{ fontWeight: 600, color: s.utilization_pct < 25 ? "var(--danger)" : "var(--success)" }}>
                                        {s.current_count} / {s.capacity} units ({s.utilization_pct}%)
                                    </span>
                                </div>
                                <div className="stock-bar">
                                    <div
                                        className="stock-fill"
                                        style={{
                                            width: `${Math.min(100, s.utilization_pct)}%`,
                                            background: s.utilization_pct < 25 ? "var(--danger)" : s.utilization_pct < 50 ? "var(--warning)" : "var(--success)"
                                        }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Recent Loss Prevention Flags */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <ShieldAlert size={15} style={{ color: "var(--warning)" }} />
                            <span>Loss Prevention Flags ({data.recent_suspicious_incidents?.length || 0})</span>
                        </div>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8, maxHeight: 270, overflowY: "auto" }}>
                        {!data.recent_suspicious_incidents || data.recent_suspicious_incidents.length === 0 ? (
                            <div className="empty-state" style={{ padding: "32px 0" }}>
                                <CheckCircle2 size={28} style={{ color: "var(--success)" }} />
                                <p>No loss prevention flags detected.</p>
                            </div>
                        ) : (
                            data.recent_suspicious_incidents.map((inc) => (
                                <div
                                    key={inc.id}
                                    style={{
                                        background: "var(--warning-subtle)",
                                        border: "1px solid var(--warning-border)",
                                        borderLeft: "3px solid var(--warning)",
                                        padding: "10px 14px",
                                        borderRadius: "var(--radius-md)",
                                        fontSize: "0.8125rem"
                                    }}
                                >
                                    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 600, color: "#92400E" }}>
                                        <span>Product: {inc.product}</span>
                                        <span style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
                                            {inc.timestamp ? new Date(inc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""}
                                        </span>
                                    </div>
                                    <div style={{ color: "#78350F", marginTop: 4 }}>
                                        {inc.message}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Analytics;
