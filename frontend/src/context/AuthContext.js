import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // On mount, restore session and verify against /api/auth/me
    useEffect(() => {
        let isMounted = true;

        async function verifySession() {
            const storedUser = localStorage.getItem("smartshelf_user");
            const token = localStorage.getItem("smartshelf_token");

            if (storedUser) {
                try {
                    setUser(JSON.parse(storedUser));
                } catch {
                    localStorage.removeItem("smartshelf_user");
                }
            }

            if (token) {
                api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
            }

            try {
                // Verify session with server (uses cookie or Bearer header)
                const res = await api.get("/auth/me");
                if (isMounted && res.data) {
                    const userData = {
                        username: res.data.username,
                        full_name: res.data.full_name,
                        role: res.data.role,
                        email: res.data.email,
                    };
                    setUser(userData);
                    localStorage.setItem("smartshelf_user", JSON.stringify(userData));
                }
            } catch {
                if (isMounted) {
                    // Session invalid or expired on server
                    localStorage.removeItem("smartshelf_token");
                    localStorage.removeItem("smartshelf_user");
                    delete api.defaults.headers.common["Authorization"];
                    setUser(null);
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        }

        verifySession();

        return () => {
            isMounted = false;
        };
    }, []);

    const login = (tokenData) => {
        if (tokenData.access_token) {
            localStorage.setItem("smartshelf_token", tokenData.access_token);
            api.defaults.headers.common["Authorization"] = `Bearer ${tokenData.access_token}`;
        }
        const userData = {
            username: tokenData.username,
            full_name: tokenData.full_name,
            role: tokenData.role,
        };
        localStorage.setItem("smartshelf_user", JSON.stringify(userData));
        setUser(userData);
    };

    const logout = async () => {
        try {
            // Call server to revoke JWT in database and clear HttpOnly cookie
            await api.post("/auth/logout");
        } catch (err) {
            // Even if network fails, continue with client-side cleanup
            console.error("[Logout notice]", err);
        } finally {
            localStorage.removeItem("smartshelf_token");
            localStorage.removeItem("smartshelf_user");
            delete api.defaults.headers.common["Authorization"];
            setUser(null);
        }
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading, isAdmin: user?.role === "admin" }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
