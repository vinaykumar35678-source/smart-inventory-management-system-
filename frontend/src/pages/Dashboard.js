import React, { useEffect, useState, useCallback, useRef } from "react";
import api from "../api";
import { Link } from "react-router-dom";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import StatCard from "../components/StatCard";
import {
  Package,
  AlertTriangle,
  Activity,
  Bell,
  Video,
  Play,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Info,
  XCircle,
  Loader2,
  ListFilter,
  Mail,
  RefreshCw
} from "lucide-react";

// ── Toast notification component ──────────────────────────
function Toast({ toasts, remove }) {
  return (
    <div id="toast-container" style={{
      position: "fixed", bottom: 24, right: 24, zIndex: 9999,
      display: "flex", flexDirection: "column-reverse", gap: 10, pointerEvents: "none"
    }}>
      {toasts.map((t) => {
        const borderColors = {
          success: 'var(--success-border)',
          danger: 'var(--danger-border)',
          warning: 'var(--warning-border)',
          info: 'var(--primary-border)'
        };
        const bgColors = {
          success: 'var(--success-subtle)',
          danger: 'var(--danger-subtle)',
          warning: 'var(--warning-subtle)',
          info: 'var(--primary-subtle)'
        };
        const textColors = {
          success: '#15803D',
          danger: '#B91C1C',
          warning: '#B45309',
          info: '#1D4ED8'
        };

        const Icon = t.icon;

        return (
          <div key={t.id} style={{
            background: bgColors[t.type] || '#FFFFFF',
            border: `1px solid ${borderColors[t.type] || 'var(--border-color)'}`,
            color: textColors[t.type] || 'var(--text-primary)',
            padding: "12px 16px",
            borderRadius: "var(--radius-md)",
            fontSize: "0.875rem",
            fontWeight: 500,
            maxWidth: 360,
            boxShadow: "var(--shadow-md)",
            pointerEvents: "all",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 10
          }} onClick={() => remove(t.id)}>
            {Icon && <Icon size={18} style={{ flexShrink: 0 }} />}
            <span>{t.body}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────
function Dashboard() {
  const [products, setProducts] = useState([]);
  const [events, setEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState([]);
  const [simulating, setSimulating] = useState(false);
  const [notificationLogs, setNotificationLogs] = useState([]);
  const wsRef = useRef(null);

  // ── Toast helpers ──────────────────────────────────────
  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, ...toast }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const fetchNotificationLogs = useCallback(async () => {
    try {
      const res = await api.get("/notifications/history?limit=10");
      setNotificationLogs(res.data);
    } catch (err) {
      console.error("Fetch notifications error:", err);
    }
  }, []);

  // ── API fetch ──────────────────────────────────────────
  const fetchAll = useCallback(async (quiet = false) => {
    try {
      const [pRes, eRes, aRes, sRes, nRes] = await Promise.all([
        api.get("/products"),
        api.get("/events?limit=20"),
        api.get("/alerts"),
        api.get("/stats"),
        api.get("/notifications/history?limit=10").catch(() => ({ data: [] })),
      ]);
      setProducts(pRes.data);
      setEvents(eRes.data);
      setAlerts(aRes.data);
      setStats(sRes.data);
      setNotificationLogs(nRes.data || []);

      if (!quiet) {
        pRes.data.filter((p) => p.stock < 5 && p.stock > 0).forEach((p) => {
          addToast({ type: "warning", icon: AlertTriangle, body: `Low Stock: ${p.name} (${p.stock} remaining)` });
        });
        pRes.data.filter((p) => p.stock <= 0).forEach((p) => {
          addToast({ type: "danger", icon: AlertCircle, body: `Out of Stock: ${p.name}` });
        });
      }
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  // ── WebSocket — instant updates ────────────────────────
  useEffect(() => {
    const host = window.location.hostname || "localhost";
    const WS_URL = `ws://${host}:8000/ws`;
    let ws;
    let retryTimer;

    const connect = () => {
      ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);

          if (msg.type === "removal" || msg.type === "addition") {
            const isAddition = msg.type === "addition";
            // Instantly update product stock
            setProducts((prev) =>
              prev.map((p) =>
                p.name === msg.product
                  ? { ...p, stock: msg.stock ?? Math.max(0, p.stock + (isAddition ? 1 : -1)) }
                  : p
              )
            );
            // Refresh stats and events
            api.get("/events?limit=20").then((r) => setEvents(r.data)).catch(() => { });
            api.get("/stats").then((r) => setStats(r.data)).catch(() => { });

            if (isAddition) {
              addToast({ type: "success", icon: CheckCircle2, body: `${msg.product} restocked: ${msg.stock ?? "?"} units` });
            } else {
              addToast({ type: "info", icon: Info, body: `${msg.product} removed: ${msg.stock ?? "?"} remaining` });
            }
          }

          if (msg.type === "alert") {
            api.get("/alerts").then((r) => setAlerts(r.data)).catch(() => { });
            addToast({ type: "warning", icon: AlertTriangle, body: msg.message || `Low stock alert for ${msg.product}` });
          }

          if (msg.type === "person") {
            addToast({ type: "info", icon: Info, body: msg.message });
          }
        } catch (_) { }
      };

      ws.onclose = () => { retryTimer = setTimeout(connect, 4000); };
      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      clearTimeout(retryTimer);
      if (wsRef.current) wsRef.current.close();
    };
  }, [addToast]);

  // ── Initial load + polling ─────────────────────────────
  useEffect(() => {
    fetchAll(true);
    const interval = setInterval(() => fetchAll(true), 15000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  // ── Handlers ───────────────────────────────────────────
  const runSimulation = async () => {
    setSimulating(true);
    try {
      const resp = await api.post('/detect/simulate');
      const data = resp.data;
      if (data.detected && data.detected.length > 0) {
        addToast({ type: 'success', icon: CheckCircle2, body: `Simulation: ${data.detected.length} event(s) processed` });
        fetchAll(true);
      } else {
        addToast({ type: 'info', icon: Info, body: 'Simulation completed: shelf state unchanged.' });
      }
    } catch (err) {
      addToast({ type: 'danger', icon: XCircle, body: `Simulation failed: ${err.message}` });
    } finally {
      setSimulating(false);
    }
  };

  // ── Derived Data ───────────────────────────────────────
  const lowStockProducts = products.filter((p) => p.stock < p.threshold);
  
  const catData = products.reduce((acc, p) => {
    const cat = p.category || "General";
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {});
  const catChartData = Object.keys(catData).map((cat) => ({ name: cat, value: catData[cat] }));
  const COLORS = ['#2563EB', '#0284C7', '#16A34A', '#D97706', '#7C3AED', '#DC2626', '#0D9488', '#4F46E5'];

  const formatTime = (ts) => {
    if (!ts) return "";
    const date = ts.endsWith("Z") ? new Date(ts) : new Date(`${ts}Z`);
    return date.toLocaleTimeString("en-US", { hour12: false });
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh", flexDirection: "column", gap: 14 }}>
        <Loader2 className="animate-spin" size={32} style={{ color: "var(--primary)" }} />
        <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="page-content">
      <Toast toasts={toasts} remove={removeToast} />

      {/* Header & Quick Actions */}
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Real-time inventory overview and automated vision metrics</p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={runSimulation}
            disabled={simulating}
          >
            {simulating ? <Loader2 className="animate-spin" size={14} /> : <Play size={14} />}
            <span>{simulating ? "Simulating..." : "Simulate Event"}</span>
          </button>
          <Link to="/live" className="btn btn-primary btn-sm">
            <Video size={14} />
            <span>Live Monitor</span>
          </Link>
          <Link to="/inventory" className="btn btn-secondary btn-sm">
            <Package size={14} />
            <span>Manage Inventory</span>
          </Link>
        </div>
      </div>

      {/* STAT CARDS */}
      <div className="stats-grid">
        <StatCard
          icon={<Package size={20} />}
          label="Total Products"
          value={stats.total_products || 0}
          color="blue"
          subtext="Catalog items"
        />
        <StatCard
          icon={<AlertTriangle size={20} />}
          label="Low Stock Items"
          value={stats.low_stock_count || 0}
          color="red"
          subtext="Under threshold"
        />
        <StatCard
          icon={<Activity size={20} />}
          label="Total Detections"
          value={stats.total_events_today || 0}
          color="green"
          subtext="Processed today"
        />
        <StatCard
          icon={<Bell size={20} />}
          label="Unresolved Alerts"
          value={stats.unresolved_alerts || 0}
          color="yellow"
          subtext="Action required"
        />
      </div>

      {/* ROW 1: Activity Feed + Category Distribution */}
      <div className="charts-grid">
        
        {/* Live Activity Feed */}
        <div className="card">
          <div className="card-header">
            <div className="card-title" style={{ margin: 0 }}>
              <ListFilter size={15} />
              <span>Real-Time Activity Feed</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="status-dot online" />
              <span style={{ fontSize: "0.75rem", fontWeight: 500, color: "var(--success)" }}>Live Stream</span>
            </div>
          </div>
          
          <div id="activity-feed">
            {events.length === 0 ? (
              <div className="empty-state" style={{ padding: "32px 16px" }}>
                <Activity size={28} />
                <p>No detections recorded yet. Run a simulation or trigger camera activity.</p>
              </div>
            ) : (
              events.slice(0, 20).map((ev) => (
                <div key={ev.id} className="feed-item">
                  <div className="feed-icon">
                    <Package size={16} />
                  </div>
                  <div className="feed-text">
                    <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                      {ev.product_name}
                      <span style={{ fontWeight: 400, color: "var(--text-secondary)", marginLeft: 6 }}>
                        — {ev.quantity_removed} item{ev.quantity_removed !== 1 ? "s" : ""} removed
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                      <span className="badge badge-gray" style={{ fontSize: "0.6875rem" }}>
                        Confidence: {(ev.confidence * 100).toFixed(0)}%
                      </span>
                      <span className="feed-time">{formatTime(ev.timestamp)}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Category Chart */}
        <div className="card">
          <div className="card-header">
            <div className="card-title" style={{ margin: 0 }}>
              <Package size={15} />
              <span>Products by Category</span>
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {products.length} registered
            </span>
          </div>

          <div style={{ width: "100%", height: 250 }}>
            {catChartData.length === 0 ? (
              <div className="empty-state" style={{ height: "100%", padding: 0 }}>
                <Package size={28} />
                <p>No product categories available.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={catChartData}
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="value"
                    stroke="#FFFFFF"
                    strokeWidth={2}
                  >
                    {catChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#FFFFFF",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      boxShadow: "var(--shadow-md)",
                      fontSize: "0.8125rem",
                      color: "var(--text-primary)"
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div style={{ display: "flex", justifyContent: "center", gap: 14, flexWrap: "wrap", marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border-subtle)" }}>
            {catChartData.map((entry, index) => (
              <div key={entry.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS[index % COLORS.length] }} />
                <span>{entry.name} ({entry.value})</span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* ROW 2: Low Stock + Recent Alerts */}
      <div className="charts-grid">
        
        {/* Low Stock Products */}
        <div className="card">
          <div className="card-header">
            <div className="card-title" style={{ margin: 0 }}>
              <AlertTriangle size={15} style={{ color: "var(--warning)" }} />
              <span>Low Stock Watchlist</span>
            </div>
            {lowStockProducts.length > 0 && (
              <span className="badge badge-warning">
                {lowStockProducts.length} items critical
              </span>
            )}
          </div>

          {lowStockProducts.length > 0 ? (
            <div className="table-container" style={{ border: "none", boxShadow: "none" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Remaining</th>
                    <th>Threshold</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStockProducts.map((p) => {
                    const pct = Math.min((p.stock / Math.max(p.threshold * 2, 1)) * 100, 100);
                    const isZero = p.stock === 0;
                    return (
                      <tr key={p.id}>
                        <td style={{ fontWeight: 600 }}>{p.name}</td>
                        <td>
                          <div style={{ display: "flex", flexDirection: "column", gap: 4, width: 80 }}>
                            <span style={{ fontWeight: 600, color: isZero ? "var(--danger)" : "var(--warning)" }}>
                              {p.stock}
                            </span>
                            <div className="stock-bar">
                              <div
                                className="stock-fill"
                                style={{
                                  width: `${pct}%`,
                                  background: isZero ? "var(--danger)" : "var(--warning)"
                                }}
                              />
                            </div>
                          </div>
                        </td>
                        <td style={{ color: "var(--text-secondary)" }}>{p.threshold}</td>
                        <td>
                          <span className={`badge ${isZero ? "badge-danger" : "badge-warning"}`}>
                            {isZero ? "Out of Stock" : "Low Stock"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "24px 0",
              color: "var(--success)",
              fontSize: "0.875rem"
            }}>
              <CheckCircle2 size={18} />
              <span>All registered inventory items meet minimum stock thresholds.</span>
            </div>
          )}
        </div>

        {/* Recent Alerts */}
        <div className="card">
          <div className="card-header">
            <div className="card-title" style={{ margin: 0 }}>
              <Bell size={15} style={{ color: "var(--primary)" }} />
              <span>Recent Incident Alerts</span>
            </div>
            <Link to="/alerts" className="btn btn-ghost btn-sm" style={{ fontSize: "0.75rem" }}>
              <span>View All</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {alerts.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {alerts.slice(0, 5).map((al) => (
                <div
                  key={al.id}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "var(--radius-md)",
                    background: "var(--surface-subtle)",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "0.8125rem",
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 10
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                    <AlertTriangle size={15} style={{ color: "var(--warning)", marginTop: 2, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                        {al.message}
                      </div>
                      <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginTop: 2 }}>
                        {al.timestamp ? new Date(al.timestamp.endsWith('Z') ? al.timestamp : `${al.timestamp}Z`).toLocaleString() : ''}
                      </div>
                    </div>
                  </div>
                  <span className="badge badge-warning" style={{ fontSize: "0.6875rem" }}>
                    Active
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "24px 0",
              color: "var(--success)",
              fontSize: "0.875rem"
            }}>
              <CheckCircle2 size={18} />
              <span>No pending alerts or anomalies detected.</span>
            </div>
          )}
        </div>

      </div>

      {/* ROW 3: Email Notification History */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <div className="card-title" style={{ margin: 0 }}>
            <Mail size={15} style={{ color: "var(--primary)" }} />
            <span>Email Notification History (Gmail Dispatch Audit)</span>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={fetchNotificationLogs}
            style={{ fontSize: "0.75rem", display: "inline-flex", alignItems: "center", gap: 4 }}
          >
            <RefreshCw size={12} />
            <span>Refresh</span>
          </button>
        </div>

        {notificationLogs.length > 0 ? (
          <div className="table-container" style={{ border: "none", boxShadow: "none" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Product / Scope</th>
                  <th>Alert Type</th>
                  <th>Recipient</th>
                  <th>Status</th>
                  <th>Dispatch Info</th>
                </tr>
              </thead>
              <tbody>
                {notificationLogs.map((log) => {
                  const isSent = log.status === "SENT";
                  const isFailed = log.status === "FAILED";
                  const formattedTime = log.created_at
                    ? new Date(log.created_at.endsWith('Z') ? log.created_at : `${log.created_at}Z`).toLocaleString()
                    : "—";

                  return (
                    <tr key={log.id}>
                      <td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", whiteSpace: "nowrap" }}>
                        {formattedTime}
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {log.product_name || "System"}
                      </td>
                      <td>
                        <span className={`badge ${
                          log.alert_type === "OUT_OF_STOCK"
                            ? "badge-danger"
                            : log.alert_type === "LOW_STOCK"
                            ? "badge-warning"
                            : "badge-info"
                        }`}>
                          {log.alert_type}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                        {log.recipient}
                      </td>
                      <td>
                        <span className={`badge ${
                          isSent ? "badge-success" : isFailed ? "badge-danger" : "badge-info"
                        }`}>
                          {log.status}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                        {isSent ? (log.sent_at ? "Delivered" : "Queued") : (log.error_message || `${log.retry_count} retries`)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "20px 0",
            color: "var(--text-muted)",
            fontSize: "0.875rem"
          }}>
            <Mail size={18} />
            <span>No email notifications recorded yet. Real-time threshold alerts will be audited here.</span>
          </div>
        )}
      </div>

    </div>
  );
}

export default Dashboard;