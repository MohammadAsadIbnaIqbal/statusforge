"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  owner_id: number;
}

export default function Home() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [userData, setUserData] = useState<any>(null);
  
  // Product Form State
  const [products, setProducts] = useState<Product[]>([]);
  const [prodName, setProdName] = useState("");
  const [prodDesc, setProdDesc] = useState("");
  const [prodPrice, setProdPrice] = useState("");

  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [loading, setLoading] = useState(false);

  // Restore JWT token from localStorage on initial page load
  useEffect(() => {
    const savedToken = localStorage.getItem("asadpy_token");
    if (savedToken) {
      setToken(savedToken);
      fetchProfile(savedToken);
    }
    fetchProducts();
  }, []);

  // Fetch Products (Public)
  const fetchProducts = async () => {
    try {
      const data = await apiFetch("/products", { method: "GET" });
      setProducts(data);
    } catch (err: any) {
      console.error("Error fetching products:", err.message);
    }
  };

  // Fetch User Profile
  const fetchProfile = async (authToken: string) => {
    setLoading(true);
    try {
      const data = await apiFetch("/users/me", { method: "GET" }, authToken);
      setUserData(data);
    } catch (err: any) {
      handleLogout();
    } finally {
      setLoading(false);
    }
  };

  // Handle Login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const data = await apiFetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString(),
      });

      const newToken = data.access_token;
      setToken(newToken);
      localStorage.setItem("asadpy_token", newToken);
      setMessage({ text: "Authenticated successfully!", type: "success" });
      fetchProfile(newToken);
    } catch (err: any) {
      setMessage({ text: err.message, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  // Handle Register
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const data = await apiFetch("/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      });
      setMessage({ text: `Account created for ${data.username}! You can now log in.`, type: "success" });
    } catch (err: any) {
      setMessage({ text: err.message, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  // Handle Product Creation (Protected Route)
  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setMessage({ text: "You must be logged in to create a product.", type: "error" });
      return;
    }
    setLoading(true);
    try {
      await apiFetch(
        "/products",
        {
          method: "POST",
          body: JSON.stringify({
            name: prodName,
            description: prodDesc,
            price: parseFloat(prodPrice),
          }),
        },
        token
      );
      setMessage({ text: "Product added successfully!", type: "success" });
      setProdName("");
      setProdDesc("");
      setProdPrice("");
      fetchProducts();
    } catch (err: any) {
      setMessage({ text: err.message, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  // Handle Logout
  const handleLogout = () => {
    setToken(null);
    setUserData(null);
    localStorage.removeItem("asadpy_token");
    setMessage({ text: "Logged out successfully.", type: "success" });
  };

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-6 flex flex-col items-center">
      <div className="max-w-4xl w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-extrabold text-blue-400">AsadPy Store Dashboard</h1>
          <p className="mt-2 text-slate-400">Next.js Frontend connected to Live Render FastAPI Backend</p>
        </div>

        {message && (
          <div
            className={`p-4 rounded-lg font-medium ${
              message.type === "success"
                ? "bg-emerald-900/50 text-emerald-300 border border-emerald-500"
                : "bg-rose-900/50 text-rose-300 border border-rose-500"
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          {/* Left Column: Authentication */}
          {!token ? (
            <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 space-y-4">
              <h2 className="text-xl font-bold text-slate-200">Account Portal</h2>
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
                <input
                  type="email"
                  placeholder="Email (for registration)"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleRegister}
                  disabled={loading}
                  className="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-2 rounded-lg font-semibold transition"
                >
                  Register
                </button>
                <button
                  onClick={handleLogin}
                  disabled={loading}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-2 rounded-lg font-semibold transition"
                >
                  Log In
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 space-y-4 flex flex-col justify-between">
              <div>
                <h2 className="text-xl font-bold text-emerald-400">Active Session</h2>
                <p className="text-sm text-slate-300 mt-2">
                  Logged in as <span className="font-bold text-white">{userData?.username || "..."}</span>
                </p>
                {userData && (
                  <pre className="mt-4 p-3 bg-slate-950 text-emerald-400 text-xs rounded-lg overflow-x-auto">
                    {JSON.stringify(userData, null, 2)}
                  </pre>
                )}
              </div>
              <button
                onClick={handleLogout}
                className="w-full bg-rose-600 hover:bg-rose-500 text-white py-2 rounded-lg font-semibold transition"
              >
                Log Out
              </button>
            </div>
          )}

          {/* Right Column: Create Product Form */}
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 space-y-4">
            <h2 className="text-xl font-bold text-slate-200">Add New Product</h2>
            <form onSubmit={handleCreateProduct} className="space-y-3">
              <input
                type="text"
                placeholder="Product Name"
                value={prodName}
                onChange={(e) => setProdName(e.target.value)}
                required
                className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
              <input
                type="text"
                placeholder="Description"
                value={prodDesc}
                onChange={(e) => setProdDesc(e.target.value)}
                required
                className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
              <input
                type="number"
                step="0.01"
                placeholder="Price ($)"
                value={prodPrice}
                onChange={(e) => setProdPrice(e.target.value)}
                required
                className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={!token || loading}
                className="w-full bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 text-white py-2 rounded-lg font-semibold transition"
              >
                {token ? "Create Product" : "Log In to Add Product"}
              </button>
            </form>
          </div>
        </div>

        {/* Product Catalog Display */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 space-y-4">
          <h2 className="text-2xl font-bold text-blue-400">Store Catalog</h2>
          {products.length === 0 ? (
            <p className="text-slate-400 text-sm italic">No products available in the database.</p>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.map((item) => (
                <div key={item.id} className="bg-slate-900 p-4 rounded-lg border border-slate-700 space-y-2">
                  <h3 className="font-bold text-lg text-white">{item.name}</h3>
                  <p className="text-slate-400 text-sm">{item.description}</p>
                  <p className="text-emerald-400 font-extrabold text-xl">${item.price.toFixed(2)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}