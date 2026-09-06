import React, { useState, useEffect } from "react";
import api from "../api";
import { Cpu, Zap, Activity, Sliders, Play, Pause, RefreshCw, Check, AlertCircle, Save, Layers } from "lucide-react";

function AIModelStatus() {
    const [status, setStatus] = useState(null);
    const [thresholds, setThresholds] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState("");

    const fetchStatus = async () => {
        try {
            const [statusRes, threshRes] = await Promise.all([
                api.get("/detection/status"),
                api.get("/settings/thresholds")
            ]);
            setStatus(statusRes.data);
            setThresholds(threshRes.data);
        } catch (err) {
            console.error("Status fetch error:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    const togglePipeline = async () => {
        if (!status) return;
        try {
            if (status.detection_status === "RUNNING") {
                await api.post("/detection/stop");
            } else {
                await api.post("/detection/start");
            }
            fetchStatus();
        } catch (err) {
            console.error(err);
        }
    };

    const handleSaveThresholds = async (e) => {
        e.preventDefault();
        setSaving(true);
        setMsg("");
        try {
            await api.put("/settings/thresholds", thresholds);
            setMsg("Threshold parameters successfully applied to AI pipeline.");
            setTimeout(() => setMsg(""), 3500);
        } catch (err) {
            setMsg("Error saving thresholds: " + (err.response?.data?.detail || err.message));
        } finally {
            setSaving(false);
        }
    };

    if (loading && !status) {
        return (
            <div className="page-content" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
                <p style={{ color: "var(--text-muted)" }}>Connecting to Computer Vision diagnostics...</p>
            </div>
        );
    }

    const isRunning = status?.detection_status === "RUNNING";

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>AI &amp; Computer Vision Diagnostics</h1>
                    <p>Real-time neural telemetry, inference latency, ByteTrack tracking engine, and threshold configuration</p>
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <button
                        className={`btn btn-sm ${isRunning ? "btn-outline-danger" : "btn-primary"}`}
                        onClick={togglePipeline}
                    >
                        {isRunning ? (
                            <>
                                <Pause size={14} />
                                <span>Pause Pipeline</span>
                            </>
                        ) : (
                            <>
                                <Play size={14} />
                                <span>Start Pipeline</span>
                            </>
                        )}
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={fetchStatus} title="Refresh Telemetry">
                        <RefreshCw size={14} />
                    </button>
                </div>
            </div>

            {/* AI HUD Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>MODEL ARCHITECTURE</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--primary-subtle)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <Cpu size={15} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {status?.model_name || "YOLOv8/11"}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        {status?.classes_count || 80} COCO &amp; custom classes
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>ACCELERATION DEVICE</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: status?.device === "CUDA" ? "var(--success-subtle)" : "var(--warning-subtle)", color: status?.device === "CUDA" ? "var(--success)" : "var(--warning)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <Zap size={15} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {status?.device || "CPU"}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        {status?.device === "CUDA" ? "Hardware GPU accelerated" : "Optimized CPU execution"}
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>INFERENCE SPEED</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--primary-subtle)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <Activity size={15} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {status?.inference_time_ms || 0} ms
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        Frame rate: <strong>{status?.fps || 0} FPS</strong>
                    </div>
                </div>

                <div className="card" style={{ padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600 }}>
                        <span>ACTIVE TRACKS</span>
                        <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--surface-subtle)", color: "var(--text-secondary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <Layers size={15} />
                        </div>
                    </div>
                    <div style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: 8, color: "var(--text-primary)" }}>
                        {status?.tracked_objects || 0}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        ByteTrack persistent Kalman tracks
                    </div>
                </div>
            </div>

            {/* Threshold & Behavior Parameter Tuning */}
            <div className="card">
                <div className="card-header">
                    <div className="card-title" style={{ margin: 0 }}>
                        <Sliders size={16} />
                        <span>Centralized Confidence &amp; Threshold Management</span>
                    </div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        Runtime hyperparameter tuning
                    </span>
                </div>
                <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 20 }}>
                    Adjust real-time neural confidence thresholds, frame confirmation temporal windows, and loss-prevention score triggers without restarting the backend service.
                </p>

                {msg && (
                    <div style={{
                        padding: "10px 14px",
                        borderRadius: "var(--radius-md)",
                        marginBottom: 16,
                        fontSize: "0.8125rem",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        background: msg.startsWith("Error") ? "var(--danger-subtle)" : "var(--success-subtle)",
                        border: `1px solid ${msg.startsWith("Error") ? "var(--danger-border)" : "var(--success-border)"}`,
                        color: msg.startsWith("Error") ? "var(--danger)" : "var(--success)"
                    }}>
                        {msg.startsWith("Error") ? <AlertCircle size={15} /> : <Check size={15} />}
                        <span>{msg}</span>
                    </div>
                )}

                <form onSubmit={handleSaveThresholds}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
                        {/* Detection Confidence */}
                        <div style={{ background: "var(--surface-subtle)", padding: 16, borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                                <label style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                                    Detection Confidence Threshold
                                </label>
                                <span style={{ color: "var(--primary)", fontWeight: 700, fontSize: "0.875rem" }}>
                                    {Math.round((thresholds.detection_confidence || 0.4) * 100)}%
                                </span>
                            </div>
                            <input
                                type="range" min="0.1" max="0.95" step="0.05"
                                value={thresholds.detection_confidence || 0.4}
                                onChange={(e) => setThresholds({ ...thresholds, detection_confidence: parseFloat(e.target.value) })}
                            />
                            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 8 }}>
                                Minimum YOLO prediction confidence to accept bounding box.
                            </div>
                        </div>

                        {/* IoU Threshold */}
                        <div style={{ background: "var(--surface-subtle)", padding: 16, borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                                <label style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                                    Tracker IoU Overlap Threshold
                                </label>
                                <span style={{ color: "var(--primary)", fontWeight: 700, fontSize: "0.875rem" }}>
                                    {Math.round((thresholds.iou_threshold || 0.45) * 100)}%
                                </span>
                            </div>
                            <input
                                type="range" min="0.1" max="0.9" step="0.05"
                                value={thresholds.iou_threshold || 0.45}
                                onChange={(e) => setThresholds({ ...thresholds, iou_threshold: parseFloat(e.target.value) })}
                            />
                            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 8 }}>
                                Minimum Intersection-over-Union to maintain persistent object identity.
                            </div>
                        </div>

                        {/* Removal Confirmation Frames */}
                        <div style={{ background: "var(--surface-subtle)", padding: 16, borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                                <label style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                                    Removal Confirmation Stability
                                </label>
                                <span style={{ color: "var(--warning)", fontWeight: 700, fontSize: "0.875rem" }}>
                                    {thresholds.removal_confirmation_frames || 10} frames
                                </span>
                            </div>
                            <input
                                type="range" min="3" max="30" step="1"
                                value={thresholds.removal_confirmation_frames || 10}
                                onChange={(e) => setThresholds({ ...thresholds, removal_confirmation_frames: parseInt(e.target.value) })}
                            />
                            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 8 }}>
                                Consecutive frames an item must remain outside the shelf before logging removal.
                            </div>
                        </div>

                        {/* Suspicious Score Threshold */}
                        <div style={{ background: "var(--surface-subtle)", padding: 16, borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                                <label style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                                    Loss Prevention Suspicious Score
                                </label>
                                <span style={{ color: "var(--danger)", fontWeight: 700, fontSize: "0.875rem" }}>
                                    &ge; {thresholds.suspicious_score_threshold || 70} / 100
                                </span>
                            </div>
                            <input
                                type="range" min="40" max="95" step="5"
                                value={thresholds.suspicious_score_threshold || 70}
                                onChange={(e) => setThresholds({ ...thresholds, suspicious_score_threshold: parseInt(e.target.value) })}
                            />
                            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 8 }}>
                                Multi-signal behavioral threshold (proximity + reaching + rapid zone exit).
                            </div>
                        </div>
                    </div>

                    <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
                        <Save size={14} />
                        <span>{saving ? "Applying..." : "Save Threshold Configuration"}</span>
                    </button>
                </form>
            </div>
        </div>
    );
}

export default AIModelStatus;
