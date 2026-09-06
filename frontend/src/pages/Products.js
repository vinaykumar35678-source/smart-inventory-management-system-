import React, { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { Package, Plus, Trash2, Search, X } from "lucide-react";

function Products() {
    const { isAdmin } = useAuth();
    const [products, setProducts] = useState([]);
    const [shelves, setShelves] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [newProd, setNewProd] = useState({
        name: "",
        category: "Fruits",
        stock: 20,
        expected_stock: 20,
        threshold: 5,
        price: 50.0,
        class_id: 0,
        shelf_id: null,
        image_url: ""
    });

    const fetchData = async () => {
        try {
            setLoading(true);
            const [pRes, sRes] = await Promise.all([
                api.get("/products"),
                api.get("/shelves")
            ]);
            setProducts(pRes.data);
            setShelves(sRes.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            const res = await api.post("/products", newProd);
            setProducts([...products, res.data]);
            setShowModal(false);
            setNewProd({
                name: "",
                category: "Fruits",
                stock: 20,
                expected_stock: 20,
                threshold: 5,
                price: 50.0,
                class_id: 0,
                shelf_id: null,
                image_url: ""
            });
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to create product");
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to remove this product and class mapping?")) return;
        try {
            await api.delete(`/products/${id}`);
            setProducts(products.filter(p => p.id !== id));
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to delete product");
        }
    };

    const filtered = products.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.category.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="page-content">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1>Product Catalog &amp; YOLO Class Mappings</h1>
                    <p>Manage retail inventory definitions, neural network class ID bindings, and zone assignments</p>
                </div>
                {isAdmin && (
                    <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
                        <Plus size={15} />
                        <span>Add Product</span>
                    </button>
                )}
            </div>

            {/* Search Bar */}
            <div style={{ marginBottom: 18, position: "relative", maxWidth: 360 }}>
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
                    placeholder="Search products or categories..."
                    style={{ paddingLeft: 32 }}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {/* Product Table */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 48, textAlign: "center", color: "var(--text-secondary)" }}>
                        Loading products catalog...
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state">
                        <Package size={36} />
                        <h3>No products found</h3>
                        <p>Try searching for a different item or add a new product entry.</p>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>Category</th>
                                <th>Stock</th>
                                <th>Threshold</th>
                                <th>Assigned Shelf</th>
                                <th>YOLO Class ID</th>
                                <th>Price</th>
                                {isAdmin && <th style={{ textAlign: "right" }}>Actions</th>}
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((p) => {
                                const shelf = shelves.find(s => s.id === p.shelf_id);
                                const isLow = p.stock <= p.threshold;

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
                                                    <Package size={15} />
                                                </div>
                                                <span style={{ fontWeight: 600 }}>{p.name}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="badge badge-info">{p.category}</span>
                                        </td>
                                        <td>
                                            <strong style={{ color: isLow ? "var(--danger)" : "var(--text-primary)" }}>
                                                {p.stock}
                                            </strong>
                                        </td>
                                        <td style={{ color: "var(--text-secondary)" }}>
                                            {p.threshold} units
                                        </td>
                                        <td>
                                            <span style={{ color: shelf ? "var(--primary)" : "var(--text-muted)", fontWeight: shelf ? 500 : 400 }}>
                                                {shelf ? shelf.name : "Unassigned"}
                                            </span>
                                        </td>
                                        <td>
                                            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", background: "var(--surface-subtle)", padding: "2px 6px", borderRadius: "var(--radius-xs)" }}>
                                                {p.class_id != null ? `Class #${p.class_id}` : "auto"}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 500 }}>
                                            ₹{p.price?.toFixed(2) || "0.00"}
                                        </td>
                                        {isAdmin && (
                                            <td style={{ textAlign: "right" }}>
                                                <button
                                                    className="btn btn-outline-danger btn-sm"
                                                    onClick={() => handleDelete(p.id)}
                                                    title="Delete Product"
                                                >
                                                    <Trash2 size={13} />
                                                </button>
                                            </td>
                                        )}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Add Product Modal */}
            {showModal && (
                <div className="modal-backdrop">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h2 className="modal-title">Add Product &amp; Class Mapping</h2>
                            <button
                                className="btn btn-ghost btn-sm"
                                onClick={() => setShowModal(false)}
                                style={{ padding: 4 }}
                            >
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleCreate}>
                            <div className="modal-body">
                                <div className="form-group">
                                    <label className="form-label">Product Name</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="e.g. Mineral Water Bottle (500ml)"
                                        value={newProd.name}
                                        onChange={(e) => setNewProd({ ...newProd, name: e.target.value })}
                                        required
                                    />
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                    <div className="form-group">
                                        <label className="form-label">Category</label>
                                        <select
                                            className="form-select"
                                            value={newProd.category}
                                            onChange={(e) => setNewProd({ ...newProd, category: e.target.value })}
                                        >
                                            <option value="Fruits">Fruits</option>
                                            <option value="Vegetables">Vegetables</option>
                                            <option value="Dairy">Dairy</option>
                                            <option value="Bakery">Bakery</option>
                                            <option value="Beverages">Beverages</option>
                                            <option value="Snacks">Snacks</option>
                                            <option value="General">General</option>
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Shelf Zone</label>
                                        <select
                                            className="form-select"
                                            value={newProd.shelf_id || ""}
                                            onChange={(e) => setNewProd({ ...newProd, shelf_id: e.target.value ? parseInt(e.target.value) : null })}
                                        >
                                            <option value="">None (Unassigned)</option>
                                            {shelves.map(s => (
                                                <option key={s.id} value={s.id}>{s.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                                    <div className="form-group">
                                        <label className="form-label">Initial Stock</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={newProd.stock}
                                            onChange={(e) => setNewProd({ ...newProd, stock: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Threshold</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={newProd.threshold}
                                            onChange={(e) => setNewProd({ ...newProd, threshold: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Price (₹)</label>
                                        <input
                                            type="number"
                                            step="0.5"
                                            className="form-input"
                                            value={newProd.price}
                                            onChange={(e) => setNewProd({ ...newProd, price: parseFloat(e.target.value) })}
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">YOLO Class ID (Neural Mapping)</label>
                                    <input
                                        type="number"
                                        className="form-input"
                                        value={newProd.class_id ?? 0}
                                        onChange={(e) => setNewProd({ ...newProd, class_id: parseInt(e.target.value) })}
                                    />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn btn-primary">
                                    Register Product
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Products;
