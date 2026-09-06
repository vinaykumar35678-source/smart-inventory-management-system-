import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
    LayoutDashboard,
    Video,
    Package,
    Layers,
    Camera,
    BarChart3,
    Bell,
    ListFilter,
    Cpu,
    ShoppingBag,
    Activity,
    Users,
    Settings,
    LogOut,
    Boxes
} from "lucide-react";

function Navbar() {
    const { user, logout } = useAuth();

    const mainItems = [
        { path: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "user"] },
        { path: "/live", label: "Live Vision", icon: Video, roles: ["admin", "user"] },
        { path: "/inventory", label: "Inventory", icon: Package, roles: ["admin", "user"] },
        { path: "/shelves", label: "Shelves & ROI", icon: Layers, roles: ["admin", "user"] },
        { path: "/cameras", label: "Cameras", icon: Camera, roles: ["admin", "user"] },
        { path: "/analytics", label: "Analytics", icon: BarChart3, roles: ["admin", "user"] },
        { path: "/alerts", label: "Alerts", icon: Bell, roles: ["admin", "user"] },
        { path: "/events", label: "Events Log", icon: ListFilter, roles: ["admin", "user"] },
    ].filter((item) => item.roles.includes(user?.role || "user"));

    const adminItems = [
        { path: "/products", label: "Products", icon: ShoppingBag, roles: ["admin", "user"] },
        { path: "/aimodel", label: "AI Diagnostics", icon: Activity, roles: ["admin", "user"] },
        { path: "/training", label: "Model Training", icon: Cpu, roles: ["admin", "user"] },
        { path: "/users", label: "Users", icon: Users, roles: ["admin"] },
        { path: "/settings", label: "Settings", icon: Settings, roles: ["admin", "user"] },
    ].filter((item) => item.roles.includes(user?.role || "user"));

    const getInitials = (name) => {
        if (!name) return "U";
        return name.slice(0, 2).toUpperCase();
    };

    return (
        <aside style={{
            width: "var(--sidebar-w)",
            height: "100vh",
            background: "var(--surface-bg)",
            borderRight: "1px solid var(--border-color)",
            display: "flex",
            flexDirection: "column",
            flexShrink: 0,
            zIndex: 10,
        }}>
            {/* Brand Header */}
            <div style={{
                padding: "24px 20px 18px",
                borderBottom: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                gap: 12,
            }}>
                <div style={{
                    width: 38,
                    height: 38,
                    borderRadius: "var(--radius-md)",
                    background: "var(--primary-subtle)",
                    color: "var(--primary)",
                    border: "1px solid var(--primary-border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                }}>
                    <Boxes size={20} />
                </div>
                <div>
                    <h1 style={{
                        fontSize: "1.05rem",
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        letterSpacing: "-0.02em",
                        margin: 0,
                        lineHeight: 1.2,
                    }}>
                        SmartShelf
                    </h1>
                    <p style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        margin: 0,
                        fontWeight: 500,
                    }}>
                        Vision AI Inventory
                    </p>
                </div>
            </div>

            {/* Navigation Lists */}
            <nav style={{
                padding: "16px 12px",
                flex: 1,
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: 2,
            }}>
                <div style={{
                    fontSize: "0.6875rem",
                    fontWeight: 700,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    padding: "8px 10px 6px",
                }}>
                    Main
                </div>

                {mainItems.map((item) => {
                    const Icon = item.icon;
                    return (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === "/"}
                            style={({ isActive }) => ({
                                display: "flex",
                                alignItems: "center",
                                gap: 10,
                                padding: "9px 12px",
                                borderRadius: "var(--radius-md)",
                                textDecoration: "none",
                                fontSize: "0.875rem",
                                fontWeight: isActive ? 600 : 500,
                                color: isActive ? "var(--primary)" : "var(--text-secondary)",
                                background: isActive ? "var(--primary-subtle)" : "transparent",
                                transition: "all 0.15s ease",
                            })}
                        >
                            <Icon size={18} strokeWidth={2} />
                            <span>{item.label}</span>
                        </NavLink>
                    );
                })}

                {adminItems.length > 0 && (
                    <>
                        <div style={{
                            fontSize: "0.6875rem",
                            fontWeight: 700,
                            color: "var(--text-muted)",
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                            padding: "16px 10px 6px",
                        }}>
                            Administration
                        </div>

                        {adminItems.map((item) => {
                            const Icon = item.icon;
                            return (
                                <NavLink
                                    key={item.path}
                                    to={item.path}
                                    end={item.path === "/"}
                                    style={({ isActive }) => ({
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 10,
                                        padding: "9px 12px",
                                        borderRadius: "var(--radius-md)",
                                        textDecoration: "none",
                                        fontSize: "0.875rem",
                                        fontWeight: isActive ? 600 : 500,
                                        color: isActive ? "var(--primary)" : "var(--text-secondary)",
                                        background: isActive ? "var(--primary-subtle)" : "transparent",
                                        transition: "all 0.15s ease",
                                    })}
                                >
                                    <Icon size={18} strokeWidth={2} />
                                    <span>{item.label}</span>
                                </NavLink>
                            );
                        })}
                    </>
                )}
            </nav>

            {/* User & Logout Footer */}
            <div style={{
                padding: "16px",
                borderTop: "1px solid var(--border-subtle)",
                background: "var(--surface-bg)",
                display: "flex",
                flexDirection: "column",
                gap: 12,
            }}>
                <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "4px 6px",
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div style={{
                            width: 32,
                            height: 32,
                            borderRadius: "var(--radius-full)",
                            background: "var(--surface-subtle)",
                            border: "1px solid var(--border-color)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            color: "var(--text-secondary)",
                        }}>
                            {getInitials(user?.username)}
                        </div>
                        <div style={{ overflow: "hidden" }}>
                            <div style={{
                                fontSize: "0.8125rem",
                                fontWeight: 600,
                                color: "var(--text-primary)",
                                whiteSpace: "nowrap",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                maxWidth: 105,
                            }}>
                                {user?.username || "User"}
                            </div>
                            <span className="badge badge-gray" style={{ fontSize: "0.6875rem", padding: "1px 6px" }}>
                                {user?.role || "Staff"}
                            </span>
                        </div>
                    </div>

                    <button
                        onClick={logout}
                        title="Sign Out"
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            width: 32,
                            height: 32,
                            borderRadius: "var(--radius-md)",
                            color: "var(--text-secondary)",
                            background: "transparent",
                            border: "1px solid var(--border-color)",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                        }}
                        onMouseOver={(e) => {
                            e.currentTarget.style.background = "var(--danger-subtle)";
                            e.currentTarget.style.color = "var(--danger)";
                            e.currentTarget.style.borderColor = "var(--danger-border)";
                        }}
                        onMouseOut={(e) => {
                            e.currentTarget.style.background = "transparent";
                            e.currentTarget.style.color = "var(--text-secondary)";
                            e.currentTarget.style.borderColor = "var(--border-color)";
                        }}
                    >
                        <LogOut size={16} />
                    </button>
                </div>
            </div>
        </aside>
    );
}

export default Navbar;
