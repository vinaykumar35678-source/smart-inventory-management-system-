import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import LiveMonitor from "./pages/LiveMonitor";
import Shelves from "./pages/Shelves";
import Cameras from "./pages/Cameras";
import Analytics from "./pages/Analytics";
import AIModelStatus from "./pages/AIModelStatus";
import ModelTraining from "./pages/ModelTraining";
import Events from "./pages/Events";
import Products from "./pages/Products";
import Alerts from "./pages/Alerts";
import Settings from "./pages/Settings";
import AdminUsers from "./pages/AdminUsers";
import "./index.css";

import { Loader2 } from "lucide-react";

// ── Protected route wrapper ──────────────────────────────
function ProtectedRoute({ children, adminOnly = false }) {
    const { user, loading } = useAuth();
    if (loading) {
        return (
            <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--canvas-bg)" }}>
                <div style={{ textAlign: "center" }}>
                    <Loader2 className="animate-spin" size={32} style={{ color: "var(--primary)", margin: "0 auto" }} />
                    <p style={{ color: "var(--text-secondary)", marginTop: 12, fontSize: "0.875rem" }}>Loading system...</p>
                </div>
            </div>
        );
    }
    if (!user) return <Navigate to="/login" replace />;
    if (adminOnly && user.role !== "admin") return <Navigate to="/" replace />;
    return children;
}

// ── App inner (needs auth context) ───────────────────────
function AppInner() {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--canvas-bg)" }}>
                <Loader2 className="animate-spin" size={32} style={{ color: "var(--primary)" }} />
            </div>
        );
    }

    return (
        <Routes>
            <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
            <Route
                path="/*"
                element={
                    <ProtectedRoute>
                        <div className="app-layout">
                            <Navbar />
                            <main className="main-content">
                                <Routes>
                                    <Route path="/" element={<Dashboard />} />
                                    <Route path="/live" element={<LiveMonitor />} />
                                    <Route path="/inventory" element={<Inventory />} />
                                    <Route path="/shelves" element={<Shelves />} />
                                    <Route path="/cameras" element={<Cameras />} />
                                    <Route path="/analytics" element={<Analytics />} />
                                    <Route path="/aimodel" element={<AIModelStatus />} />
                                    <Route path="/training" element={<ModelTraining />} />
                                    <Route path="/events" element={<Events />} />
                                    <Route path="/products" element={<Products />} />
                                    <Route path="/alerts" element={<Alerts />} />
                                    <Route path="/settings" element={<Settings />} />
                                    <Route path="/users" element={
                                        <ProtectedRoute adminOnly>
                                            <AdminUsers />
                                        </ProtectedRoute>
                                    } />
                                    <Route path="*" element={<Navigate to="/" replace />} />
                                </Routes>
                            </main>
                        </div>
                    </ProtectedRoute>
                }
            />
        </Routes>
    );
}

function App() {
    return (
        <Router>
            <AuthProvider>
                <AppInner />
            </AuthProvider>
        </Router>
    );
}

export default App;
