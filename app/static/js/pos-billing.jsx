import React, { useState, useMemo, useRef, useEffect } from "react";
import {
  ShoppingCart,
  Search,
  Barcode,
  Plus,
  Minus,
  Trash2,
  Printer,
  X,
  Receipt,
  Package,
  LayoutDashboard,
  Tags,
  Truck,
  Users,
  FileText,
  TrendingUp,
  LogOut,
  ShoppingBag,
  CircleCheck,
} from "lucide-react";

const PRODUCTS = [
  { id: "P001", name: "Sparkling Soda 330ml", barcode: "8901030875021", price: 45, stock: 120, category: "Beverages", emoji: "🥤" },
  { id: "P002", name: "Basmati Rice 5kg", barcode: "8901030875022", price: 540, stock: 34, category: "Grocery", emoji: "🌾" },
  { id: "P003", name: "Toor Dal 1kg", barcode: "8901030875023", price: 130, stock: 8, category: "Grocery", emoji: "🫘" },
  { id: "P004", name: "Amul Butter 500g", barcode: "8901030875024", price: 275, stock: 60, category: "Dairy", emoji: "🧈" },
  { id: "P005", name: "Colgate Toothpaste", barcode: "8901030875025", price: 55, stock: 5, category: "Personal Care", emoji: "🪥" },
  { id: "P006", name: "Sunflower Oil 1L", barcode: "8901030875026", price: 165, stock: 42, category: "Grocery", emoji: "🛢️" },
  { id: "P007", name: "Whole Wheat Bread", barcode: "8901030875027", price: 40, stock: 25, category: "Bakery", emoji: "🍞" },
  { id: "P008", name: "Britannia Biscuits", barcode: "8901030875028", price: 30, stock: 90, category: "Snacks", emoji: "🍪" },
];

const TAX_RATE = 0.05; // 5% GST

const NAV_ITEMS = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Products", icon: Package },
  { label: "Categories", icon: Tags },
  { label: "Suppliers", icon: Truck },
  { label: "Customers", icon: Users },
  { label: "Billing (POS)", icon: Receipt, active: true },
  { label: "Sales", icon: TrendingUp },
  { label: "Purchase", icon: ShoppingBag },
];

