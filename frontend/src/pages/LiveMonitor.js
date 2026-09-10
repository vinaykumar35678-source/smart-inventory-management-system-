import React, { useEffect, useState, useRef, useCallback } from "react";
import api from "../api";
import {
    Camera,
    Upload,
    Sparkles,
    Play,
    Square,
    Zap,
    AlertTriangle,
    ShieldAlert,
    CheckCircle2,
    Package,
    Search,
    Loader2,
    Activity,
    Shuffle,
    ShoppingBag,
    Inbox,
    AlertCircle,
    Cpu,
    Bug
} from "lucide-react";

function LiveMonitor() {
    const [events, setEvents] = useState([]);
    const [connected, setConnected] = useState(false);
    const [debugMode, setDebugMode] = useState(false);
    const [currentDetections, setCurrentDetections] = useState([]);
    const [cameraOn, setCameraOn] = useState(false);
    const [cameraError, setCameraError] = useState("");
    const [scanning, setScanning] = useState(false);
    const [autoScan, setAutoScan] = useState(false);
    const [scanInterval, setScanInterval] = useState(2); // seconds
    const [sourceMode, setSourceMode] = useState("webcam"); // "webcam" | "upload" | "demo"
    const [, setVideoSrc] = useState(null);

    // AI Pipeline Telemetry
    const [aiStats, setAiStats] = useState({
        fps: 0,
        latency_ms: 0,
        device: "CPU",
        model_name: "YOLO11",
        tracked_count: 0,
        pending_events: 0,
        system_status: "NORMAL"
    });

    const [dbStock, setDbStock] = useState(0);

    const wsRef = useRef(null);
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const overlayCanvasRef = useRef(null);
    const streamRef = useRef(null);
    const autoTimerRef = useRef(null);
    const logRef = useRef(null);

    const host = (typeof window !== "undefined" && window.location.hostname) ? window.location.hostname : "localhost";
    const WS_URL = `ws://${host}:8000/ws`;

    // ── Load Database Stock ────────────────────────────────
    const loadProducts = useCallback(async () => {
        try {
            const res = await api.get("/products");
            const total = (res.data || []).reduce((acc, p) => acc + (p.stock || 0), 0);
            setDbStock(total);
        } catch (err) {
            console.error("Error loading products:", err);
        }
    }, []);

    // ── WebSocket & Initialization ────────────────────────
    useEffect(() => {
        let isDisposed = false;
        let retryTimer = null;
        let pingTimer = null;
        let ws = null;

        const connect = () => {
            if (isDisposed) return;
            try {
                ws = new WebSocket(WS_URL);
                wsRef.current = ws;

                ws.onopen = () => {
                    if (isDisposed) {
                        try { ws.close(1000, "Clean unmount"); } catch (_) {}
                        return;
                    }
                    setConnected(true);
                };

                ws.onmessage = (msg) => {
                    if (isDisposed) return;
                    try {
                        const data = JSON.parse(msg.data);
                        if (data.type === "pong") return;
                        setEvents((prev) => {
                            const newEvent = { ...data, id: Date.now() + Math.random() };
                            return [newEvent, ...prev].slice(0, 80);
                        });
                        // Refresh database inventory on verified event
                        if (data.database_inventory !== undefined || data.type === "event") {
                            loadProducts();
                        }
                    } catch (_) { }
                };

                ws.onclose = () => {
                    if (!isDisposed) {
                        setConnected(false);
                        retryTimer = setTimeout(connect, 3000);
                    }
                };

                ws.onerror = () => {
                    // Avoid triggering premature close during connection handshake
                };

                pingTimer = setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send("ping");
                    }
                }, 15000);
            } catch (err) {
                if (!isDisposed) {
                    retryTimer = setTimeout(connect, 3000);
                }
            }
        };

        connect();
        loadProducts();

        return () => {
            isDisposed = true;
            if (retryTimer) clearTimeout(retryTimer);
            if (pingTimer) clearInterval(pingTimer);
            if (ws) {
                ws.onclose = null;
                ws.onerror = null;
                ws.onmessage = null;
                if (ws.readyState === WebSocket.OPEN) {
                    try { ws.close(1000, "Clean unmount"); } catch (_) {}
                } else if (ws.readyState === WebSocket.CONNECTING) {
                    ws.onopen = () => {
                        try { ws.close(1000, "Clean unmount"); } catch (_) {}
                    };
                }
            }
            stopCamera();
        };
    }, [WS_URL, loadProducts]);

    // ── Camera Management ──────────────────────────────────
    const startCamera = async () => {
        setCameraError("");
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "environment" },
                audio: false,
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play();
            }
            setCameraOn(true);
            setVideoSrc(null);
        } catch (err) {
            setCameraError(
                err.name === "NotAllowedError"
                    ? "Camera permission denied in browser."
                    : `Camera error: ${err.message}`
            );
        }
    };

    const stopCamera = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        if (videoRef.current) videoRef.current.srcObject = null;
        setCameraOn(false);
        setAutoScan(false);
        clearInterval(autoTimerRef.current);
    };

    // ── Handle Video Upload ────────────────────────────────
    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            stopCamera();
            const url = URL.createObjectURL(file);
            setVideoSrc(url);
            setCameraOn(true);
            if (videoRef.current) {
                videoRef.current.src = url;
                videoRef.current.play();
            }
        }
    };

    // ── Draw Real-Time Overlays on Canvas ──────────────────
    const renderVisualOverlays = (cvData, frameW, frameH) => {
        const canvas = overlayCanvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const scaleX = canvas.width / (frameW || 640);
        const scaleY = canvas.height / (frameH || 480);

        // 1. Draw Virtual Shelf ROIs
        const shelves = cvData.shelves || {};
        Object.values(shelves).forEach((shelf) => {
            const [x1, y1, x2, y2] = shelf.box.map((v, i) => i % 2 === 0 ? v * scaleX : v * scaleY);
            ctx.strokeStyle = shelf.is_empty ? "#DC2626" : shelf.status === "LOW_STOCK" ? "#D97706" : "#16A34A";
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 6]);
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
            ctx.setLineDash([]);

            // Shelf Tag
            ctx.fillStyle = shelf.is_empty ? "rgba(220,38,38,0.9)" : "rgba(22,163,74,0.9)";
            const tagText = `Shelf: ${shelf.name} (${shelf.detected_count}/${shelf.capacity})`;
            ctx.fillRect(x1, y1 - 22, Math.max(130, (tagText.length * 6.5)), 20);
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 11px Inter, sans-serif";
            ctx.fillText(tagText, x1 + 6, y1 - 8);
        });

        // 2. Draw Tracked Objects (Persons & Products) with State Machine Indicators
        const objects = cvData.tracked_objects || [];
        objects.forEach((obj) => {
            const [x1, y1, x2, y2] = obj.box.map((v, i) => i % 2 === 0 ? v * scaleX : v * scaleY);
            const isPerson = obj.category === "person";
            const state = obj.track_state || "TRACKING";
            const isOccluded = obj.is_occluded || (state === "TEMPORARILY_OCCLUDED");

            // State-specific border colors
            let color = "#2563EB";
            if (isPerson) {
                color = "#0284C7";
            } else if (state === "STABLE_ON_SHELF") {
                color = "#16A34A";
            } else if (state === "INTERACTING") {
                color = "#D97706";
            } else if (state === "POSSIBLE_REMOVAL") {
                color = "#EA580C";
            } else if (state === "REMOVAL_CONFIRMED") {
                color = "#DC2626";
            } else if (state === "POSSIBLE_PLACEMENT") {
                color = "#0284C7";
            } else if (isOccluded) {
                color = "#7C3AED";
            }

            ctx.strokeStyle = color;
            ctx.lineWidth = isOccluded ? 1.5 : (state === "POSSIBLE_REMOVAL" ? 3 : 2);
            if (isOccluded) {
                ctx.setLineDash([5, 5]);
            } else {
                ctx.setLineDash([]);
            }
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
            ctx.setLineDash([]);

            // Label tag with Tracking ID and Confidence
            let labelText = isPerson
                ? `Person #${obj.track_id} (${Math.round(obj.confidence * 100)}%)`
                : `${obj.display_name || obj.label} #${obj.track_id} (${Math.round(obj.confidence * 100)}%)`;

            if (debugMode) {
                labelText = `[CID:${obj.class_id ?? '?'}] ${obj.display_name || obj.label} #${obj.track_id} (${Math.round(obj.confidence * 100)}%)`;
            }

            ctx.fillStyle = color;
            ctx.fillRect(x1, y1 - 20, Math.max(90, labelText.length * 6.5), 18);
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 10px Inter, sans-serif";
            ctx.fillText(labelText, x1 + 5, y1 - 6);

            // Developer Debug coordinates & area ratio tag
            if (debugMode) {
                const bw = Math.round(x2 - x1);
                const bh = Math.round(y2 - y1);
                const relArea = Math.round((bw * bh) / (canvas.width * canvas.height) * 100);
                const coordTag = `[${Math.round(x1)},${Math.round(y1)},${bw}x${bh}] (${relArea}% Area)`;
                ctx.fillStyle = "rgba(15,23,42,0.92)";
                ctx.fillRect(x1, y1 - 36, Math.max(110, coordTag.length * 5.8), 14);
                ctx.fillStyle = "#38BDF8";
                ctx.font = "9px monospace";
                ctx.fillText(coordTag, x1 + 4, y1 - 25);
            }

            // State Machine pill below bounding box for products
            if (!isPerson) {
                let stateTag = state;
                if (state === "POSSIBLE_REMOVAL") stateTag = "EVALUATING REMOVAL";
                else if (state === "STABLE_ON_SHELF") stateTag = "ON SHELF";
                else if (isOccluded) stateTag = "OCCLUDED (HOLDING)";
                else if (state === "INTERACTING") stateTag = "INTERACTING";

                ctx.fillStyle = "rgba(15,23,42,0.85)";
                ctx.fillRect(x1, y2 + 2, Math.max(75, stateTag.length * 6.2), 16);
                ctx.fillStyle = color;
                ctx.font = "bold 9px Inter, sans-serif";
                ctx.fillText(stateTag, x1 + 4, y2 + 13);
            }

            // Draw Trajectory tail
            if (obj.trajectory && obj.trajectory.length > 1) {
                ctx.beginPath();
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.5;
                ctx.globalAlpha = 0.5;
                obj.trajectory.forEach((pt, idx) => {
                    const tx = pt[0] * scaleX;
                    const ty = pt[1] * scaleY;
                    if (idx === 0) ctx.moveTo(tx, ty);
                    else ctx.lineTo(tx, ty);
                });
                ctx.stroke();
                ctx.globalAlpha = 1.0;
            }
        });

        // 3. Draw Pose Reaching Lines & Hand Positions
        const poseResults = cvData.pose_results || [];
        poseResults.forEach((pr) => {
            if (pr.is_reaching && pr.right_wrist) {
                const wx = pr.right_wrist[0] * scaleX;
                const wy = pr.right_wrist[1] * scaleY;
                ctx.beginPath();
                ctx.arc(wx, wy, 6, 0, 2 * Math.PI);
                ctx.fillStyle = "#D97706";
                ctx.fill();
                ctx.strokeStyle = "#FFFFFF";
                ctx.stroke();

                ctx.fillStyle = "#D97706";
                ctx.font = "bold 10px Inter, sans-serif";
                ctx.fillText("Reaching", wx + 10, wy - 4);
            }
        });

        // 4. Highlight Misplaced Items
        const misplaced = cvData.misplaced_items || [];
        misplaced.forEach((mis) => {
            const [x1, y1, x2, y2] = mis.box.map((v, i) => i % 2 === 0 ? v * scaleX : v * scaleY);
            ctx.strokeStyle = "#DC2626";
            ctx.lineWidth = 2.5;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
            ctx.fillStyle = "#DC2626";
            ctx.fillRect(x1, y2, 130, 18);
            ctx.fillStyle = "#FFFFFF";
            ctx.font = "bold 10px Inter, sans-serif";
            ctx.fillText(`MISPLACED: ${mis.product}`, x1 + 4, y2 + 13);
        });
    };

    // ── Capture & Send Frame ───────────────────────────────
    const captureAndAnalyze = useCallback(async () => {
        if (!videoRef.current || !canvasRef.current || !cameraOn) return;
        setScanning(true);
        const video = videoRef.current;
        const canvas = canvasRef.current;
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL("image/jpeg", 0.75);

        try {
            const res = await api.post("/detect/frame", { image: imageData });
            
            // Update HUD Telemetry
            setAiStats({
                fps: res.data.fps || 0,
                latency_ms: res.data.latency_ms || 0,
                device: res.data.device || "CPU",
                model_name: res.data.model_name || "YOLO11",
                tracked_count: res.data.tracked_count ?? res.data.tracked_objects?.length ?? 0,
                pending_events: res.data.pending_events || 0,
                system_status: res.data.system_status || "NORMAL"
            });

            // Draw bounding boxes, shelf ROIs, tracking IDs on overlay canvas
            renderVisualOverlays(res.data, canvas.width, canvas.height);
            setCurrentDetections(res.data.tracked_objects || []);

            // Log new events
            if (res.data.events && res.data.events.length > 0) {
                setEvents((prev) => [...res.data.events, ...prev].slice(0, 80));
            }
        } catch (err) {
            console.error("Frame analysis error:", err);
        } finally {
            setScanning(false);
        }
    }, [cameraOn]);

    // ── Auto Scan Loop ─────────────────────────────────────
    const toggleAutoScan = () => {
        if (autoScan) {
            clearInterval(autoTimerRef.current);
            setAutoScan(false);
        } else {
            setAutoScan(true);
            autoTimerRef.current = setInterval(captureAndAnalyze, scanInterval * 1000);
        }
    };

    useEffect(() => {
        if (autoScan) {
            clearInterval(autoTimerRef.current);
            autoTimerRef.current = setInterval(captureAndAnalyze, scanInterval * 1000);
        }
        return () => clearInterval(autoTimerRef.current);
    }, [scanInterval, autoScan, captureAndAnalyze]);

    // ── Trigger Demo Scenario ─────────────────────────────
    const triggerDemo = async (scenario) => {
        setScanning(true);
        try {
            const res = await api.post(`/demo/scenario/${scenario}`);
            if (res.data.event) {
                setEvents((prev) => [res.data.event, ...prev].slice(0, 80));
            }
        } catch (err) {
            console.error("Demo scenario error:", err);
        } finally {
            setTimeout(() => setScanning(false), 500);
        }
    };

    const clearLog = () => setEvents([]);

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>Live Vision Monitor</h1>
                    <p>Real-time YOLO object detection, ByteTrack tracking, virtual shelf zones, and event telemetry</p>
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <span className="badge badge-info" style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 12px" }}>
                        <Zap size={13} />
                        <span>Device: {aiStats.device} ({aiStats.fps} FPS · {aiStats.latency_ms} ms)</span>
                    </span>
                    <span className={`badge ${connected ? "badge-success" : "badge-gray"}`} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span className={`status-dot ${connected ? "online" : "offline"}`} />
                        <span>{connected ? "WebSocket Connected" : "Offline"}</span>
                    </span>
                </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 20 }}>
                {/* Left Panel: Camera & Video Viewport */}
                <div>
                    <div className="card" style={{ padding: 20, marginBottom: 20 }}>
                        {/* Source Controls */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                            <div style={{ display: "flex", gap: 8 }}>
                                <button
                                    className={`btn btn-sm ${sourceMode === "webcam" ? "btn-primary" : "btn-secondary"}`}
                                    onClick={() => { setSourceMode("webcam"); stopCamera(); }}
                                >
                                    <Camera size={14} />
                                    <span>Webcam</span>
                                </button>
                                <button
                                    className={`btn btn-sm ${sourceMode === "upload" ? "btn-primary" : "btn-secondary"}`}
                                    onClick={() => { setSourceMode("upload"); stopCamera(); }}
                                >
                                    <Upload size={14} />
                                    <span>Upload Video</span>
                                </button>
                                <button
                                    className={`btn btn-sm ${sourceMode === "demo" ? "btn-primary" : "btn-secondary"}`}
                                    onClick={() => setSourceMode("demo")}
                                >
                                    <Sparkles size={14} />
                                    <span>Demo Mode</span>
                                </button>
                            </div>
                        </div>

                        {/* Inventory vs Currently Tracked Telemetry Grid */}
                        <div style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(4, 1fr)",
                            gap: 10,
                            marginBottom: 16
                        }}>
                            <div style={{
                                padding: "10px 14px",
                                border: "1px solid var(--border-color)",
                                borderRadius: "var(--radius-md)",
                                background: "var(--surface-subtle)"
                            }}>
                                <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                                    DB Stock
                                </div>
                                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--primary)", marginTop: 2 }}>
                                    {dbStock} <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "var(--text-muted)" }}>units</span>
                                </div>
                            </div>

                            <div style={{
                                padding: "10px 14px",
                                border: "1px solid var(--border-color)",
                                borderRadius: "var(--radius-md)",
                                background: "var(--surface-subtle)"
                            }}>
                                <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                                    Tracked Now
                                </div>
                                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--success)", marginTop: 2 }}>
                                    {aiStats.tracked_count} <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "var(--text-muted)" }}>items</span>
                                </div>
                            </div>

                            <div style={{
                                padding: "10px 14px",
                                border: "1px solid var(--border-color)",
                                borderRadius: "var(--radius-md)",
                                background: "var(--surface-subtle)"
                            }}>
                                <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                                    Pending Events
                                </div>
                                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: aiStats.pending_events > 0 ? "var(--warning)" : "var(--text-primary)", marginTop: 2 }}>
                                    {aiStats.pending_events}
                                </div>
                            </div>

                            <div style={{
                                padding: "10px 14px",
                                border: "1px solid var(--border-color)",
                                borderRadius: "var(--radius-md)",
                                background: "var(--surface-subtle)"
                            }}>
                                <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                                    Pipeline State
                                </div>
                                <div style={{ fontSize: "0.8125rem", fontWeight: 700, marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                                    <span className={`status-dot ${aiStats.system_status === "POSSIBLE_REMOVAL" ? "warning" : "online"}`} />
                                    <span style={{
                                        color: aiStats.system_status === "POSSIBLE_REMOVAL" ? "var(--warning)" : "var(--success)",
                                        textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap"
                                    }}>
                                        {aiStats.system_status}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Video Frame with Overlaid Visuals */}
                        <div style={{
                            position: "relative",
                            background: "#0F172A",
                            borderRadius: "var(--radius-md)",
                            overflow: "hidden",
                            aspectRatio: "16/9",
                            border: "1px solid var(--border-strong)"
                        }}>
                            <video
                                ref={videoRef}
                                style={{ width: "100%", height: "100%", objectFit: "cover", display: cameraOn ? "block" : "none" }}
                                muted playsInline loop
                            />
                            {/* Hidden capture canvas */}
                            <canvas ref={canvasRef} style={{ display: "none" }} />
                            {/* Visible bounding box overlay canvas */}
                            <canvas
                                ref={overlayCanvasRef}
                                width={640} height={360}
                                style={{
                                    position: "absolute", inset: 0, width: "100%", height: "100%",
                                    pointerEvents: "none", zIndex: 10, display: cameraOn ? "block" : "none"
                                }}
                            />

                            {!cameraOn && (
                                <div style={{
                                    position: "absolute",
                                    inset: 0,
                                    display: "flex",
                                    flexDirection: "column",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    gap: 12,
                                    color: "var(--text-secondary)",
                                    padding: 24,
                                    background: "#F8FAFC"
                                }}>
                                    {sourceMode === "upload" ? (
                                        <>
                                            <Upload size={40} style={{ color: "var(--primary)", opacity: 0.8 }} />
                                            <p style={{ fontSize: "0.875rem", textAlign: "center", maxWidth: 320 }}>
                                                Select an MP4/WebM video file to test CV tracking pipeline
                                            </p>
                                            <input
                                                type="file"
                                                accept="video/mp4,video/webm"
                                                onChange={handleFileUpload}
                                                style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}
                                            />
                                        </>
                                    ) : (
                                        <>
                                            <Camera size={40} style={{ color: "var(--primary)", opacity: 0.8 }} />
                                            <p style={{ fontSize: "0.875rem", textAlign: "center" }}>
                                                Click "Start Camera" to initialize the video optical feed
                                            </p>
                                            {cameraError && (
                                                <div style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: 6,
                                                    color: "var(--danger)",
                                                    fontSize: "0.8125rem"
                                                }}>
                                                    <AlertCircle size={14} />
                                                    <span>{cameraError}</span>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}

                            {/* Telemetry HUD overlay in top-left */}
                            {cameraOn && (
                                <div style={{
                                    position: "absolute", top: 12, left: 12, zIndex: 20,
                                    background: "rgba(15, 23, 42, 0.85)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "4px 10px",
                                    fontSize: "0.75rem",
                                    fontWeight: 500,
                                    color: "#FFFFFF",
                                    border: "1px solid rgba(255, 255, 255, 0.2)",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 6
                                }}>
                                    <span className="status-dot online" />
                                    <span>LIVE | {aiStats.model_name} · {aiStats.fps} FPS · {aiStats.latency_ms}ms · {aiStats.tracked_count} Tracks</span>
                                </div>
                            )}
                        </div>

                        {/* Stream Controls */}
                        <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
                            {!cameraOn && sourceMode === "webcam" ? (
                                <button className="btn btn-primary" style={{ flex: 1 }} onClick={startCamera}>
                                    <Play size={16} />
                                    <span>Start Camera Feed</span>
                                </button>
                            ) : cameraOn ? (
                                <>
                                    <button className="btn btn-primary" onClick={captureAndAnalyze} disabled={scanning} style={{ flex: 1 }}>
                                        {scanning ? <Loader2 className="animate-spin" size={15} /> : <Search size={15} />}
                                        <span>{scanning ? "Analyzing frame..." : "Scan Current Frame"}</span>
                                    </button>
                                    <button
                                        className="btn btn-secondary"
                                        onClick={toggleAutoScan}
                                        style={{
                                            flex: 1,
                                            borderColor: autoScan ? "var(--warning-border)" : "var(--border-color)",
                                            background: autoScan ? "var(--warning-subtle)" : "var(--surface-bg)",
                                            color: autoScan ? "var(--warning)" : "var(--text-primary)"
                                        }}
                                    >
                                        {autoScan ? <Square size={14} /> : <Play size={14} />}
                                        <span>{autoScan ? `Stop Continuous (${scanInterval}s)` : "Continuous Auto Scan"}</span>
                                    </button>
                                    <button
                                        className="btn btn-sm"
                                        onClick={() => setDebugMode(!debugMode)}
                                        style={{
                                            background: debugMode ? "rgba(99, 102, 241, 0.2)" : "var(--surface-bg)",
                                            borderColor: debugMode ? "var(--primary)" : "var(--border-color)",
                                            color: debugMode ? "var(--primary)" : "var(--text-secondary)",
                                            fontWeight: debugMode ? 600 : 500,
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 6
                                        }}
                                    >
                                        <Bug size={14} />
                                        <span>{debugMode ? "Debug: ON" : "Debug: OFF"}</span>
                                    </button>
                                    <button className="btn btn-outline-danger btn-sm" onClick={stopCamera}>
                                        Stop Feed
                                    </button>
                                </>
                            ) : null}
                        </div>

                        {/* Scan Interval Switcher */}
                        {cameraOn && (
                            <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8, fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                                <span>Scan Rate:</span>
                                {[1, 2, 3, 5].map((s) => (
                                    <button
                                        key={s}
                                        onClick={() => setScanInterval(s)}
                                        className="btn btn-sm"
                                        style={{
                                            padding: "2px 10px",
                                            borderRadius: "var(--radius-full)",
                                            background: scanInterval === s ? "var(--primary-subtle)" : "var(--surface-bg)",
                                            color: scanInterval === s ? "var(--primary)" : "var(--text-secondary)",
                                            borderColor: scanInterval === s ? "var(--primary-border)" : "var(--border-color)",
                                            fontWeight: scanInterval === s ? 600 : 500,
                                            fontSize: "0.75rem"
                                        }}
                                    >
                                        {s}s
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Developer Debug Telemetry Panel */}
                    {debugMode && (
                        <div className="card" style={{ marginTop: 16, border: "1px solid var(--primary-border)", background: "rgba(15, 23, 42, 0.6)" }}>
                            <div className="card-header" style={{ paddingBottom: 8 }}>
                                <div className="card-title" style={{ margin: 0, fontSize: "0.875rem", display: "flex", alignItems: "center", gap: 8 }}>
                                    <Cpu size={16} style={{ color: "var(--primary)" }} />
                                    <span>Developer Diagnostic Mode — Active Telemetry</span>
                                </div>
                                <span style={{ fontSize: "0.75rem", padding: "2px 8px", background: "var(--primary-subtle)", color: "var(--primary)", borderRadius: 4, fontWeight: 600 }}>
                                    {aiStats.model_name}
                                </span>
                            </div>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 14 }}>
                                <div style={{ background: "var(--surface-bg)", padding: 8, borderRadius: 6, border: "1px solid var(--border-color)" }}>
                                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Inference Time</div>
                                    <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>{aiStats.latency_ms} ms</div>
                                </div>
                                <div style={{ background: "var(--surface-bg)", padding: 8, borderRadius: 6, border: "1px solid var(--border-color)" }}>
                                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Framerate</div>
                                    <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--success)" }}>{aiStats.fps} FPS</div>
                                </div>
                                <div style={{ background: "var(--surface-bg)", padding: 8, borderRadius: 6, border: "1px solid var(--border-color)" }}>
                                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Hardware Device</div>
                                    <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--primary)" }}>{aiStats.device}</div>
                                </div>
                                <div style={{ background: "var(--surface-bg)", padding: 8, borderRadius: 6, border: "1px solid var(--border-color)" }}>
                                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Active Tracks</div>
                                    <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#F59E0B" }}>{aiStats.tracked_count}</div>
                                </div>
                            </div>

                            <div style={{ fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-primary)" }}>
                                Current Object Detections ({currentDetections.length})
                            </div>
                            {currentDetections.length === 0 ? (
                                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic", padding: "8px 0" }}>
                                    No objects currently detected in view (scene clear).
                                </div>
                            ) : (
                                <div style={{ overflowX: "auto" }}>
                                    <table style={{ width: "100%", fontSize: "0.75rem", borderCollapse: "collapse" }}>
                                        <thead>
                                            <tr style={{ borderBottom: "1px solid var(--border-color)", textAlign: "left", color: "var(--text-muted)" }}>
                                                <th style={{ padding: "6px 8px" }}>Track ID</th>
                                                <th style={{ padding: "6px 8px" }}>Class ID</th>
                                                <th style={{ padding: "6px 8px" }}>Class Name</th>
                                                <th style={{ padding: "6px 8px" }}>Category</th>
                                                <th style={{ padding: "6px 8px" }}>Confidence</th>
                                                <th style={{ padding: "6px 8px" }}>Bounding Box [x1, y1, x2, y2]</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {currentDetections.map((d, i) => (
                                                <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                                                    <td style={{ padding: "6px 8px", fontWeight: 600, color: "#38BDF8" }}>#{d.track_id}</td>
                                                    <td style={{ padding: "6px 8px", color: "var(--text-muted)" }}>{d.class_id ?? "—"}</td>
                                                    <td style={{ padding: "6px 8px", fontWeight: 600, color: d.category === "person" ? "#67E8F9" : "var(--primary)" }}>{d.display_name || d.label}</td>
                                                    <td style={{ padding: "6px 8px" }}><span style={{ textTransform: "uppercase", fontSize: "0.6875rem", padding: "1px 5px", borderRadius: 3, background: d.category === "uncertain" ? "rgba(245,158,11,0.2)" : "rgba(99,102,241,0.2)", color: d.category === "uncertain" ? "#F59E0B" : "var(--primary)" }}>{d.category}</span></td>
                                                    <td style={{ padding: "6px 8px", fontWeight: 600 }}>{Math.round(d.confidence * 100)}%</td>
                                                    <td style={{ padding: "6px 8px", fontFamily: "monospace", color: "var(--text-muted)" }}>[{d.box ? d.box.join(", ") : ""}]</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Calibrated Demo Scenarios */}
                    <div className="card">

                        <div className="card-header">
                            <div className="card-title" style={{ margin: 0 }}>
                                <Sparkles size={15} style={{ color: "var(--primary)" }} />
                                <span>Automated Pipeline Scenarios</span>
                            </div>
                            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Simulated verification</span>
                        </div>
                        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 14 }}>
                            Execute calibrated computer vision test cases for state machine validation and event engine verification.
                        </p>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                            <button
                                className="btn btn-secondary btn-sm"
                                style={{ justifyContent: "flex-start" }}
                                onClick={() => triggerDemo("restock")}
                            >
                                <Package size={14} style={{ color: "var(--success)" }} />
                                <span>1. Product Restocking</span>
                            </button>
                            <button
                                className="btn btn-secondary btn-sm"
                                style={{ justifyContent: "flex-start" }}
                                onClick={() => triggerDemo("pickup")}
                            >
                                <ShoppingBag size={14} style={{ color: "var(--primary)" }} />
                                <span>2. Customer Pickup</span>
                            </button>
                            <button
                                className="btn btn-secondary btn-sm"
                                style={{ justifyContent: "flex-start" }}
                                onClick={() => triggerDemo("misplaced")}
                            >
                                <Shuffle size={14} style={{ color: "var(--warning)" }} />
                                <span>3. Misplaced Product</span>
                            </button>
                            <button
                                className="btn btn-secondary btn-sm"
                                style={{ justifyContent: "flex-start" }}
                                onClick={() => triggerDemo("suspicious_removal")}
                            >
                                <ShieldAlert size={14} style={{ color: "var(--danger)" }} />
                                <span>4. Loss Prevention</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right Panel: Verified Events & Loss Prevention Feed */}
                <div className="card" style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 150px)" }}>
                    <div className="card-header">
                        <div className="card-title" style={{ margin: 0 }}>
                            <Activity size={15} />
                            <span>Real-Time CV Event Log</span>
                            {events.length > 0 && <span className="badge badge-info" style={{ marginLeft: 6 }}>{events.length}</span>}
                        </div>
                        <button className="btn btn-ghost btn-sm" onClick={clearLog}>Clear</button>
                    </div>

                    <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }} ref={logRef}>
                        {events.length === 0 ? (
                            <div className="empty-state" style={{ margin: "auto" }}>
                                <Inbox size={32} />
                                <h3>No events logged yet</h3>
                                <p>Start your camera feed or trigger a pipeline scenario on the left.</p>
                            </div>
                        ) : (
                            events.map((e) => {
                                const isSuspicious = e.event_type === "SUSPICIOUS_REMOVAL" || e.severity === "CRITICAL";
                                const isMisplaced = e.event_type === "PRODUCT_MISPLACED";
                                const isRestock = e.event_type === "PRODUCT_PLACED" || e.type === "addition";

                                return (
                                    <div
                                        key={e.id || Math.random()}
                                        style={{
                                            background: isSuspicious ? "var(--danger-subtle)" : isMisplaced ? "var(--warning-subtle)" : isRestock ? "var(--success-subtle)" : "var(--surface-subtle)",
                                            border: `1px solid ${isSuspicious ? "var(--danger-border)" : isMisplaced ? "var(--warning-border)" : isRestock ? "var(--success-border)" : "var(--border-color)"}`,
                                            borderLeft: `4px solid ${isSuspicious ? "var(--danger)" : isMisplaced ? "var(--warning)" : isRestock ? "var(--success)" : "var(--primary)"}`,
                                            borderRadius: "var(--radius-md)",
                                            padding: "10px 14px",
                                        }}
                                    >
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                            <div style={{
                                                fontWeight: 600,
                                                fontSize: "0.8125rem",
                                                display: "flex",
                                                alignItems: "center",
                                                gap: 6,
                                                color: isSuspicious ? "var(--danger)" : isMisplaced ? "var(--warning)" : isRestock ? "var(--success)" : "var(--text-primary)"
                                            }}>
                                                {isSuspicious ? (
                                                    <>
                                                        <ShieldAlert size={14} />
                                                        <span>Loss Prevention Alert</span>
                                                    </>
                                                ) : isMisplaced ? (
                                                    <>
                                                        <AlertTriangle size={14} />
                                                        <span>Misplaced Product</span>
                                                    </>
                                                ) : isRestock ? (
                                                    <>
                                                        <CheckCircle2 size={14} />
                                                        <span>Shelf Restocked</span>
                                                    </>
                                                ) : (
                                                    <>
                                                        <Package size={14} />
                                                        <span>Product Removed</span>
                                                    </>
                                                )}
                                            </div>
                                            <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                                                {e.timestamp ? new Date(e.timestamp.endsWith("Z") ? e.timestamp : `${e.timestamp}Z`).toLocaleTimeString("en-US", { hour12: false }) : "Just now"}
                                            </span>
                                        </div>

                                        <div style={{ marginTop: 4, fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                                            <strong>{e.product || e.product_name}</strong>
                                            {e.quantity && (
                                                <span style={{
                                                    marginLeft: 6,
                                                    fontWeight: 600,
                                                    color: isRestock ? "var(--success)" : "var(--danger)"
                                                }}>
                                                    ({isRestock ? `+${e.quantity}` : `-${e.quantity}`} units)
                                                </span>
                                            )}
                                            {e.tracking_id && (
                                                <span style={{ marginLeft: 6, color: "var(--text-secondary)", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                                                    [Track #{e.tracking_id}]
                                                </span>
                                            )}
                                        </div>

                                        {e.metadata?.reason && (
                                            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                                                {e.metadata.reason}
                                            </div>
                                        )}

                                        {e.metadata?.suspicious_score && (
                                            <div style={{ marginTop: 6 }}>
                                                <span className="badge badge-danger" style={{ fontSize: "0.6875rem" }}>
                                                    Suspicious Score: {e.metadata.suspicious_score}/100
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default LiveMonitor;
