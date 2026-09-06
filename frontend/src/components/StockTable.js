import React, { useState } from "react";
import { Search, Edit2, Trash2, Package, ArrowUpDown } from "lucide-react";

const CATEGORIES = ["All", "Fruits", "Vegetables", "Dairy", "Bakery", "Beverages", "General"];

function StockTable({ products = [], onEdit, onDelete }) {
    const [filter, setFilter] = useState("All");
    const [search, setSearch] = useState("");
    const [sortKey, setSortKey] = useState("name");
    const [sortDir, setSortDir] = useState("asc");

    const handleSort = (key) => {
        if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        else { setSortKey(key); setSortDir("asc"); }
    };

    const filtered = products
        .filter((p) => (filter === "All" ? true : p.category === filter))
        .filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
        .sort((a, b) => {
            const av = a[sortKey], bv = b[sortKey];
            if (typeof av === "string") return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
            return sortDir === "asc" ? av - bv : bv - av;
        });

    return (
        <div>
            {/* Toolbar */}
            <div style={{
                display: "flex",
                gap: 12,
                marginBottom: 16,
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between"
            }}>
                <div style={{ position: "relative", minWidth: 260, maxWidth: 360, flex: 1 }}>
                    <Search
                        size={15}
                        style={{
                            position: "absolute",
                            left: 10,
                            top: "50%",
                            transform: "translateY(-50%)",
                            color: "var(--text-muted)",
                            pointerEvents: "none"
                        }}
                    />
                    <input
                        type="text"
                        className="form-input"
                        placeholder="Search products by name..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        style={{ paddingLeft: 32 }}
                    />
                </div>

                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {CATEGORIES.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setFilter(cat)}
                            className="btn btn-sm"
                            style={{
                                background: filter === cat ? "var(--primary-subtle)" : "var(--surface-bg)",
                                color: filter === cat ? "var(--primary)" : "var(--text-secondary)",
                                borderColor: filter === cat ? "var(--primary-border)" : "var(--border-color)",
                                fontWeight: filter === cat ? 600 : 500,
                            }}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* Table */}
            <div className="table-container">
                <table className="data-table">
                    <thead>
                        <tr>
                            {[
                                { key: "name", label: "Product" },
                                { key: "category", label: "Category" },
                                { key: "stock", label: "Stock Level" },
                                { key: "threshold", label: "Min Threshold" },
                                { key: "price", label: "Price" },
                            ].map(({ key, label }) => (
                                <th
                                    key={key}
                                    onClick={() => handleSort(key)}
                                    style={{ cursor: "pointer", userSelect: "none" }}
                                >
                                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                        <span>{label}</span>
                                        <ArrowUpDown size={12} style={{ opacity: sortKey === key ? 1 : 0.4 }} />
                                    </div>
                                </th>
                            ))}
                            <th>Status</th>
                            <th style={{ textAlign: "right" }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.length === 0 ? (
                            <tr>
                                <td colSpan={7} style={{ textAlign: "center", padding: "48px 16px", color: "var(--text-muted)" }}>
                                    <Package size={32} style={{ opacity: 0.3, margin: "0 auto 8px" }} />
                                    <div style={{ fontWeight: 500 }}>No products found</div>
                                    <div style={{ fontSize: "0.8125rem", marginTop: 4 }}>Try adjusting your search or category filter</div>
                                </td>
                            </tr>
                        ) : (
                            filtered.map((p) => {
                                const isLow = p.stock <= p.threshold;
                                const pct = Math.min((p.stock / Math.max(p.threshold * 3, 1)) * 100, 100);
                                return (
                                    <tr key={p.id}>
                                        <td>
                                            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                                                <div style={{
                                                    width: 32,
                                                    height: 32,
                                                    borderRadius: "var(--radius-sm)",
                                                    background: "var(--surface-subtle)",
                                                    border: "1px solid var(--border-subtle)",
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent: "center",
                                                    color: "var(--text-secondary)",
                                                    flexShrink: 0
                                                }}>
                                                    <Package size={16} />
                                                </div>
                                                <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{p.name}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="badge badge-info">{p.category || "General"}</span>
                                        </td>
                                        <td>
                                            <div style={{ display: "flex", flexDirection: "column", gap: 4, width: 110 }}>
                                                <span style={{
                                                    fontWeight: 600,
                                                    fontSize: "0.875rem",
                                                    color: isLow ? "var(--danger)" : "var(--text-primary)"
                                                }}>
                                                    {p.stock} units
                                                </span>
                                                <div className="stock-bar">
                                                    <div
                                                        className="stock-fill"
                                                        style={{
                                                            width: `${pct}%`,
                                                            background: isLow ? "var(--danger)" : "var(--success)",
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        </td>
                                        <td style={{ color: "var(--text-secondary)" }}>{p.threshold} units</td>
                                        <td style={{ fontWeight: 500 }}>₹{p.price ? p.price.toFixed(2) : "0.00"}</td>
                                        <td>
                                            <span className={`badge ${isLow ? "badge-danger" : "badge-success"}`}>
                                                <span className={`status-dot ${isLow ? "danger" : "online"}`} />
                                                {isLow ? "Low Stock" : "Optimal"}
                                            </span>
                                        </td>
                                        <td style={{ textAlign: "right" }}>
                                            <div style={{ display: "inline-flex", gap: 6 }}>
                                                <button
                                                    className="btn btn-outline btn-sm"
                                                    onClick={() => onEdit(p)}
                                                    title="Edit Product"
                                                >
                                                    <Edit2 size={13} />
                                                    <span>Edit</span>
                                                </button>
                                                <button
                                                    className="btn btn-outline-danger btn-sm"
                                                    onClick={() => onDelete(p.id)}
                                                    title="Delete Product"
                                                >
                                                    <Trash2 size={13} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>
            <div style={{ marginTop: 12, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Showing {filtered.length} of {products.length} registered products
            </div>
        </div>
    );
}

export default StockTable;
