import React, { useState, useEffect, useMemo, useCallback } from "react";
import { apiService } from '../services/apiService';
import { useAuth } from '../contexts/AuthContext';

const randomInt = (min, max) =>
  Math.floor(Math.random() * (max - min + 1)) + min;

const randomId = () => String(randomInt(100000, 999999));
const randomUid = () =>
  Math.random().toString(36).substring(2, 8).toUpperCase();
const randomExOrderId = () => String(randomInt(100000000, 999999999));

const enrichOrder = (o) => {
  const isSD = o.symbol.includes(" SD ");
  const price = o.price;
  let leg1Price = price;
  let leg2Price = "-";
  const nowDate = new Date();
  const defaultDateTime = `${nowDate.toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Asia/Kolkata" })} ${nowDate.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" })}`;

  if (isSD) {
    // mock CE/PE prices around given price
    leg1Price = (price + 5).toFixed(2); // CE
    leg2Price = (price - 5).toFixed(2); // PE
  }

  return {
    ...o,
    orderId: o.orderId ?? randomId(),
    uniqueId: o.uniqueId ?? randomUid(),
    exchangeOrderId: o.exchangeOrderId ?? randomExOrderId(),
    triggerPrice: o.triggerPrice ?? 0,
    target: o.target ?? 0,
    stopLoss: o.stopLoss ?? 0,
    executedQty: o.executedQty ?? o.qty,
    executionPrice: o.executionPrice ?? o.price,
    orderDateTime: o.orderDateTime ?? defaultDateTime,
    exchangeTime: o.exchangeTime ?? defaultDateTime,
    executionTime: o.executionTime ?? defaultDateTime,
    leg1Price,
    leg2Price,
  };
};

