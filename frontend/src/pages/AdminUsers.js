import React, { useEffect, useState, useCallback } from "react";
import api from "../api";
import {
    Users,
    ShieldCheck,
    UserCheck,
    Plus,
    Trash2,
    Play,
    Pause,
    X,
    CheckCircle2,
    AlertCircle,
    Info,
    Loader2
} from "lucide-react";

function AdminUsers() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ username: "", full_name: "", email: "", password: "", role: "user" });
    const [toast, setToast] = useState(null);
    const [processing, setProcessing] = useState(null);

    const showToast = (msg, type = "success") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    const fetchUsers = useCallback(async () => {
        try {
            const res = await api.get("/users");
            setUsers(res.data);
        } catch (e) {
            showToast("Failed to load users", "error");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchUsers(); }, [fetchUsers]);

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            await api.post("/users", form);
            showToast(`User '${form.username}' created successfully.`);
            setShowModal(false);
            setForm({ username: "", full_name: "", email: "", password: "", role: "user" });
            fetchUsers();
        } catch (err) {
            showToast(err.response?.data?.detail || "Failed to create user", "error");
        }
    };

    const handleToggle = async (user) => {
        setProcessing(user.id);
        try {
            await api.put(`/users/${user.id}/toggle`);
            showToast(`${user.is_active ? "Deactivated" : "Activated"} user '${user.username}'.`);
            fetchUsers();
        } catch (err) {
            showToast(err.response?.data?.detail || "Failed to toggle user", "error");
        } finally {
            setProcessing(null);
        }
    };

    const handleDelete = async (user) => {
        if (!window.confirm(`Delete user '${user.username}'? This cannot be undone.`)) return;
        setProcessing(user.id);
        try {
            await api.delete(`/users/${user.id}`);
            showToast(`User '${user.username}' deleted.`);
            fetchUsers();
        } catch (err) {
            showToast(err.response?.data?.detail || "Failed to delete user", "error");
        } finally {
            setProcessing(null);
        }
    };

    const formatDate = (ts) => ts ? new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";

    return (
        <div className="page-content">
            {/* Toast */}
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
                    <h1>User Management</h1>
                    <p>Manage staff accounts, administrator privileges, and system access</p>
                </div>
                <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
                    <Plus size={15} />
                    <span>Add User</span>
                </button>
            </div>

            {/* Stats Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 24 }}>
                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>TOTAL ACCOUNTS</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--primary-subtle)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <Users size={16} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.75rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {users.length}
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>ADMINISTRATORS</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--primary-subtle)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <ShieldCheck size={16} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.75rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {users.filter(u => u.role === "admin").length}
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>STAFF OPERATORS</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--success-subtle)", color: "var(--success)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <UserCheck size={16} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.75rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {users.filter(u => u.role === "user").length}
                    </div>
                </div>
            </div>

            {/* Table */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 48, textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                        <Loader2 className="animate-spin" size={28} style={{ color: "var(--primary)" }} />
                        <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Loading user directory...</span>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>User</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Account Status</th>
                                <th>Created</th>
                                <th style={{ textAlign: "right" }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((u) => {
                                const initials = (u.full_name?.charAt(0) || u.username?.charAt(0) || "U").toUpperCase();
                                return (
                                    <tr key={u.id}>
                                        <td>
                                            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                                                <div style={{
                                                    width: 34,
                                                    height: 34,
                                                    borderRadius: "var(--radius-full)",
                                                    background: "var(--surface-subtle)",
                                                    border: "1px solid var(--border-color)",
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent: "center",
                                                    fontSize: "0.8125rem",
                                                    fontWeight: 600,
                                                    color: "var(--text-primary)",
                                                    flexShrink: 0
                                                }}>
                                                    {initials}
                                                </div>
                                                <div>
                                                    <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{u.full_name || u.username}</div>
                                                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>@{u.username}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td style={{ color: "var(--text-secondary)" }}>{u.email || "—"}</td>
                                        <td>
                                            <span className={`badge ${u.role === "admin" ? "badge-info" : "badge-gray"}`}>
                                                {u.role === "admin" ? "Administrator" : "Staff"}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${u.is_active ? "badge-success" : "badge-gray"}`}>
                                                <span className={`status-dot ${u.is_active ? "online" : "offline"}`} />
                                                {u.is_active ? "Active" : "Inactive"}
                                            </span>
                                        </td>
                                        <td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                                            {formatDate(u.created_at)}
                                        </td>
                                        <td style={{ textAlign: "right" }}>
                                            <div style={{ display: "inline-flex", gap: 6 }}>
                                                {u.username !== "admin" ? (
                                                    <>
                                                        <button
                                                            className="btn btn-secondary btn-sm"
                                                            onClick={() => handleToggle(u)}
                                                            disabled={processing === u.id}
                                                            title={u.is_active ? "Deactivate" : "Activate"}
                                                        >
                                                            {processing === u.id ? (
                                                                <Loader2 className="animate-spin" size={13} />
                                                            ) : u.is_active ? (
                                                                <>
                                                                    <Pause size={13} />
                                                                    <span>Deactivate</span>
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <Play size={13} />
                                                                    <span>Activate</span>
                                                                </>
                                                            )}
                                                        </button>
                                                        <button
                                                            className="btn btn-outline-danger btn-sm"
                                                            onClick={() => handleDelete(u)}
                                                            disabled={processing === u.id}
                                                            title="Delete User"
                                                        >
                                                            <Trash2 size={13} />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                                                        Root Admin
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Create User Modal */}
            {showModal && (
                <div className="modal-backdrop">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h2 className="modal-title">Create User Account</h2>
                            <button className="btn btn-ghost btn-sm" onClick={() => setShowModal(false)} style={{ padding: 4 }}>
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleCreate}>
                            <div className="modal-body">
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                    <div className="form-group">
                                        <label className="form-label">Username *</label>
                                        <input
                                            className="form-input"
                                            required
                                            value={form.username}
                                            onChange={(e) => setForm(f => ({ ...f, username: e.target.value }))}
                                            placeholder="e.g. jsmith"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Full Name</label>
                                        <input
                                            className="form-input"
                                            value={form.full_name}
                                            onChange={(e) => setForm(f => ({ ...f, full_name: e.target.value }))}
                                            placeholder="e.g. John Smith"
                                        />
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Email Address</label>
                                    <input
                                        className="form-input"
                                        type="email"
                                        value={form.email}
                                        onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))}
                                        placeholder="user@example.com"
                                    />
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                    <div className="form-group">
                                        <label className="form-label">Initial Password *</label>
                                        <input
                                            className="form-input"
                                            type="password"
                                            required
                                            value={form.password}
                                            onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))}
                                            placeholder="Min 6 characters"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Assigned Role</label>
                                        <select
                                            className="form-select"
                                            value={form.role}
                                            onChange={(e) => setForm(f => ({ ...f, role: e.target.value }))}
                                        >
                                            <option value="user">Staff Operator</option>
                                            <option value="admin">Administrator</option>
                                        </select>
                                    </div>
                                </div>

                                <div style={{
                                    background: "var(--surface-subtle)",
                                    border: "1px solid var(--border-subtle)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "10px 12px",
                                    fontSize: "0.75rem",
                                    color: "var(--text-secondary)",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8,
                                    marginTop: 6
                                }}>
                                    <Info size={14} style={{ color: "var(--primary)", flexShrink: 0 }} />
                                    <span>Administrators have full read/write privileges over users, settings, and products. Staff accounts can view live monitoring and inventory.</span>
                                </div>
                            </div>

                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn btn-primary">
                                    Create Account
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default AdminUsers;
