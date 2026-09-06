import React, { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { Camera, Plus, Trash2, MapPin, X, Video } from "lucide-react";

function Cameras() {
    const { isAdmin } = useAuth();
    const [cameras, setCameras] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [newCam, setNewCam] = useState({
        name: "",
        location: "Aisle 1",
        source: "0",
        camera_type: "webcam",
        status: "ACTIVE"
    });

    const fetchCameras = async () => {
        try {
            setLoading(true);
            const res = await api.get("/cameras");
            setCameras(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCameras();
    }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            const res = await api.post("/cameras", newCam);
            setCameras([...cameras, res.data]);
            setShowModal(false);
            setNewCam({ name: "", location: "Aisle 1", source: "0", camera_type: "webcam", status: "ACTIVE" });
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to create camera");
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to remove this camera stream?")) return;
        try {
            await api.delete(`/cameras/${id}`);
            setCameras(cameras.filter(c => c.id !== id));
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to delete camera");
        }
    };

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>Camera Stream Management</h1>
                    <p>Configure hardware video inputs, RTSP streams, laptop webcams, and test video feeds</p>
                </div>
                {isAdmin && (
                    <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
                        <Plus size={15} />
                        <span>Add Camera</span>
                    </button>
                )}
            </div>

            {/* Cameras Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 20 }}>
                {loading ? (
                    <p style={{ color: "var(--text-muted)", gridColumn: "1 / -1" }}>Loading camera streams...</p>
                ) : cameras.length === 0 ? (
                    <div className="card empty-state" style={{ gridColumn: "1 / -1" }}>
                        <Camera size={36} />
                        <h3>No cameras configured</h3>
                        <p>Register a webcam or network video stream to initiate automated computer vision tracking.</p>
                    </div>
                ) : (
                    cameras.map((c) => {
                        const isActive = c.status === "ACTIVE";
                        return (
                            <div
                                key={c.id}
                                className="card"
                                style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    justifyContent: "space-between",
                                    gap: 16
                                }}
                            >
                                <div>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                            <div style={{
                                                width: 40,
                                                height: 40,
                                                borderRadius: "var(--radius-md)",
                                                background: "var(--primary-subtle)",
                                                color: "var(--primary)",
                                                border: "1px solid var(--primary-border)",
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "center",
                                                flexShrink: 0
                                            }}>
                                                <Video size={20} />
                                            </div>
                                            <div>
                                                <div style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--text-primary)" }}>
                                                    {c.name}
                                                </div>
                                                <div style={{
                                                    fontSize: "0.75rem",
                                                    color: "var(--text-secondary)",
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: 4,
                                                    marginTop: 2
                                                }}>
                                                    <MapPin size={12} style={{ color: "var(--text-muted)" }} />
                                                    <span>{c.location || "Unassigned"}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <span className={`badge ${isActive ? "badge-success" : "badge-gray"}`}>
                                            <span className={`status-dot ${isActive ? "online" : "offline"}`} />
                                            {isActive ? "Online" : "Offline"}
                                        </span>
                                    </div>

                                    <div style={{
                                        background: "var(--surface-subtle)",
                                        border: "1px solid var(--border-subtle)",
                                        borderRadius: "var(--radius-md)",
                                        padding: "10px 14px",
                                        fontSize: "0.8125rem",
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: 6
                                    }}>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--text-secondary)" }}>Stream Type:</span>
                                            <strong style={{ textTransform: "uppercase", color: "var(--text-primary)", fontSize: "0.75rem" }}>
                                                {c.camera_type}
                                            </strong>
                                        </div>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--text-secondary)" }}>Device/URL:</span>
                                            <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontSize: "0.75rem" }}>
                                                {c.source}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    borderTop: "1px solid var(--border-subtle)",
                                    paddingTop: 12
                                }}>
                                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                        Channel ID: #{c.id}
                                    </span>
                                    {isAdmin && (
                                        <button
                                            className="btn btn-outline-danger btn-sm"
                                            onClick={() => handleDelete(c.id)}
                                            title="Remove Stream"
                                        >
                                            <Trash2 size={13} />
                                            <span>Delete</span>
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Create Camera Modal */}
            {showModal && (
                <div className="modal-backdrop">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h2 className="modal-title">Add Video Input Stream</h2>
                            <button
                                onClick={() => setShowModal(false)}
                                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
                            >
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleCreate}>
                            <div className="modal-body">
                                <div className="form-group">
                                    <label className="form-label">Camera Identifier</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="e.g. Overhead Shelf Camera A"
                                        value={newCam.name}
                                        onChange={(e) => setNewCam({ ...newCam, name: e.target.value })}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Location / Aisle</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="e.g. Aisle 2 - Beverages"
                                        value={newCam.location}
                                        onChange={(e) => setNewCam({ ...newCam, location: e.target.value })}
                                    />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Stream Protocol</label>
                                    <select
                                        className="form-select"
                                        value={newCam.camera_type}
                                        onChange={(e) => setNewCam({ ...newCam, camera_type: e.target.value })}
                                    >
                                        <option value="webcam">Integrated / USB Webcam</option>
                                        <option value="rtsp">CCTV RTSP Network Stream</option>
                                        <option value="file">Local Video File (MP4/WebM)</option>
                                        <option value="demo">Demo Simulation Feed</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Device Index / Stream URL</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="0 for default webcam, or rtsp://192.168.1.10:554/live"
                                        value={newCam.source}
                                        onChange={(e) => setNewCam({ ...newCam, source: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn btn-primary">
                                    Register Camera
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Cameras;
