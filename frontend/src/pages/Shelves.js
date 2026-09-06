import React, { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { Plus, Trash2, Edit3, Layers, Camera, Check, X, Sliders, Box } from "lucide-react";

function Shelves() {
    const { isAdmin } = useAuth();
    const [shelves, setShelves] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedShelf, setSelectedShelf] = useState(null);
    const [editMode, setEditMode] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newShelf, setNewShelf] = useState({
        name: "",
        category: "General",
        capacity: 20,
        roi_x1: 0.1,
        roi_y1: 0.2,
        roi_x2: 0.9,
        roi_y2: 0.8
    });
    const [editForm, setEditForm] = useState({});

    const fetchShelves = async () => {
        try {
            setLoading(true);
            const res = await api.get("/shelves");
            setShelves(res.data);
            if (res.data.length > 0 && !selectedShelf) {
                setSelectedShelf(res.data[0]);
                setEditForm(res.data[0]);
            }
        } catch (err) {
            console.error("Error fetching shelves:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchShelves();
    }, []);

    const handleSelectShelf = (shelf) => {
        setSelectedShelf(shelf);
        setEditForm(shelf);
        setEditMode(false);
    };

    const handleSaveEdit = async (e) => {
        e.preventDefault();
        try {
            const res = await api.put(`/shelves/${selectedShelf.id}`, editForm);
            setShelves(shelves.map(s => s.id === selectedShelf.id ? res.data : s));
            setSelectedShelf(res.data);
            setEditMode(false);
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to update shelf");
        }
    };

    const handleDelete = async (shelfId) => {
        if (!window.confirm("Are you sure you want to delete this shelf zone?")) return;
        try {
            await api.delete(`/shelves/${shelfId}`);
            setShelves(shelves.filter(s => s.id !== shelfId));
            if (selectedShelf?.id === shelfId) {
                setSelectedShelf(null);
            }
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to delete shelf");
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            const res = await api.post("/shelves", newShelf);
            setShelves([...shelves, res.data]);
            setSelectedShelf(res.data);
            setEditForm(res.data);
            setShowCreateModal(false);
            setNewShelf({
                name: "",
                category: "General",
                capacity: 20,
                roi_x1: 0.1,
                roi_y1: 0.2,
                roi_x2: 0.9,
                roi_y2: 0.8
            });
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to create shelf");
        }
    };

    const activeForm = editMode ? editForm : selectedShelf;

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>Virtual Shelves &amp; ROI Zones</h1>
                    <p>Configure calibrated region-of-interest (ROI) bounding boxes, capacity thresholds, and category rules</p>
                </div>
                {isAdmin && (
                    <button className="btn btn-primary btn-sm" onClick={() => setShowCreateModal(true)}>
                        <Plus size={15} />
                        <span>Add Shelf Zone</span>
                    </button>
                )}
            </div>

            {/* 2-Column Layout */}
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 24, alignItems: "start" }}>
                {/* Column 1 (Left): Camera Preview & ROI Visualizer */}
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                    <div className="card">
                        <div className="card-header">
                            <div className="card-title" style={{ margin: 0 }}>
                                <Camera size={15} />
                                <span>ROI Viewport Calibration</span>
                            </div>
                            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                Normalized space (0.00 → 1.00)
                            </span>
                        </div>

                        {/* Interactive ROI Canvas Viewport */}
                        <div style={{
                            width: "100%",
                            height: 380,
                            background: "#0F172A",
                            borderRadius: "var(--radius-md)",
                            position: "relative",
                            overflow: "hidden",
                            border: "1px solid var(--border-strong)",
                            boxShadow: "inset 0 2px 4px rgba(0,0,0,0.2)"
                        }}>
                            {/* Grid Lines for Calibration */}
                            <div style={{
                                position: "absolute",
                                inset: 0,
                                backgroundImage: "linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)",
                                backgroundSize: "20% 20%",
                                pointerEvents: "none"
                            }} />

                            {/* Viewport HUD */}
                            <div style={{
                                position: "absolute",
                                top: 12,
                                left: 12,
                                background: "rgba(15, 23, 42, 0.75)",
                                padding: "4px 10px",
                                borderRadius: "var(--radius-sm)",
                                fontSize: "0.75rem",
                                color: "#94A3B8",
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                                border: "1px solid rgba(255,255,255,0.1)"
                            }}>
                                <span className="status-dot online" />
                                <span>Camera Viewport (Active Zones: {shelves.length})</span>
                            </div>

                            {/* Render All Shelf Boundaries */}
                            {shelves.map((s) => {
                                const isSelected = selectedShelf?.id === s.id;
                                const x1 = (isSelected && editMode ? editForm.roi_x1 : s.roi_x1) * 100;
                                const y1 = (isSelected && editMode ? editForm.roi_y1 : s.roi_y1) * 100;
                                const width = ((isSelected && editMode ? editForm.roi_x2 : s.roi_x2) - (isSelected && editMode ? editForm.roi_x1 : s.roi_x1)) * 100;
                                const height = ((isSelected && editMode ? editForm.roi_y2 : s.roi_y2) - (isSelected && editMode ? editForm.roi_y1 : s.roi_y1)) * 100;

                                return (
                                    <div
                                        key={s.id}
                                        onClick={() => handleSelectShelf(s)}
                                        style={{
                                            position: "absolute",
                                            left: `${Math.max(0, Math.min(100, x1))}%`,
                                            top: `${Math.max(0, Math.min(100, y1))}%`,
                                            width: `${Math.max(5, Math.min(100, width))}%`,
                                            height: `${Math.max(5, Math.min(100, height))}%`,
                                            border: `2px dashed ${isSelected ? "#2563EB" : "rgba(148, 163, 184, 0.5)"}`,
                                            background: isSelected ? "rgba(37, 99, 235, 0.18)" : "rgba(148, 163, 184, 0.08)",
                                            borderRadius: "var(--radius-sm)",
                                            cursor: "pointer",
                                            transition: "all 0.15s ease",
                                            display: "flex",
                                            alignItems: "flex-start",
                                            justifyContent: "flex-start",
                                            padding: 4
                                        }}
                                    >
                                        <span style={{
                                            background: isSelected ? "#2563EB" : "#475569",
                                            color: "#FFFFFF",
                                            fontSize: "0.6875rem",
                                            fontWeight: 600,
                                            padding: "2px 6px",
                                            borderRadius: "var(--radius-xs)",
                                            whiteSpace: "nowrap",
                                            overflow: "hidden",
                                            textOverflow: "ellipsis",
                                            maxWidth: "90%"
                                        }}>
                                            {s.name}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Coordinate Summary Footer */}
                        {activeForm && (
                            <div style={{
                                display: "grid",
                                gridTemplateColumns: "repeat(4, 1fr)",
                                gap: 10,
                                marginTop: 14,
                                padding: "12px 14px",
                                background: "var(--surface-subtle)",
                                borderRadius: "var(--radius-md)",
                                border: "1px solid var(--border-subtle)"
                            }}>
                                <div>
                                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>X1 Min</span>
                                    <div style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "var(--font-mono)" }}>
                                        {activeForm.roi_x1?.toFixed(2) ?? "0.00"}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Y1 Min</span>
                                    <div style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "var(--font-mono)" }}>
                                        {activeForm.roi_y1?.toFixed(2) ?? "0.00"}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>X2 Max</span>
                                    <div style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "var(--font-mono)" }}>
                                        {activeForm.roi_x2?.toFixed(2) ?? "1.00"}
                                    </div>
                                </div>
                                <div>
                                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Y2 Max</span>
                                    <div style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "var(--font-mono)" }}>
                                        {activeForm.roi_y2?.toFixed(2) ?? "1.00"}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Column 2 (Right): Shelf List & Configuration Panel */}
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                    {/* Active Zones List */}
                    <div className="card">
                        <div className="card-header">
                            <div className="card-title" style={{ margin: 0 }}>
                                <Layers size={15} />
                                <span>Configured Zones ({shelves.length})</span>
                            </div>
                        </div>

                        {loading ? (
                            <p style={{ color: "var(--text-muted)", padding: "12px 0" }}>Loading shelf zones...</p>
                        ) : shelves.length === 0 ? (
                            <div className="empty-state" style={{ padding: "24px 0" }}>
                                <Box size={28} />
                                <p>No shelf zones created yet.</p>
                            </div>
                        ) : (
                            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 220, overflowY: "auto" }}>
                                {shelves.map((s) => {
                                    const isSelected = selectedShelf?.id === s.id;
                                    const pct = Math.min(100, Math.round(((s.current_count || 0) / (s.capacity || 1)) * 100));

                                    return (
                                        <div
                                            key={s.id}
                                            onClick={() => handleSelectShelf(s)}
                                            style={{
                                                padding: "10px 14px",
                                                borderRadius: "var(--radius-md)",
                                                background: isSelected ? "var(--primary-subtle)" : "var(--surface-bg)",
                                                border: `1px solid ${isSelected ? "var(--primary-border)" : "var(--border-color)"}`,
                                                cursor: "pointer",
                                                transition: "all 0.15s ease",
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "space-between"
                                            }}
                                        >
                                            <div>
                                                <div style={{ fontWeight: 600, fontSize: "0.875rem", color: isSelected ? "var(--primary)" : "var(--text-primary)" }}>
                                                    {s.name}
                                                </div>
                                                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                                                    Category: {s.category} · Stock: {s.current_count || 0}/{s.capacity} ({pct}%)
                                                </div>
                                            </div>
                                            <span className={`badge ${s.status === "EMPTY" ? "badge-danger" : s.status === "LOW_STOCK" ? "badge-warning" : "badge-success"}`} style={{ fontSize: "0.6875rem" }}>
                                                {s.status || "OPTIMAL"}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Zone Configuration / Edit Panel */}
                    {selectedShelf ? (
                        <div className="card">
                            <div className="card-header">
                                <div>
                                    <div className="card-title" style={{ margin: 0 }}>
                                        <Sliders size={15} />
                                        <span>{editMode ? "Edit Shelf Zone" : "Zone Details"}</span>
                                    </div>
                                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{selectedShelf.name}</span>
                                </div>
                                {isAdmin && !editMode && (
                                    <div style={{ display: "flex", gap: 6 }}>
                                        <button className="btn btn-secondary btn-sm" onClick={() => setEditMode(true)}>
                                            <Edit3 size={13} />
                                            <span>Edit</span>
                                        </button>
                                        <button className="btn btn-outline-danger btn-sm" onClick={() => handleDelete(selectedShelf.id)}>
                                            <Trash2 size={13} />
                                        </button>
                                    </div>
                                )}
                            </div>

                            {editMode ? (
                                <form onSubmit={handleSaveEdit}>
                                    <div className="form-group">
                                        <label className="form-label">Shelf Name</label>
                                        <input
                                            type="text"
                                            className="form-input"
                                            value={editForm.name || ""}
                                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                            required
                                        />
                                    </div>

                                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                        <div className="form-group">
                                            <label className="form-label">Category</label>
                                            <select
                                                className="form-select"
                                                value={editForm.category || "General"}
                                                onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                                            >
                                                <option value="General">General</option>
                                                <option value="Fruits">Fruits</option>
                                                <option value="Vegetables">Vegetables</option>
                                                <option value="Dairy">Dairy</option>
                                                <option value="Bakery">Bakery</option>
                                                <option value="Beverages">Beverages</option>
                                                <option value="Snacks">Snacks</option>
                                            </select>
                                        </div>

                                        <div className="form-group">
                                            <label className="form-label">Max Capacity</label>
                                            <input
                                                type="number"
                                                className="form-input"
                                                value={editForm.capacity || 20}
                                                onChange={(e) => setEditForm({ ...editForm, capacity: parseInt(e.target.value) })}
                                            />
                                        </div>
                                    </div>

                                    <div style={{ marginTop: 8, marginBottom: 16 }}>
                                        <label className="form-label">Normalized ROI Coordinates</label>
                                        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                                            <div>
                                                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>X1</span>
                                                <input
                                                    type="number" step="0.01" min="0" max="1" className="form-input"
                                                    value={editForm.roi_x1 ?? 0}
                                                    onChange={(e) => setEditForm({ ...editForm, roi_x1: parseFloat(e.target.value) })}
                                                />
                                            </div>
                                            <div>
                                                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Y1</span>
                                                <input
                                                    type="number" step="0.01" min="0" max="1" className="form-input"
                                                    value={editForm.roi_y1 ?? 0}
                                                    onChange={(e) => setEditForm({ ...editForm, roi_y1: parseFloat(e.target.value) })}
                                                />
                                            </div>
                                            <div>
                                                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>X2</span>
                                                <input
                                                    type="number" step="0.01" min="0" max="1" className="form-input"
                                                    value={editForm.roi_x2 ?? 1}
                                                    onChange={(e) => setEditForm({ ...editForm, roi_x2: parseFloat(e.target.value) })}
                                                />
                                            </div>
                                            <div>
                                                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Y2</span>
                                                <input
                                                    type="number" step="0.01" min="0" max="1" className="form-input"
                                                    value={editForm.roi_y2 ?? 1}
                                                    onChange={(e) => setEditForm({ ...editForm, roi_y2: parseFloat(e.target.value) })}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditMode(false)}>
                                            <X size={13} />
                                            <span>Cancel</span>
                                        </button>
                                        <button type="submit" className="btn btn-primary btn-sm">
                                            <Check size={13} />
                                            <span>Save Changes</span>
                                        </button>
                                    </div>
                                </form>
                            ) : (
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: "0.8125rem" }}>
                                    <div style={{ background: "var(--surface-subtle)", padding: "10px 12px", borderRadius: "var(--radius-sm)" }}>
                                        <span style={{ color: "var(--text-secondary)" }}>Category</span>
                                        <div style={{ fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>{selectedShelf.category}</div>
                                    </div>
                                    <div style={{ background: "var(--surface-subtle)", padding: "10px 12px", borderRadius: "var(--radius-sm)" }}>
                                        <span style={{ color: "var(--text-secondary)" }}>Capacity</span>
                                        <div style={{ fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>{selectedShelf.capacity} units</div>
                                    </div>
                                    <div style={{ background: "var(--surface-subtle)", padding: "10px 12px", borderRadius: "var(--radius-sm)" }}>
                                        <span style={{ color: "var(--text-secondary)" }}>Current Units</span>
                                        <div style={{ fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>{selectedShelf.current_count || 0} detected</div>
                                    </div>
                                    <div style={{ background: "var(--surface-subtle)", padding: "10px 12px", borderRadius: "var(--radius-sm)" }}>
                                        <span style={{ color: "var(--text-secondary)" }}>Status</span>
                                        <div style={{ marginTop: 2 }}>
                                            <span className={`badge ${selectedShelf.status === "EMPTY" ? "badge-danger" : "badge-success"}`}>
                                                {selectedShelf.status || "NORMAL"}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="card empty-state">
                            <Box size={28} />
                            <p>Select a shelf zone to inspect or configure properties.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Create Shelf Modal */}
            {showCreateModal && (
                <div className="modal-backdrop">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h2 className="modal-title">Create Virtual Shelf Zone</h2>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
                            >
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleCreate}>
                            <div className="modal-body">
                                <div className="form-group">
                                    <label className="form-label">Zone Name</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="e.g. Zone A - Beverages"
                                        value={newShelf.name}
                                        onChange={(e) => setNewShelf({ ...newShelf, name: e.target.value })}
                                        required
                                    />
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                    <div className="form-group">
                                        <label className="form-label">Category</label>
                                        <select
                                            className="form-select"
                                            value={newShelf.category}
                                            onChange={(e) => setNewShelf({ ...newShelf, category: e.target.value })}
                                        >
                                            <option value="General">General</option>
                                            <option value="Fruits">Fruits</option>
                                            <option value="Vegetables">Vegetables</option>
                                            <option value="Dairy">Dairy</option>
                                            <option value="Bakery">Bakery</option>
                                            <option value="Beverages">Beverages</option>
                                            <option value="Snacks">Snacks</option>
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Max Capacity</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={newShelf.capacity}
                                            onChange={(e) => setNewShelf({ ...newShelf, capacity: parseInt(e.target.value) })}
                                        />
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn btn-primary">
                                    Create Zone
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Shelves;
