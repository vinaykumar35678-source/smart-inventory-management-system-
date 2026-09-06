import React, { useState, useEffect } from "react";
import api from "../api";
import {
    ClipboardList,
    Search,
    Filter,
    AlertTriangle,
    ShieldAlert,
    ArrowDownRight,
    ArrowUpRight,
    RefreshCw,
    Loader2
} from "lucide-react";

function Events() {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [typeFilter, setTypeFilter] = useState("ALL");

    const fetchEvents = async () => {
        try {
            setLoading(true);
            const res = await api.get("/events?limit=100");
            setEvents(res.data);
        } catch (err) {
            console.error("Failed to fetch events:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    const filtered = events.filter((e) => {
        const matchesSearch = e.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (e.event_id && e.event_id.toLowerCase().includes(searchTerm.toLowerCase()));
        const matchesType = typeFilter === "ALL" || e.event_type === typeFilter;
        return matchesSearch && matchesType;
    });

    const getEventBadge = (type) => {
        switch (type) {
            case "PRODUCT_REMOVED":
                return <span className="badge badge-danger"><ArrowDownRight size={12} /> Removal</span>;
            case "PRODUCT_PLACED":
            case "RESTOCKING_DETECTED":
                return <span className="badge badge-success"><ArrowUpRight size={12} /> Restocked</span>;
            case "PRODUCT_MISPLACED":
                return <span className="badge badge-warning"><AlertTriangle size={12} /> Misplaced</span>;
            case "SUSPICIOUS_REMOVAL":
                return <span className="badge badge-danger"><ShieldAlert size={12} /> Suspicious</span>;
            default:
                return <span className="badge badge-info">{type}</span>;
        }
    };

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>Computer Vision Event Audit Log</h1>
                    <p>Verified immutable audit trail of shelf interactions, item pickups, restocking, and loss prevention</p>
                </div>
                <button className="btn btn-secondary btn-sm" onClick={fetchEvents}>
                    <RefreshCw size={14} />
                    <span>Refresh Feed</span>
                </button>
            </div>

            {/* Filter Bar */}
            <div style={{ display: "flex", gap: 12, marginBottom: 18, alignItems: "center", flexWrap: "wrap", justifyContent: "space-between" }}>
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
                        placeholder="Search product name or event ID..."
                        style={{ paddingLeft: 32 }}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Filter size={15} style={{ color: "var(--text-secondary)" }} />
                    <select
                        className="form-select"
                        style={{ width: 200 }}
                        value={typeFilter}
                        onChange={(e) => setTypeFilter(e.target.value)}
                    >
                        <option value="ALL">All Event Types</option>
                        <option value="PRODUCT_REMOVED">Item Removals</option>
                        <option value="PRODUCT_PLACED">Placements / Restock</option>
                        <option value="PRODUCT_MISPLACED">Misplaced Items</option>
                        <option value="SUSPICIOUS_REMOVAL">Suspicious Removals</option>
                    </select>
                </div>
            </div>

            {/* Table Container */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 48, textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                        <Loader2 className="animate-spin" size={28} style={{ color: "var(--primary)" }} />
                        <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Loading event audit records...</span>
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state" style={{ padding: 48 }}>
                        <ClipboardList size={36} />
                        <h3>No events matching filter</h3>
                        <p>No shelf events found matching your current search parameters.</p>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Event Type</th>
                                <th>Product</th>
                                <th>Track ID</th>
                                <th>Quantity</th>
                                <th>Confidence</th>
                                <th>Status</th>
                                <th style={{ textAlign: "right" }}>Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((e) => (
                                <tr key={e.id}>
                                    <td>
                                        {getEventBadge(e.event_type)}
                                    </td>
                                    <td style={{ fontWeight: 600 }}>
                                        {e.product_name}
                                    </td>
                                    <td>
                                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                                            {e.tracking_id ? `#${e.tracking_id}` : "—"}
                                        </span>
                                    </td>
                                    <td>
                                        <span style={{
                                            fontWeight: 600,
                                            color: (e.quantity_removed || 1) > 0 ? "var(--danger)" : "var(--success)"
                                        }}>
                                            {(e.quantity_removed || 1) > 0 ? `-${Math.abs(e.quantity_removed || 1)}` : `+${Math.abs(e.quantity_removed || 1)}`}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="badge badge-info">
                                            {((e.confidence || 0.9) * 100).toFixed(0)}%
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`badge ${e.status === "SUSPICIOUS" ? "badge-danger" : e.status === "FLAGGED" ? "badge-warning" : "badge-success"}`}>
                                            {e.status || "VERIFIED"}
                                        </span>
                                    </td>
                                    <td style={{ textAlign: "right", color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                                        {e.timestamp ? new Date(e.timestamp.endsWith("Z") ? e.timestamp : `${e.timestamp}Z`).toLocaleString("en-US", {
                                            month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit"
                                        }) : "—"}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
            <div style={{ marginTop: 12, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Showing {filtered.length} of {events.length} audit entries
            </div>
        </div>
    );
}

export default Events;
