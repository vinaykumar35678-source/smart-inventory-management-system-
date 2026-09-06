import React, { useEffect, useState, useCallback } from "react";
import api from "../api";
import StockTable from "../components/StockTable";
import { Plus, X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

const EMPTY_FORM = { name: "", stock: 0, threshold: 5, price: 0, category: "General", image_url: "" };
const CATEGORIES = ["General", "Fruits", "Vegetables", "Dairy", "Bakery", "Beverages", "Snacks"];

function Inventory() {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editMode, setEditMode] = useState(false);
    const [form, setForm] = useState(EMPTY_FORM);
    const [editId, setEditId] = useState(null);
    const [toast, setToast] = useState(null);

    const showToast = (msg, type = "success") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    const fetchProducts = useCallback(async () => {
        try {
            const res = await api.get("/products");
            setProducts(res.data);
        } catch (e) {
            showToast("Failed to load products", "error");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchProducts(); }, [fetchProducts]);

    const openAdd = () => {
        setForm(EMPTY_FORM); setEditMode(false); setEditId(null); setShowModal(true);
    };

    const openEdit = (p) => {
        setForm({
            name: p.name,
            stock: p.stock,
            threshold: p.threshold,
            price: p.price,
            category: p.category || "General",
            image_url: p.image_url || ""
        });
        setEditMode(true); setEditId(p.id); setShowModal(true);
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to remove this product?")) return;
        try {
            await api.delete(`/products/${id}`);
            showToast("Product deleted successfully");
            fetchProducts();
        } catch {
            showToast("Failed to delete product", "error");
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const payload = {
            ...form,
            stock: Number(form.stock),
            threshold: Number(form.threshold),
            price: Number(form.price),
            image_url: form.image_url || "",
        };
        try {
            if (editMode) {
                await api.put(`/products/${editId}`, payload);
                showToast("Product updated successfully");
            } else {
                await api.post("/products", payload);
                showToast("Product added successfully");
            }
            setShowModal(false);
            fetchProducts();
        } catch (err) {
            const detail = err.response?.data?.detail || "Operation failed";
            showToast(detail, "error");
        }
    };

    return (
        <div className="page-content">
            {/* Toast Notification */}
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
                    <h1>Inventory Management</h1>
                    <p>Track real-time item quantities, safety thresholds, categories, and automated computer vision audits</p>
                </div>
                <button className="btn btn-primary btn-sm" onClick={openAdd}>
                    <Plus size={15} />
                    <span>Add Product</span>
                </button>
            </div>

            {loading ? (
                <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 60, flexDirection: "column", gap: 12 }}>
                    <Loader2 className="animate-spin" size={32} style={{ color: "var(--primary)" }} />
                    <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>Loading inventory items...</p>
                </div>
            ) : (
                <StockTable
                    products={products}
                    onEdit={openEdit}
                    onDelete={handleDelete}
                    onRefresh={fetchProducts}
                />
            )}

            {/* Product Modal */}
            {showModal && (
                <div className="modal-backdrop">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h2 className="modal-title">
                                {editMode ? "Edit Product" : "Add New Product"}
                            </h2>
                            <button
                                className="btn btn-ghost btn-sm"
                                onClick={() => setShowModal(false)}
                                style={{ padding: 4 }}
                            >
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit}>
                            <div className="modal-body">
                                <div className="form-group">
                                    <label className="form-label">Product Name</label>
                                    <input
                                        className="form-input"
                                        type="text"
                                        value={form.name}
                                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                                        placeholder="e.g. Whole Milk 1L"
                                        required
                                    />
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                                    <div className="form-group">
                                        <label className="form-label">Category</label>
                                        <select
                                            className="form-select"
                                            value={form.category}
                                            onChange={(e) => setForm({ ...form, category: e.target.value })}
                                        >
                                            {CATEGORIES.map((c) => (
                                                <option key={c} value={c}>{c}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Unit Price (₹)</label>
                                        <input
                                            className="form-input"
                                            type="number"
                                            value={form.price}
                                            onChange={(e) => setForm({ ...form, price: e.target.value })}
                                            min="0"
                                            step="0.01"
                                            required
                                        />
                                    </div>
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                                    <div className="form-group">
                                        <label className="form-label">Current Stock</label>
                                        <input
                                            className="form-input"
                                            type="number"
                                            value={form.stock}
                                            onChange={(e) => setForm({ ...form, stock: e.target.value })}
                                            min="0"
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Alert Threshold</label>
                                        <input
                                            className="form-input"
                                            type="number"
                                            value={form.threshold}
                                            onChange={(e) => setForm({ ...form, threshold: e.target.value })}
                                            min="0"
                                            required
                                        />
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn btn-primary">
                                    {editMode ? "Save Changes" : "Create Product"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Inventory;