// ------- Orders Tab -------
const OrdersTab = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [sortConfig, setSortConfig] = useState({
    key: "time",
    direction: "asc",
  });
  const [selectedOrderId, setSelectedOrderId] = useState(null);

  const formatTime = useCallback((isoLike) => {
    const date = new Date(isoLike || new Date().toISOString());
    return date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" });
  }, []);

  const formatDateTime = useCallback((isoLike) => {
    const date = new Date(isoLike || new Date().toISOString());
    return `${date.toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Asia/Kolkata" })} ${date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" })}`;
  }, []);

  const mapOrder = useCallback((order) => {
    const createdAt = order.created_at || order.createdAt || order.updated_at || new Date().toISOString();
    const updatedAt = order.updated_at || order.updatedAt || createdAt;
    const qty = Number(order.quantity ?? order.qty ?? 0);
    const executedQty = Number(order.filled_qty ?? order.executedQty ?? qty);
    const pendingQty = Math.max(0, qty - executedQty);
    const executionPrice = Number(order.execution_price ?? order.executionPrice ?? order.avg_execution_price ?? order.price ?? 0);
    const displayPrice = Number(order.price ?? executionPrice ?? 0);
    const statusRaw = String(order.status || 'PENDING');
    const status = statusRaw.toUpperCase();
    return enrichOrder({
      id: order.id ?? randomId(),
      time: formatTime(createdAt),
      exTime: formatTime(updatedAt),
      side: String(order.transaction_type || order.side || 'BUY').toUpperCase(),
      symbol: order.symbol || 'UNKNOWN',
      orderMode: order.order_type || order.orderMode || 'MARKET',
      productType: order.product_type || order.productType || 'MIS',
      qty,
      price: displayPrice,
      status,
      rejectionReason: order.remarks || order.rejection_reason || order.reason || '',
      triggerPrice: order.trigger_price ?? order.triggerPrice ?? 0,
      target: order.target_price ?? order.target ?? 0,
      stopLoss: order.stop_loss_price ?? order.stopLoss ?? 0,
      executedQty,
      pendingQty,
      executionPrice,
      orderDateTime: formatDateTime(createdAt),
      exchangeTime: formatDateTime(updatedAt),
      executionTime: formatDateTime(updatedAt)
    });
  }, [formatDateTime, formatTime]);

  const fetchOrders = useCallback(async () => {
    try {
      const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN';
      const params = !isAdmin && user?.id ? { user_id: user.id } : {};
      const response = await apiService.get('/trading/orders', params);
      if (response && response.data) {
        setOrders(response.data.map(mapOrder));
      } else {
        setOrders([]);
      }
    } catch (err) {
      console.error('Error fetching orders:', err);
    }
  }, [user, mapOrder]);

  // Fetch orders from API
  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  useEffect(() => {
    const handleOrdersUpdated = () => fetchOrders();
    window.addEventListener('orders:updated', handleOrdersUpdated);
    return () => window.removeEventListener('orders:updated', handleOrdersUpdated);
  }, [fetchOrders]);

  // Manual refresh function
  const handleRefresh = () => {
    fetchOrders();
  };

  const sortedOrders = useMemo(() => {
    const data = [...orders];
    if (!sortConfig.key) return data;

    data.sort((a, b) => {
      const { key, direction } = sortConfig;
      let av = a[key];
      let bv = b[key];

      if (key === "qty" || key === "price") {
        av = Number(av);
        bv = Number(bv);
      } else {
        av = String(av).toUpperCase();
        bv = String(bv).toUpperCase();
      }

      if (av < bv) return direction === "asc" ? -1 : 1;
      if (av > bv) return direction === "asc" ? 1 : -1;
      return 0;
    });

    return data;
  }, [orders, sortConfig]);

  const onHeaderClick = (key) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        return { key, direction: prev.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "asc" };
    });
  };

  const handleRowClick = (id) => {
    // clicking another row switches details; clicking same row closes
    setSelectedOrderId((prev) => (prev === id ? null : id));
  };

  const selectedOrder =
    sortedOrders.find((o) => o.id === selectedOrderId) || null;

  // ------- styles -------
  const pageStyle = {
    minHeight: "100vh",
    margin: 0,
    padding: "24px",
    fontFamily:
      "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    backgroundColor: "#f3f4f6",
  };

  const layoutStyle = {
    maxWidth: "1200px",
    margin: "0 auto",
    display: "flex",
    gap: "16px",
  };

  const tableCardStyle = {
    flex: "2 1 0",
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    boxShadow: "0 10px 30px rgba(15,23,42,0.12)",
    padding: "24px 24px 32px 24px",
    border: "1px solid #e5e7eb",
  };

  const detailsCardStyle = {
    flex: "1 0 320px",
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    boxShadow: "0 10px 30px rgba(15,23,42,0.12)",
    padding: "18px 20px 20px 20px",
    border: "1px solid #e5e7eb",
    fontSize: "12px",
    color: "#111827",
    alignSelf: "flex-start",
    maxHeight: "600px",
    overflowY: "auto",
  };

  const headerRowStyle = {
    marginBottom: "16px",
    fontSize: "16px",
    fontWeight: 600,
    color: "#111827",
  };

  const tableOuterStyle = {
    borderRadius: "8px",
    border: "1px solid #e5e7eb",
    overflow: "hidden",
    backgroundColor: "#ffffff",
  };

  const tableStyle = {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "12px",
  };

  const theadStyle = {
    backgroundColor: "#f9fafb",
    borderBottom: "1px solid #e5e7eb",
  };

  const sortableHeader = (label, key, alignRight = false) => {
    const isActive = sortConfig.key === key;
    const arrow = sortConfig.direction === "asc" ? "\u25B2" : "\u25BC"; // ▲ / ▼
    const base = {
      padding: "10px 12px",
      textAlign: alignRight ? "right" : "left",
      fontWeight: 600,
      color: "#6b7280",
      whiteSpace: "nowrap",
      cursor: "pointer",
      userSelect: "none",
    };
    return (
      <th key={key} style={base} onClick={() => onHeaderClick(key)}>
        <span>
          {label}
          {isActive && (
            <span style={{ marginLeft: 4, fontSize: "10px" }}>{arrow}</span>
          )}
        </span>
      </th>
    );
  };

  const rowStyle = {
    borderBottom: "1px solid #e5e7eb",
    backgroundColor: "#ffffff",
    cursor: "pointer",
  };

  const rowSelectedStyle = {
    ...rowStyle,
    backgroundColor: "#eff6ff",
  };

  const tdStyle = {
    padding: "10px 12px",
    color: "#111827",
    verticalAlign: "middle",
    whiteSpace: "nowrap",
  };

  const tdRight = { ...tdStyle, textAlign: "right" };

  const sideBadge = (side) => {
    const base = {
      padding: "4px 12px",
      borderRadius: "999px",
      fontSize: "11px",
      fontWeight: 700,
      color: "#ffffff",
      display: "inline-block",
    };
    const bg =
      side === "BUY"
        ? "linear-gradient(90deg, #3b82f6, #2563eb)"
        : "linear-gradient(90deg, #fb923c, #f97316)";
    return <span style={{ ...base, backgroundImage: bg }}>{side}</span>;
  };

  const orderTypeBadge = () => ({
    borderRadius: "999px",
    padding: "2px 10px",
    fontSize: "10px",
    fontWeight: 600,
    border: "1px solid #d1d5db",
    color: "#4b5563",
    backgroundColor: "#f3f4f6",
    marginLeft: 8,
    display: "inline-block",
  });

  const statusStyle = (status) => {
    const base = { fontWeight: 600 };
    const normalized = String(status || '').toUpperCase();
    if (normalized === "EXECUTED") return { ...base, color: "#16a34a" };
    if (normalized === "PARTIAL") return { ...base, color: "#d97706" };
    if (normalized === "REJECTED") return { ...base, color: "#dc2626" };
    return { ...base, color: "#111827" }; // Pending/others
  };

  const detailsHeaderStyle = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "12px",
  };

  const tickCircleStyle = {
    width: 26,
    height: 26,
    borderRadius: "999px",
    border: "2px solid #16a34a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#16a34a",
    fontSize: "16px",
  };

  const detailRowStyle = {
    display: "flex",
    justifyContent: "space-between",
    padding: "6px 0",
    borderBottom: "1px solid #e5e7eb",
  };

  const detailLabelStyle = {
    fontSize: "11px",
    color: "#6b7280",
  };

  const detailValueStyle = {
    fontSize: "12px",
    fontWeight: 500,
    color: "#111827",
  };

  const closeButtonStyle = {
    marginTop: "16px",
    width: "100%",
    padding: "8px 0",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    backgroundColor: "#f3f4f6",
    fontSize: "12px",
    fontWeight: 600,
    cursor: "pointer",
  };

  // ------- helpers -------
  const renderDetailsRow = (label, value) => (
    <div style={detailRowStyle}>
      <div style={detailLabelStyle}>{label}</div>
      <div style={detailValueStyle}>{value}</div>
    </div>
  );

  // ------- render -------
  return (
    <div style={pageStyle}>
      <div style={layoutStyle}>
        {/* Left: Orders table */}
        <div style={tableCardStyle}>
          <div style={{...headerRowStyle, display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
            <span>Executed Order ({orders.length})</span>
            <button
              onClick={handleRefresh}
              style={{
                background: 'none',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                padding: '4px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Refresh orders"
            >
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
          <div style={tableOuterStyle}>
            <table style={tableStyle}>
              <thead style={theadStyle}>
                <tr>
                  {sortableHeader("Time", "time")}
                  {sortableHeader("Ex. Time", "exTime")}
                  {sortableHeader("Type", "side")}
                  {sortableHeader("Symbol", "symbol")}
                  {sortableHeader("Order Type", "orderMode")}
                  {sortableHeader("Qty", "qty", true)}
                  {sortableHeader("Price", "price", true)}
                  {sortableHeader("Status", "status")}
                </tr>
              </thead>
              <tbody>
                {sortedOrders.map((o) => (
                  <tr
                    key={o.id}
                    style={
                      selectedOrderId === o.id ? rowSelectedStyle : rowStyle
                    }
                    onClick={() => handleRowClick(o.id)}
                  >
                    <td style={tdStyle}>{o.time}</td>
                    <td style={tdStyle}>{o.exTime}</td>
                    <td style={tdStyle}>{sideBadge(o.side)}</td>
                    <td style={tdStyle}>{o.symbol}</td>
                    <td style={tdStyle}>
                      <span>{o.orderMode}</span>
                      <span style={orderTypeBadge(o.productType)}>
                        {o.productType}
                      </span>
                    </td>
                    <td style={tdRight}>
                      {o.status === 'PARTIAL'
                        ? `${o.executedQty.toLocaleString("en-IN")} / ${o.qty.toLocaleString("en-IN")}`
                        : o.qty.toLocaleString("en-IN")}
                    </td>
                    <td style={tdRight}>{o.price.toFixed(2)}</td>
                    <td style={tdStyle}>
                      <span style={statusStyle(o.status)}>
                        {o.status === 'PARTIAL' && o.pendingQty > 0 ? `PARTIAL (PENDING ${o.pendingQty})` : o.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {sortedOrders.length === 0 && (
                  <tr>
                    <td style={tdStyle} colSpan={8}>
                      No orders yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Details panel */}
        {selectedOrder && (
          <div style={detailsCardStyle}>
            <div style={detailsHeaderStyle}>
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  color: "#111827",
                }}
              >
                {selectedOrder.symbol.split(" 14")[0]}
              </div>
              <div style={tickCircleStyle}>
                <span>✔</span>
              </div>
            </div>

            {renderDetailsRow("Product", selectedOrder.productType)}
            {renderDetailsRow("Rate Type", selectedOrder.orderMode)}
            {renderDetailsRow(
              "Operation Type",
              selectedOrder.side === "BUY" ? "Buy" : "Sell"
            )}
            {renderDetailsRow("Input Price", selectedOrder.price.toFixed(2))}
            {renderDetailsRow(
              "Trigger Price",
              selectedOrder.triggerPrice.toFixed
                ? selectedOrder.triggerPrice.toFixed(2)
                : selectedOrder.triggerPrice
            )}
            {renderDetailsRow(
              "Target",
              selectedOrder.target.toFixed
                ? selectedOrder.target.toFixed(2)
                : selectedOrder.target
            )}
            {renderDetailsRow(
              "Stop Loss",
              selectedOrder.stopLoss.toFixed
                ? selectedOrder.stopLoss.toFixed(2)
                : selectedOrder.stopLoss
            )}
            {renderDetailsRow(
              "Quantity",
              selectedOrder.qty.toLocaleString("en-IN")
            )}
            {renderDetailsRow("Order Status", selectedOrder.status)}
            {selectedOrder.status === "REJECTED" && selectedOrder.rejectionReason && (
              renderDetailsRow("Rejection Reason", selectedOrder.rejectionReason)
            )}
            {renderDetailsRow(
              "Executed Quantity",
              selectedOrder.executedQty.toLocaleString("en-IN")
            )}
            {renderDetailsRow(
              "Pending Quantity",
              Number(selectedOrder.pendingQty || 0).toLocaleString("en-IN")
            )}
            {renderDetailsRow(
              "Execution Price",
              selectedOrder.executionPrice.toFixed(2)
            )}
            {renderDetailsRow("Order Time", selectedOrder.orderDateTime)}
            {renderDetailsRow("Exchange Time", selectedOrder.exchangeTime)}
            {renderDetailsRow("Execution Time", selectedOrder.executionTime)}
            {renderDetailsRow("Order Id", selectedOrder.orderId)}
            {renderDetailsRow("Unique Identifier", selectedOrder.uniqueId)}
            {renderDetailsRow(
              "Exchange Order Id",
              selectedOrder.exchangeOrderId
            )}
            {renderDetailsRow("Leg 1", selectedOrder.leg1Price)}
            {renderDetailsRow("Leg 2", selectedOrder.leg2Price)}

            <button
              style={closeButtonStyle}
              onClick={() => setSelectedOrderId(null)}
            >
              CLOSE
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrdersTab;
