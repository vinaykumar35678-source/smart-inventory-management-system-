import React, { useState, useEffect, useRef } from "react";
import api from "../api";
import {
    Database, Play, CheckCircle2, ShieldCheck,
    Cpu, Zap, Eye, Sparkles, Sliders, RefreshCw, BarChart2,
    Layers, Upload, Check, Package, AlertCircle
} from "lucide-react";

function ModelTraining() {
    const [activeTab, setActiveTab] = useState("datasets"); // "datasets" | "preview" | "training" | "models" | "testing"

    // Datasets
    const [datasets, setDatasets] = useState([]);
    const [selectedDataset, setSelectedDataset] = useState(null);
    const [validationReport, setValidationReport] = useState(null);
    const [isValidating, setIsValidating] = useState(false);
    const [previews, setPreviews] = useState([]);
    const [isLoadingPreviews, setIsLoadingPreviews] = useState(false);

    // Import form
    const [importName, setImportName] = useState("");
    const [importPath, setImportPath] = useState("");
    const [isImporting, setIsImporting] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [isPreparing, setIsPreparing] = useState(false);
    const [systemResources, setSystemResources] = useState(null);

    // Training Config & Progress
    const [trainingConfig, setTrainingConfig] = useState({
        base_model: "yolo11s.pt",
        epochs: 20,
        batch_size: 8,
        image_size: 640,
        model_name: "inventory_yolo11"
    });
    const [trainingStatus, setTrainingStatus] = useState({
        status: "NOT_STARTED",
        current_epoch: 0,
        total_epochs: 20,
        device: "CPU",
        loss: 0,
        precision: 0,
        recall: 0,
        map50: 0,
        map50_95: 0,
        message: "No active training job."
    });
    const [isLaunching, setIsLaunching] = useState(false);

    // Models & Comparison
    const [models, setModels] = useState([]);
    const [comparison, setComparison] = useState(null);
    const [activeModelId, setActiveModelId] = useState("");

    // Testing Playground
    const [testImage, setTestImage] = useState(null);
    const [testModelId, setTestModelId] = useState("");
    const [testResult, setTestResult] = useState(null);
    const [isTesting, setIsTesting] = useState(false);

    const pollTimerRef = useRef(null);

    // ── Initial Fetch ──────────────────────────────────────
    const fetchInitialData = async () => {
        try {
            const [dsRes, modRes, cfgRes, compRes, resRes] = await Promise.all([
                api.get("/ml/datasets"),
                api.get("/ml/models"),
                api.get("/ml/training/config"),
                api.get("/ml/models/compare"),
                api.get("/ml/system/resources").catch(() => ({ data: null }))
            ]);
            setDatasets(dsRes.data);
            if (dsRes.data.length > 0) {
                setSelectedDataset(dsRes.data[0]);
            }
            setModels(modRes.data);
            const active = modRes.data.find(m => m.is_active);
            if (active) {
                setActiveModelId(active.model_id);
                setTestModelId(active.model_id);
            } else if (modRes.data.length > 0) {
                setActiveModelId(modRes.data[0].model_id);
                setTestModelId(modRes.data[0].model_id);
            }
            if (cfgRes.data) {
                setTrainingConfig(prev => ({ ...prev, ...cfgRes.data }));
            }
            setComparison(compRes.data);
            if (resRes?.data) {
                setSystemResources(resRes.data);
            }
        } catch (err) {
            console.error("Failed to load ML data:", err);
        }
    };

    useEffect(() => {
        fetchInitialData();
        return () => clearInterval(pollTimerRef.current);
    }, []);


    // ── Poll Training Status ────────────────────────────────
    useEffect(() => {
        const pollStatus = async () => {
            try {
                const res = await api.get("/ml/training/status");
                setTrainingStatus(res.data);
                if (res.data.status === "COMPLETED" || res.data.status === "FAILED") {
                    clearInterval(pollTimerRef.current);
                    // Refresh models
                    api.get("/ml/models").then(r => setModels(r.data));
                    api.get("/ml/models/compare").then(r => setComparison(r.data));
                }
            } catch (_) {}
        };

        if (trainingStatus.status === "TRAINING") {
            pollTimerRef.current = setInterval(pollStatus, 2000);
        } else {
            clearInterval(pollTimerRef.current);
        }
        return () => clearInterval(pollTimerRef.current);
    }, [trainingStatus.status]);

    // ── Validate Dataset ───────────────────────────────────
    const handleValidate = async () => {
        if (!selectedDataset) return;
        setIsValidating(true);
        try {
            const res = await api.post("/ml/datasets/validate", {
                dataset_path: selectedDataset.path,
                yaml_path: selectedDataset.yaml_path
            });
            setValidationReport(res.data);
        } catch (err) {
            alert(`Validation failed: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsValidating(false);
        }
    };

    // ── Load Previews ──────────────────────────────────────
    const handleLoadPreviews = async () => {
        if (!selectedDataset) return;
        setIsLoadingPreviews(true);
        try {
            const res = await api.get(`/ml/datasets/preview?dataset_path=${encodeURIComponent(selectedDataset.path)}&max_samples=6`);
            setPreviews(res.data.previews || []);
        } catch (err) {
            console.error("Failed to fetch previews:", err);
        } finally {
            setIsLoadingPreviews(false);
        }
    };

    useEffect(() => {
        if (activeTab === "preview" && selectedDataset && previews.length === 0) {
            handleLoadPreviews();
        }
    }, [activeTab, selectedDataset]);

    // ── Import Dataset ─────────────────────────────────────
    const handleImport = async (e) => {
        e.preventDefault();
        if (!importName || !importPath) return;
        setIsImporting(true);
        try {
            const isZip = importPath.toLowerCase().endsWith(".zip");
            await api.post("/ml/datasets/import", {
                source_type: isZip ? "zip" : "directory",
                source_path: importPath,
                dataset_name: importName
            });
            alert("Dataset imported successfully!");
            setImportName("");
            setImportPath("");
            const res = await api.get("/ml/datasets");
            setDatasets(res.data);
        } catch (err) {
            alert(`Import error: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsImporting(false);
        }
    };

    // ── Start Training ─────────────────────────────────────
    const handleStartTraining = async () => {
        if (!selectedDataset) {
            alert("Please select a valid dataset first.");
            return;
        }
        setIsLaunching(true);
        try {
            await api.post("/ml/training/start", {
                data_yaml: selectedDataset.yaml_path || "smart_shelf/data.yaml",
                base_model: trainingConfig.base_model,
                epochs: parseInt(trainingConfig.epochs, 10),
                batch_size: parseInt(trainingConfig.batch_size, 10),
                image_size: parseInt(trainingConfig.image_size, 10),
                model_name: trainingConfig.model_name || `inventory_${Date.now()}`,
                dataset_name: selectedDataset.name
            });
            setTrainingStatus(prev => ({ ...prev, status: "TRAINING" }));
            alert("Training job launched successfully! Monitor progress in real-time below.");
        } catch (err) {
            alert(`Training launch error: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsLaunching(false);
        }
    };

    // ── Activate Model ─────────────────────────────────────
    const handleActivateModel = async (modelId) => {
        try {
            const res = await api.post(`/ml/models/${modelId}/activate`);
            setActiveModelId(modelId);
            setModels(prev => prev.map(m => ({ ...m, is_active: m.model_id === modelId })));
            alert(`Model activated! The live detection pipeline will now use '${res.data.active_model.model_name}'.`);
        } catch (err) {
            alert(`Failed to activate model: ${err.response?.data?.detail || err.message}`);
        }
    };

    // ── Dataset Actions & Rollback ─────────────────────────
    const handleDownloadDatasets = async () => {
        setIsDownloading(true);
        try {
            await api.post("/ml/datasets/download");
            alert("Approved retail dataset successfully ingested into ml/datasets/raw/!");
            fetchInitialData();
        } catch (err) {
            alert("Download error: " + (err.response?.data?.detail || err.message));
        } finally {
            setIsDownloading(false);
        }
    };

    const handlePrepareDatasets = async () => {
        setIsPreparing(true);
        try {
            await api.post("/ml/datasets/prepare");
            alert("Multi-product dataset normalized, deduplicated, and split (70% train / 20% val / 10% test) into ml/datasets/merged/!");
            fetchInitialData();
        } catch (err) {
            alert("Preparation error: " + (err.response?.data?.detail || err.message));
        } finally {
            setIsPreparing(false);
        }
    };

    const handleRollbackModel = async () => {
        if (!window.confirm("Rollback active model to verified base architecture?")) return;
        try {
            const res = await api.post("/ml/models/rollback");
            setActiveModelId(res.data.active_model.active_model_id);
            setModels(prev => prev.map(m => ({ ...m, is_active: m.model_id === res.data.active_model.active_model_id })));
            alert(`Rolled back successfully to '${res.data.active_model.model_name}'!`);
        } catch (err) {
            alert("Rollback failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleSyncDb = async (modelId) => {
        try {
            const res = await api.post(`/ml/models/${modelId}/sync-db`);
            alert(`Synchronized ${res.data.synced_count} classes to products database table!`);
        } catch (err) {
            alert("Database sync failed: " + (err.response?.data?.detail || err.message));
        }
    };


    // ── Test Model on Image ────────────────────────────────
    const handleImageUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setTestImage(reader.result);
                setTestResult(null);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleRunTest = async () => {
        if (!testImage || !testModelId) return;
        setIsTesting(true);
        try {
            const res = await api.post("/ml/models/test", {
                model_id: testModelId,
                image: testImage,
                confidence: 0.35
            });
            setTestResult(res.data);
        } catch (err) {
            alert(`Testing failed: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsTesting(false);
        }
    };

    return (
        <div className="page-content">
            {/* Header with Hardware & Active Model Status */}
            <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <h1>Custom Dataset Training &amp; Model Studio</h1>
                    <p>Import custom YOLO retail datasets, validate annotations, train custom weights, and hot-swap active models</p>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                    <span className="badge badge-blue" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <Cpu size={14} /> Device: {trainingStatus.device || "CPU"}
                    </span>
                    <span className="badge badge-green" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <CheckCircle2 size={14} /> Active Model: {models.find(m => m.is_active)?.model_name || "YOLOv8 Nano"}
                    </span>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--border)", marginBottom: 20, paddingBottom: 6 }}>
                {[
                    { id: "datasets", label: "1. Dataset Import & Validation", icon: <Database size={16} /> },
                    { id: "preview", label: "2. Dataset Preview", icon: <Eye size={16} /> },
                    { id: "training", label: "3. Training Studio", icon: <Sliders size={16} /> },
                    { id: "models", label: "4. Model Registry & Activation", icon: <Layers size={16} /> },
                    { id: "testing", label: "5. Model Playground", icon: <Sparkles size={16} /> }
                ].map(tab => (
                    <button
                        key={tab.id}
                        className={`btn btn-sm ${activeTab === tab.id ? "btn-primary" : "btn-ghost"}`}
                        onClick={() => setActiveTab(tab.id)}
                        style={{ display: "flex", alignItems: "center", gap: 6 }}
                    >
                        {tab.icon} {tab.label}
                    </button>
                ))}
            </div>

            {/* ========================================================
                TAB 1: DATASET IMPORT & VALIDATION
            ======================================================== */}
            {activeTab === "datasets" && (
                <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
                    {/* Available Datasets & Validation Card */}
                    <div className="card">
                        <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <Database size={18} color="var(--primary)" />
                            Available Inventory Datasets
                        </div>

                        {/* Quick Dataset Pipeline Actions */}
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
                            <button className="btn btn-sm btn-ghost" onClick={handleDownloadDatasets} disabled={isDownloading} style={{ border: "1px solid var(--border)" }}>
                                <RefreshCw size={13} className={isDownloading ? "animate-spin" : ""} style={{ marginRight: 4 }} />
                                {isDownloading ? "Ingesting..." : "Ingest Retail Datasets"}
                            </button>
                            <button className="btn btn-sm btn-ghost" onClick={handlePrepareDatasets} disabled={isPreparing} style={{ border: "1px solid var(--border)" }}>
                                <Layers size={13} className={isPreparing ? "animate-spin" : ""} style={{ marginRight: 4 }} />
                                {isPreparing ? "Preparing..." : "Merge Multi-Product (70/20/10)"}
                            </button>
                            <a
                                href="http://localhost:8000/api/ml/datasets/report"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-sm btn-ghost"
                                style={{ display: "flex", alignItems: "center", gap: 4, textDecoration: "none", border: "1px solid var(--border)" }}
                            >
                                <Eye size={13} /> View HTML Audit Report
                            </a>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
                            {datasets.map(ds => (
                                <div
                                    key={ds.id}
                                    onClick={() => { setSelectedDataset(ds); setValidationReport(null); setPreviews([]); }}
                                    style={{
                                        padding: "12px 16px", borderRadius: 8, cursor: "pointer",
                                        background: selectedDataset?.id === ds.id ? "rgba(99,102,241,0.12)" : "var(--bg-secondary)",
                                        border: `1px solid ${selectedDataset?.id === ds.id ? "var(--primary)" : "var(--border)"}`
                                    }}
                                >
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                        <strong style={{ fontSize: "0.95rem" }}>{ds.name}</strong>
                                        <span className="badge badge-blue">{ds.counts.total} Images</span>
                                    </div>
                                    <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 4 }}>
                                        Path: <code style={{ color: "var(--primary)" }}>{ds.path}</code>
                                    </div>
                                    <div style={{ display: "flex", gap: 12, marginTop: 8, fontSize: "0.8rem" }}>
                                        <span>Train: <strong>{ds.counts.train}</strong></span>
                                        <span>Val: <strong>{ds.counts.val}</strong></span>
                                        <span>Classes: <strong>{ds.num_classes}</strong></span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {selectedDataset && (
                            <div>
                                <button
                                    className="btn btn-primary"
                                    onClick={handleValidate}
                                    disabled={isValidating}
                                    style={{ width: "100%", display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}
                                >
                                    {isValidating ? <RefreshCw className="animate-spin" size={16} /> : <ShieldCheck size={16} />}
                                    {isValidating ? "Validating Dataset…" : "Run Deep Validation Check"}
                                </button>
                            </div>
                        )}

                        {/* Validation Results Report */}
                        {validationReport && (
                            <div style={{ marginTop: 20, padding: 14, background: "rgba(15,23,42,0.6)", borderRadius: 8, border: "1px solid var(--border)" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                                    <strong style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                        {validationReport.is_valid ? (
                                            <span style={{ color: "var(--success)", display: "flex", alignItems: "center", gap: 6 }}>
                                                <CheckCircle2 size={16} /> Dataset Valid &amp; Ready for Training
                                            </span>
                                        ) : (
                                            <span style={{ color: "var(--danger)", display: "flex", alignItems: "center", gap: 6 }}>
                                                <AlertCircle size={16} /> Issues Detected in Dataset
                                            </span>
                                        )}
                                    </strong>
                                </div>

                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8, marginBottom: 14 }}>
                                    <div className="card" style={{ padding: 10, textAlign: "center" }}>
                                        <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{validationReport.summary.total_images}</div>
                                        <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Images</div>
                                    </div>
                                    <div className="card" style={{ padding: 10, textAlign: "center" }}>
                                        <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{validationReport.summary.total_labels}</div>
                                        <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Labels</div>
                                    </div>
                                    <div className="card" style={{ padding: 10, textAlign: "center" }}>
                                        <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{validationReport.summary.valid_annotations}</div>
                                        <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>BBoxes</div>
                                    </div>
                                    <div className="card" style={{ padding: 10, textAlign: "center" }}>
                                        <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{validationReport.summary.classes_detected}</div>
                                        <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Classes</div>
                                    </div>
                                </div>

                                {/* Class Distribution */}
                                <div style={{ marginBottom: 10 }}>
                                    <span style={{ fontSize: "0.82rem", fontWeight: 600 }}>Class Distribution:</span>
                                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                                        {Object.entries(validationReport.class_distribution).map(([cname, count]) => (
                                            <span key={cname} className="badge badge-blue" style={{ fontSize: "0.75rem" }}>
                                                {cname}: {count}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Issue list */}
                                {validationReport.issues.corrupted_images.length > 0 && (
                                    <div style={{ color: "var(--accent-red)", fontSize: "0.78rem" }}>
                                        Corrupted Images: {validationReport.issues.corrupted_images.length}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Import New Dataset Form */}
                    <div className="card">
                        <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <Upload size={18} color="var(--primary)" />
                            Import Custom Dataset
                        </div>
                        <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 14 }}>
                            Import custom inventory products formatted in YOLO structure (`images/`, `labels/`, `data.yaml`) from a folder or ZIP file.
                        </p>

                        <form onSubmit={handleImport} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                            <div className="form-group">
                                <label className="form-label">Dataset Name</label>
                                <input
                                    className="form-control"
                                    type="text"
                                    placeholder="e.g. retail_beverages_v1"
                                    value={importName}
                                    onChange={e => setImportName(e.target.value)}
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Local Folder Path or ZIP File Path</label>
                                <input
                                    className="form-control"
                                    type="text"
                                    placeholder="D:/datasets/retail_dataset or D:/data.zip"
                                    value={importPath}
                                    onChange={e => setImportPath(e.target.value)}
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                className="btn btn-success"
                                disabled={isImporting}
                                style={{ marginTop: 8 }}
                            >
                                {isImporting ? "Importing Dataset…" : "Import & Parse Dataset"}
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* ========================================================
                TAB 2: DATASET PREVIEW
            ======================================================== */}
            {activeTab === "preview" && (
                <div>
                    <div className="card" style={{ marginBottom: 20 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div>
                                <h3 style={{ margin: 0, fontSize: "1.1rem" }}>Annotated Bounding Box Verification</h3>
                                <p style={{ margin: "4px 0 0", fontSize: "0.82rem", color: "var(--text-muted)" }}>
                                    Inspect bounding box positions, normalized coordinates, and class mappings to ensure data quality before training.
                                </p>
                            </div>
                            <button className="btn btn-primary btn-sm" onClick={handleLoadPreviews} disabled={isLoadingPreviews}>
                                <RefreshCw size={14} className={isLoadingPreviews ? "animate-spin" : ""} style={{ marginRight: 6 }} />
                                Refresh Sample Previews
                            </button>
                        </div>
                    </div>

                    {isLoadingPreviews ? (
                        <div style={{ textAlign: "center", padding: 40 }}>
                            <RefreshCw size={36} className="animate-spin" color="var(--primary)" />
                            <p style={{ marginTop: 12, color: "var(--text-muted)" }}>Loading annotated samples…</p>
                        </div>
                    ) : previews.length === 0 ? (
                        <div className="empty-state">
                            <Eye size={40} color="var(--text-muted)" />
                            <h3>No preview images available</h3>
                            <p>Click "Refresh Sample Previews" or choose another dataset</p>
                        </div>
                    ) : (
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
                            {previews.map((item, idx) => (
                                <div key={idx} className="card" style={{ padding: 12 }}>
                                    <div style={{ position: "relative", borderRadius: 8, overflow: "hidden", aspectRatio: "4/3", background: "#000" }}>
                                        <img src={item.image_base64} alt={item.filename} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                                    </div>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
                                        <span style={{ fontSize: "0.82rem", fontWeight: 600 }}>{item.filename}</span>
                                        <span className="badge badge-blue">{item.annotations_count} BBoxes</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* ========================================================
                TAB 3: TRAINING STUDIO
            ======================================================== */}
            {activeTab === "training" && (
                <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.3fr", gap: 20 }}>
                    {/* Training Configuration Form */}
                    <div className="card">
                        <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <Sliders size={18} color="var(--primary)" />
                            Custom YOLO Training Studio
                        </div>

                        {/* Hardware Resource Pre-flight Banner */}
                        {systemResources && (
                            <div style={{ padding: "10px 14px", background: "rgba(15,23,42,0.8)", borderRadius: 8, border: "1px solid var(--border)", marginBottom: 14 }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem", flexWrap: "wrap", gap: 8 }}>
                                    <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--accent-cyan)", fontWeight: 600 }}>
                                        <Cpu size={14} /> Hardware Pre-Flight: {systemResources.device} ({systemResources.device_name})
                                    </span>
                                    <span>RAM: <strong>{systemResources.ram_available_gb} GB free</strong></span>
                                    <span>Disk: <strong>{systemResources.disk_free_gb} GB free</strong></span>
                                    <span className={`badge ${systemResources.is_safe ? "badge-green" : "badge-red"}`}>
                                        {systemResources.is_safe ? "SYSTEM SAFE" : "LOW RESOURCES"}
                                    </span>
                                </div>
                            </div>
                        )}

                        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                            <div className="form-group">
                                <label className="form-label">Pretrained Base Model (Transfer Learning)</label>
                                <select
                                    className="form-control"
                                    value={trainingConfig.base_model}
                                    onChange={e => setTrainingConfig({ ...trainingConfig, base_model: e.target.value })}
                                >
                                    <option value="yolo11s.pt">YOLO11 Small (Recommended — Multi-Product Retail)</option>
                                    <option value="yolo11n.pt">YOLO11 Nano (Next-Gen, Fast CPU Execution)</option>
                                    <option value="yolov8n.pt">YOLOv8 Nano (Legacy Baseline Fallback)</option>
                                    <option value="yolov8s.pt">YOLOv8 Small (Balanced)</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label className="form-label">New Model Version Name</label>
                                <input
                                    className="form-control"
                                    type="text"
                                    value={trainingConfig.model_name}
                                    onChange={e => setTrainingConfig({ ...trainingConfig, model_name: e.target.value })}
                                    placeholder="e.g. inventory_custom_v1"
                                />
                            </div>

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                <div className="form-group">
                                    <label className="form-label">Training Epochs ({trainingConfig.epochs})</label>
                                    <input
                                        type="range" min="5" max="100" step="5"
                                        value={trainingConfig.epochs}
                                        onChange={e => setTrainingConfig({ ...trainingConfig, epochs: parseInt(e.target.value, 10) })}
                                        style={{ width: "100%" }}
                                    />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Batch Size</label>
                                    <select
                                        className="form-control"
                                        value={trainingConfig.batch_size}
                                        onChange={e => setTrainingConfig({ ...trainingConfig, batch_size: parseInt(e.target.value, 10) })}
                                    >
                                        <option value="4">4 (CPU / Low RAM)</option>
                                        <option value="8">8 (Recommended)</option>
                                        <option value="16">16 (GPU)</option>
                                    </select>
                                </div>
                            </div>

                            <div className="form-group">
                                <label className="form-label">Image Input Size</label>
                                <select
                                    className="form-control"
                                    value={trainingConfig.image_size}
                                    onChange={e => setTrainingConfig({ ...trainingConfig, image_size: parseInt(e.target.value, 10) })}
                                >
                                    <option value="640">640x640 (Standard YOLO resolution)</option>
                                    <option value="320">320x320 (Lightweight CPU)</option>
                                </select>
                            </div>

                            <button
                                className="btn btn-primary"
                                onClick={handleStartTraining}
                                disabled={isLaunching || trainingStatus.status === "TRAINING"}
                                style={{ marginTop: 10, padding: 12, display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}
                            >
                                <Play size={16} />
                                {trainingStatus.status === "TRAINING" ? "Training in Progress…" : "Start Custom YOLO Training"}
                            </button>
                        </div>
                    </div>

                    {/* Live Training Progress & Metrics HUD */}
                    <div className="card">
                        <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <BarChart2 size={18} color="var(--primary)" />
                                Live Training Telemetry
                            </span>
                            <span className={`badge ${trainingStatus.status === "TRAINING" ? "badge-blue" : trainingStatus.status === "COMPLETED" ? "badge-green" : "badge-gray"}`}>
                                {trainingStatus.status}
                            </span>
                        </div>

                        {/* Progress Bar */}
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: 6 }}>
                                <span>Epoch: <strong>{trainingStatus.current_epoch} / {trainingStatus.total_epochs}</strong></span>
                                <span>{trainingStatus.total_epochs > 0 ? Math.round((trainingStatus.current_epoch / trainingStatus.total_epochs) * 100) : 0}%</span>
                            </div>
                            <div style={{ height: 8, background: "var(--bg-secondary)", borderRadius: 10, overflow: "hidden" }}>
                                <div
                                    style={{
                                        height: "100%",
                                        width: `${trainingStatus.total_epochs > 0 ? (trainingStatus.current_epoch / trainingStatus.total_epochs) * 100 : 0}%`,
                                        background: "linear-gradient(90deg, var(--primary), var(--accent-cyan))",
                                        transition: "width 0.4s ease"
                                    }}
                                />
                            </div>
                        </div>

                        {/* Real-Time Metrics Cards */}
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 16 }}>
                            <div className="card" style={{ padding: 12, textAlign: "center" }}>
                                <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--primary)" }}>
                                    {trainingStatus.precision ? `${Math.round(trainingStatus.precision * 100)}%` : "—"}
                                </div>
                                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Precision</div>
                            </div>

                            <div className="card" style={{ padding: 12, textAlign: "center" }}>
                                <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--accent-cyan)" }}>
                                    {trainingStatus.recall ? `${Math.round(trainingStatus.recall * 100)}%` : "—"}
                                </div>
                                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Recall</div>
                            </div>

                            <div className="card" style={{ padding: 12, textAlign: "center" }}>
                                <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--accent-green)" }}>
                                    {trainingStatus.map50 ? `${Math.round(trainingStatus.map50 * 100)}%` : "—"}
                                </div>
                                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>mAP@0.50</div>
                            </div>
                        </div>

                        <div style={{ padding: 12, background: "rgba(15,23,42,0.8)", borderRadius: 8, fontSize: "0.8rem", fontFamily: "monospace", color: "var(--text-secondary)" }}>
                            <div>[Status] {trainingStatus.message}</div>
                            {trainingStatus.loss > 0 && <div style={{ marginTop: 4 }}>[Loss] {trainingStatus.loss}</div>}
                            {trainingStatus.map50_95 > 0 && <div style={{ marginTop: 4 }}>[mAP@0.50:0.95] {trainingStatus.map50_95}</div>}
                        </div>
                    </div>
                </div>
            )}

            {/* ========================================================
                TAB 4: MODEL REGISTRY & COMPARISON
            ======================================================== */}
            {activeTab === "models" && (
                <div>
                    <div className="card" style={{ marginBottom: 20 }}>
                        <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <Layers size={18} color="var(--primary)" />
                            Model Registry &amp; Active Detection Pipeline
                        </div>
                        <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 12 }}>
                            Multiple trained models can be maintained concurrently. The active model directly powers the live camera detection and ByteTrack pipeline.
                        </p>

                        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 16 }}>
                            <button className="btn btn-sm btn-outline" onClick={handleRollbackModel}>
                                <RefreshCw size={13} style={{ marginRight: 6 }} /> Rollback to Baseline Model
                            </button>
                            {activeModelId && (
                                <button className="btn btn-sm btn-outline" onClick={() => handleSyncDb(activeModelId)}>
                                    <Package size={13} style={{ marginRight: 6 }} /> Sync Active Classes to Inventory DB
                                </button>
                            )}
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16 }}>
                            {models.map(m => (
                                <div
                                    key={m.model_id}
                                    className="card"
                                    style={{
                                        border: m.is_active ? "2px solid var(--accent-green)" : "1px solid var(--border)",
                                        background: m.is_active ? "rgba(16,185,129,0.06)" : "var(--bg-secondary)",
                                        position: "relative"
                                    }}
                                >
                                    {m.is_active && (
                                        <span className="badge badge-green" style={{ position: "absolute", top: 12, right: 12, display: "flex", alignItems: "center", gap: 4 }}>
                                            <Check size={12} /> ACTIVE
                                        </span>
                                    )}

                                    <h3 style={{ margin: "0 0 6px", fontSize: "1.05rem" }}>{m.model_name}</h3>
                                    <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 10 }}>
                                        Dataset: <strong>{m.dataset}</strong> | Classes: <strong>{m.num_classes}</strong>
                                    </div>

                                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6, marginBottom: 14 }}>
                                        <div style={{ background: "rgba(0,0,0,0.2)", padding: 6, borderRadius: 6, textAlign: "center" }}>
                                            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Precision</div>
                                            <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>{Math.round((m.precision || 0) * 100)}%</div>
                                        </div>
                                        <div style={{ background: "rgba(0,0,0,0.2)", padding: 6, borderRadius: 6, textAlign: "center" }}>
                                            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Recall</div>
                                            <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>{Math.round((m.recall || 0) * 100)}%</div>
                                        </div>
                                        <div style={{ background: "rgba(0,0,0,0.2)", padding: 6, borderRadius: 6, textAlign: "center" }}>
                                            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>mAP50</div>
                                            <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "var(--accent-green)" }}>{Math.round((m.map50 || 0) * 100)}%</div>
                                        </div>
                                    </div>

                                    {!m.is_active && (
                                        <button
                                            className="btn btn-sm btn-primary"
                                            onClick={() => handleActivateModel(m.model_id)}
                                            style={{ width: "100%", display: "flex", justifyContent: "center", alignItems: "center", gap: 6 }}
                                        >
                                            <Zap size={14} /> Activate for Live Detection
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Pretrained vs Custom Model Comparison Table */}
                    {comparison && comparison.models_comparison.length > 1 && (
                        <div className="card">
                            <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <BarChart2 size={16} />
                                <span>Model Architecture &amp; Benchmark Comparison</span>
                            </div>
                            <div className="table-container">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Model Name</th>
                                            <th>Type</th>
                                            <th>Classes</th>
                                            <th>Precision</th>
                                            <th>Recall</th>
                                            <th>mAP@0.50</th>
                                            <th>mAP@0.50:0.95</th>
                                            <th>Latency (ms)</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {comparison.models_comparison.map(row => (
                                            <tr key={row.model_id} style={{ background: row.is_active ? "rgba(16,185,129,0.08)" : "transparent" }}>
                                                <td><strong>{row.model_name}</strong></td>
                                                <td>{row.is_custom ? "Custom Trained" : "COCO Base"}</td>
                                                <td>{row.num_classes}</td>
                                                <td>{Math.round(row.precision * 100)}%</td>
                                                <td>{Math.round(row.recall * 100)}%</td>
                                                <td style={{ color: "var(--accent-green)", fontWeight: 700 }}>{Math.round(row.map50 * 100)}%</td>
                                                <td>{Math.round(row.map50_95 * 100)}%</td>
                                                <td>{row.inference_speed_ms} ms</td>
                                                <td>
                                                    {row.is_active ? (
                                                        <span className="badge badge-green">ACTIVE PIPELINE</span>
                                                    ) : (
                                                        <span className="badge badge-gray">Standby</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ========================================================
                TAB 5: MODEL TESTING PLAYGROUND
            ======================================================== */}
            {activeTab === "testing" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                    {/* Input Viewport */}
                    <div className="card">
                        <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <Sparkles size={18} color="var(--primary)" />
                            Test Trained Model on Sample
                        </div>

                        <div className="form-group" style={{ marginBottom: 14 }}>
                            <label className="form-label">Select Model to Test</label>
                            <select
                                className="form-control"
                                value={testModelId}
                                onChange={e => setTestModelId(e.target.value)}
                            >
                                {models.map(m => (
                                    <option key={m.model_id} value={m.model_id}>
                                        {m.model_name} ({m.is_active ? "ACTIVE" : "Standby"})
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div style={{ marginBottom: 14 }}>
                            <label className="form-label">Upload Image to Test</label>
                            <input type="file" accept="image/*" onChange={handleImageUpload} />
                        </div>

                        {testImage && (
                            <div style={{ position: "relative", borderRadius: 8, overflow: "hidden", aspectRatio: "16/9", background: "#000", marginBottom: 14 }}>
                                <img src={testImage} alt="Test sample" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                            </div>
                        )}

                        <button
                            className="btn btn-primary"
                            onClick={handleRunTest}
                            disabled={!testImage || isTesting}
                            style={{ width: "100%", display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}
                        >
                            {isTesting ? <RefreshCw className="animate-spin" size={16} /> : <Play size={16} />}
                            {isTesting ? "Running Inference…" : "Run Model Inference"}
                        </button>
                    </div>

                    {/* Detection Results */}
                    <div className="card">
                        <div className="section-title">Inference Results &amp; Bounding Boxes</div>
                        {testResult ? (
                            <div>
                                <div style={{ position: "relative", borderRadius: 8, overflow: "hidden", aspectRatio: "16/9", background: "#000", marginBottom: 14 }}>
                                    <img src={testResult.annotated_image} alt="Annotated inference result" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                                </div>

                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                                    <strong>Detected Items ({testResult.detections_count}):</strong>
                                    <span className="badge badge-blue">Device: {testResult.device}</span>
                                </div>

                                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    {testResult.detections.map((d, idx) => (
                                        <div
                                            key={idx}
                                            style={{
                                                padding: "8px 12px", background: "var(--surface-subtle)", borderRadius: "var(--radius-sm)",
                                                border: "1px solid var(--border-subtle)",
                                                display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.85rem"
                                            }}
                                        >
                                            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                                <Package size={14} style={{ color: "var(--primary)" }} />
                                                <strong>{d.label}</strong> (Class #{d.class_id})
                                            </span>
                                            <span style={{ color: "var(--primary)", fontWeight: 700 }}>
                                                {Math.round(d.confidence * 100)}% Confidence
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="empty-state">
                                <Sparkles size={40} color="var(--text-muted)" />
                                <h3>No test run yet</h3>
                                <p>Upload an image on the left and click "Run Model Inference"</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default ModelTraining;