function currency(n) {
  return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function POSBilling() {
  const [query, setQuery] = useState("");
  const [cart, setCart] = useState([]); // {id, qty}
  const [discountPct, setDiscountPct] = useState(0);
  const [showInvoice, setShowInvoice] = useState(false);
  const [invoice, setInvoice] = useState(null);
  const [toast, setToast] = useState("");
  const searchRef = useRef(null);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 1600);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return PRODUCTS;
    return PRODUCTS.filter(
      (p) => p.name.toLowerCase().includes(q) || p.barcode.includes(q)
    );
  }, [query]);

  const cartLines = useMemo(
    () =>
      cart.map((c) => {
        const p = PRODUCTS.find((p) => p.id === c.id);
        return { ...p, qty: c.qty, lineTotal: p.price * c.qty };
      }),
    [cart]
  );

  const subtotal = cartLines.reduce((sum, l) => sum + l.lineTotal, 0);
  const discountAmt = (subtotal * discountPct) / 100;
  const taxable = subtotal - discountAmt;
  const taxAmt = taxable * TAX_RATE;
  const grandTotal = taxable + taxAmt;

  function addToCart(product) {
    if (product.stock <= 0) return;
    setCart((prev) => {
      const existing = prev.find((c) => c.id === product.id);
      if (existing) {
        if (existing.qty >= product.stock) return prev;
        return prev.map((c) => (c.id === product.id ? { ...c, qty: c.qty + 1 } : c));
      }
      return [...prev, { id: product.id, qty: 1 }];
    });
    setToast(`Added ${product.name}`);
  }

  function changeQty(id, delta) {
    setCart((prev) =>
      prev
        .map((c) => {
          if (c.id !== id) return c;
          const product = PRODUCTS.find((p) => p.id === id);
          const newQty = Math.min(product.stock, Math.max(0, c.qty + delta));
          return { ...c, qty: newQty };
        })
        .filter((c) => c.qty > 0)
    );
  }

  function removeLine(id) {
    setCart((prev) => prev.filter((c) => c.id !== id));
  }

  function handleBarcodeEnter(e) {
    if (e.key === "Enter") {
      const match = PRODUCTS.find((p) => p.barcode === query.trim());
      if (match) {
        addToCart(match);
        setQuery("");
      }
    }
  }

  function generateBill() {
    if (cartLines.length === 0) return;
    const now = new Date();
    setInvoice({
      id: "INV-" + now.getTime().toString().slice(-8),
      date: now.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }),
      time: now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
      lines: cartLines,
      subtotal,
      discountPct,
      discountAmt,
      taxAmt,
      grandTotal,
    });
    setShowInvoice(true);
  }

  function startNewBill() {
    setCart([]);
    setDiscountPct(0);
    setShowInvoice(false);
    setInvoice(null);
  }

  return (
    <div style={{ display: "flex", minHeight: "700px", fontFamily: "'Inter', system-ui, sans-serif", background: "#F3F4F8" }}>
      {/* Sidebar */}
      <div style={{ width: "220px", background: "#0B1224", display: "flex", flexDirection: "column", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "22px 20px", color: "white", fontWeight: 700, fontSize: "18px" }}>
          <ShoppingCart size={20} />
          SuperMart
        </div>
        <div style={{ padding: "8px 12px", display: "flex", flexDirection: "column", gap: "4px" }}>
          {NAV_ITEMS.map((item) => (
            <div
              key={item.label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 12px",
                borderRadius: "10px",
                fontSize: "14px",
                fontWeight: item.active ? 600 : 500,
                color: item.active ? "white" : "#8B92A8",
                background: item.active ? "linear-gradient(135deg, #3B5BDB, #5B7CFA)" : "transparent",
                cursor: "pointer",
              }}
            >
              <item.icon size={17} />
              {item.label}
            </div>
          ))}
        </div>
        <div style={{ marginTop: "auto", padding: "16px 20px", display: "flex", alignItems: "center", gap: "10px", color: "#E45C5C", fontSize: "14px", fontWeight: 500, cursor: "pointer" }}>
          <LogOut size={16} />
          Logout
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, padding: "24px 28px", display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 700, color: "#111827" }}>Billing (POS)</h1>
            <p style={{ margin: "2px 0 0", fontSize: "13px", color: "#8B92A8" }}>Search products, build the cart, and generate the bill.</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#111827" }}>admin</div>
              <div style={{ fontSize: "11px", color: "#8B92A8" }}>ADMIN</div>
            </div>
            <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "#3B5BDB", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>A</div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "20px", flex: 1, minHeight: 0 }}>
          {/* Product search + grid */}
          <div style={{ flex: "1.4", display: "flex", flexDirection: "column", minWidth: 0 }}>
            <div style={{ position: "relative", marginBottom: "16px" }}>
              <Search size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "#8B92A8" }} />
              <input
                ref={searchRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleBarcodeEnter}
                placeholder="Search by product name or scan barcode..."
                style={{
                  width: "100%",
                  padding: "12px 14px 12px 40px",
                  borderRadius: "10px",
                  border: "1px solid #E5E7EB",
                  fontSize: "14px",
                  outline: "none",
                  boxSizing: "border-box",
                  background: "white",
                }}
              />
              <Barcode size={16} style={{ position: "absolute", right: "14px", top: "50%", transform: "translateY(-50%)", color: "#C7CBD6" }} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "12px", overflowY: "auto", paddingRight: "4px" }}>
              {filtered.length === 0 && (
                <div style={{ gridColumn: "1 / -1", textAlign: "center", padding: "40px 0", color: "#8B92A8", fontSize: "14px" }}>
                  No products match "{query}"
                </div>
              )}
              {filtered.map((p) => {
                const inCart = cart.find((c) => c.id === p.id);
                const lowStock = p.stock <= 10;
                const outOfStock = p.stock <= 0;
                return (
                  <div
                    key={p.id}
                    onClick={() => addToCart(p)}
                    style={{
                      background: "white",
                      borderRadius: "12px",
                      border: inCart ? "1.5px solid #3B5BDB" : "1px solid #EEF0F4",
                      padding: "14px",
                      cursor: outOfStock ? "not-allowed" : "pointer",
                      opacity: outOfStock ? 0.5 : 1,
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                      transition: "border 0.15s",
                    }}
                  >
                    <div style={{ fontSize: "26px" }}>{p.emoji}</div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#111827", lineHeight: 1.3 }}>{p.name}</div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#3B5BDB" }}>{currency(p.price)}</div>
                    <div style={{ fontSize: "11px", color: lowStock ? "#D9463A" : "#8B92A8" }}>
                      {outOfStock ? "Out of stock" : `Stock: ${p.stock}`}
                    </div>
                    {inCart && (
                      <div style={{ fontSize: "11px", fontWeight: 600, color: "#3B5BDB" }}>In cart: {inCart.qty}</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Cart panel */}
          <div style={{ flex: "1", display: "flex", flexDirection: "column", background: "white", borderRadius: "14px", border: "1px solid #EEF0F4", overflow: "hidden", minWidth: "320px" }}>
            <div style={{ padding: "16px 18px", borderBottom: "1px solid #EEF0F4", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "15px", color: "#111827" }}>
                <ShoppingCart size={17} /> Cart
              </div>
              <div style={{ fontSize: "12px", color: "#8B92A8" }}>{cartLines.length} item{cartLines.length !== 1 ? "s" : ""}</div>
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: "10px 14px" }}>
              {cartLines.length === 0 ? (
                <div style={{ textAlign: "center", color: "#B4B8C4", fontSize: "13px", padding: "40px 10px" }}>
                  Cart is empty. Click a product to add it.
                </div>
              ) : (
                cartLines.map((l) => (
                  <div key={l.id} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 0", borderBottom: "1px solid #F3F4F8" }}>
                    <div style={{ fontSize: "18px" }}>{l.emoji}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#111827", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{l.name}</div>
                      <div style={{ fontSize: "11px", color: "#8B92A8" }}>{currency(l.price)} each</div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <button onClick={() => changeQty(l.id, -1)} style={qtyBtnStyle}><Minus size={12} /></button>
                      <span style={{ fontSize: "13px", fontWeight: 600, width: "18px", textAlign: "center" }}>{l.qty}</span>
                      <button onClick={() => changeQty(l.id, 1)} style={qtyBtnStyle}><Plus size={12} /></button>
                    </div>
                    <div style={{ fontSize: "13px", fontWeight: 700, width: "70px", textAlign: "right", color: "#111827" }}>{currency(l.lineTotal)}</div>
                    <button onClick={() => removeLine(l.id)} style={{ background: "none", border: "none", cursor: "pointer", color: "#D9463A", padding: "4px" }}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>

            <div style={{ padding: "16px 18px", borderTop: "1px solid #EEF0F4", background: "#FAFBFC" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "12.5px", color: "#8B92A8" }}>Discount</span>
                <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={discountPct}
                    onChange={(e) => setDiscountPct(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
                    style={{ width: "50px", padding: "4px 6px", borderRadius: "6px", border: "1px solid #E5E7EB", fontSize: "12.5px", textAlign: "right" }}
                  />
                  <span style={{ fontSize: "12.5px", color: "#8B92A8" }}>%</span>
                </div>
              </div>
              <SummaryRow label="Subtotal" value={currency(subtotal)} />
              <SummaryRow label={`Discount (${discountPct}%)`} value={"- " + currency(discountAmt)} muted />
              <SummaryRow label={`GST (${(TAX_RATE * 100).toFixed(0)}%)`} value={"+ " + currency(taxAmt)} muted />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "10px", paddingTop: "10px", borderTop: "1px dashed #E5E7EB" }}>
                <span style={{ fontSize: "14px", fontWeight: 700, color: "#111827" }}>Total</span>
                <span style={{ fontSize: "19px", fontWeight: 800, color: "#3B5BDB" }}>{currency(grandTotal)}</span>
              </div>

              <button
                onClick={generateBill}
                disabled={cartLines.length === 0}
                style={{
                  width: "100%",
                  marginTop: "14px",
                  padding: "12px",
                  borderRadius: "10px",
                  border: "none",
                  background: cartLines.length === 0 ? "#C7CBD6" : "linear-gradient(135deg, #3B5BDB, #5B7CFA)",
                  color: "white",
                  fontWeight: 700,
                  fontSize: "14px",
                  cursor: cartLines.length === 0 ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                }}
              >
                <Receipt size={16} /> Generate Bill
              </button>
            </div>
          </div>
        </div>
      </div>

      {toast && (
        <div style={{ position: "fixed", bottom: "24px", left: "50%", transform: "translateX(-50%)", background: "#111827", color: "white", padding: "10px 18px", borderRadius: "10px", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 6px 18px rgba(0,0,0,0.2)" }}>
          <CircleCheck size={15} color="#5BD98A" /> {toast}
        </div>
      )}

      {showInvoice && invoice && (
        <InvoiceModal invoice={invoice} onClose={() => setShowInvoice(false)} onNewBill={startNewBill} />
      )}
    </div>
  );
}

function SummaryRow({ label, value, muted }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
      <span style={{ fontSize: "12.5px", color: "#8B92A8" }}>{label}</span>
      <span style={{ fontSize: "12.5px", color: muted ? "#8B92A8" : "#111827", fontWeight: 500 }}>{value}</span>
    </div>
  );
}

const qtyBtnStyle = {
  width: "22px",
  height: "22px",
  borderRadius: "6px",
  border: "1px solid #E5E7EB",
  background: "white",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
};

function InvoiceModal({ invoice, onClose, onNewBill }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(15,18,30,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} className="pos-modal-overlay">
      <div style={{ background: "white", borderRadius: "16px", width: "380px", maxHeight: "88vh", overflow: "hidden", display: "flex", flexDirection: "column" }} className="pos-invoice">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", borderBottom: "1px solid #EEF0F4" }} className="pos-no-print">
          <div style={{ fontWeight: 700, fontSize: "15px", color: "#111827" }}>Invoice generated</div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#8B92A8" }}>
            <X size={18} />
          </button>
        </div>

        <div id="pos-invoice-print" style={{ padding: "22px 24px", overflowY: "auto" }}>
          <div style={{ textAlign: "center", marginBottom: "14px" }}>
            <div style={{ fontWeight: 800, fontSize: "17px", color: "#111827" }}>SuperMart</div>
            <div style={{ fontSize: "11px", color: "#8B92A8" }}>123 Market Street, Chennai · GSTIN: 33ABCDE1234F1Z5</div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", color: "#6B7280", marginBottom: "12px" }}>
            <span>{invoice.id}</span>
            <span>{invoice.date}, {invoice.time}</span>
          </div>
          <div style={{ borderTop: "1px dashed #D1D5DB", borderBottom: "1px dashed #D1D5DB", padding: "10px 0", marginBottom: "10px" }}>
            {invoice.lines.map((l) => (
              <div key={l.id} style={{ display: "flex", justifyContent: "space-between", fontSize: "12.5px", padding: "4px 0" }}>
                <span style={{ flex: 1 }}>{l.name} <span style={{ color: "#9CA3AF" }}>x{l.qty}</span></span>
                <span style={{ fontWeight: 600 }}>{currency(l.lineTotal)}</span>
              </div>
            ))}
          </div>
          <SummaryRow label="Subtotal" value={currency(invoice.subtotal)} />
          <SummaryRow label={`Discount (${invoice.discountPct}%)`} value={"- " + currency(invoice.discountAmt)} muted />
          <SummaryRow label="GST (5%)" value={"+ " + currency(invoice.taxAmt)} muted />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "10px", paddingTop: "10px", borderTop: "1px solid #111827" }}>
            <span style={{ fontWeight: 800, fontSize: "14.5px" }}>Total</span>
            <span style={{ fontWeight: 800, fontSize: "14.5px" }}>{currency(invoice.grandTotal)}</span>
          </div>
          <div style={{ textAlign: "center", fontSize: "11px", color: "#9CA3AF", marginTop: "18px" }}>Thank you for shopping with us!</div>
        </div>

        <div style={{ display: "flex", gap: "10px", padding: "16px 20px", borderTop: "1px solid #EEF0F4" }} className="pos-no-print">
          <button
            onClick={() => window.print()}
            style={{ flex: 1, padding: "11px", borderRadius: "10px", border: "none", background: "linear-gradient(135deg, #3B5BDB, #5B7CFA)", color: "white", fontWeight: 700, fontSize: "13.5px", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", cursor: "pointer" }}
          >
            <Printer size={15} /> Print bill
          </button>
          <button
            onClick={onNewBill}
            style={{ flex: 1, padding: "11px", borderRadius: "10px", border: "1px solid #E5E7EB", background: "white", color: "#111827", fontWeight: 700, fontSize: "13.5px", cursor: "pointer" }}
          >
            New bill
          </button>
        </div>
      </div>

      <style>{`
        @media print {
          body * { visibility: hidden; }
          #pos-invoice-print, #pos-invoice-print * { visibility: visible; }
          #pos-invoice-print { position: absolute; top: 0; left: 0; width: 100%; }
          .pos-no-print { display: none !important; }
        }
      `}</style>
    </div>
  );
}
