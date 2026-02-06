import React, { useState, useEffect, useCallback } from "react";
import { apiService } from '../services/apiService';

// ---------- Baskets Tab ----------
const BasketsTab = () => {
  const [baskets, setBaskets] = useState([]);
  const [user, setUser] = useState({ id: "admin-1", walletBalance: 250000 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      
      // Fetch baskets and user data in parallel
      const [basketsResponse, userResponse] = await Promise.all([
        apiService.get('/trading/basket-orders'),
        apiService.get('/admin/users') // Use FastAPI admin users endpoint
      ]);
      
      if (basketsResponse && basketsResponse.data) {
        setBaskets(basketsResponse.data);
      }
      
      if (userResponse && userResponse.data && userResponse.data.length > 0) {
        setUser(userResponse.data[0]); // Use first user for now
      }
      
    } catch (err) {
      console.error('Error fetching baskets data:', err);
      setError('Failed to load baskets');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch baskets and user data from API
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    const handleBasketsUpdated = () => fetchData();
    window.addEventListener('baskets:updated', handleBasketsUpdated);
    return () => window.removeEventListener('baskets:updated', handleBasketsUpdated);
  }, [fetchData]);

  // Manual refresh function
  const handleRefresh = () => {
    fetchData();
  };

  const handleExecute = async (basketId) => {
    try {
      const basket = baskets.find(b => b.id === basketId);
      if (!basket) {
        setError('Basket not found');
        return;
      }

      // Execute basket order via FastAPI
      const response = await apiService.post('/trading/basket-orders/execute', {
        basket_id: basketId,
        name: basket.name,
        orders: basket.legs.map(leg => ({
          security_id: leg.symbol,
          quantity: leg.qty,
          transaction_type: leg.side,
          order_type: 'LIMIT',
          product_type: leg.productType === 'NORMAL' ? 'DELIVERY' : 'INTRADAY',
          exchange: leg.exchange || 'NSE_EQ',
          price: leg.price
        }))
      });

      if (response) {
        setError('Basket order executed successfully!');
        setTimeout(() => setError(''), 3000);
      }
    } catch (err) {
      console.error('Error executing basket:', err);
      setError('Failed to execute basket order');
      setTimeout(() => setError(''), 3000);
    }
  };

  const handleDeleteBasket = async (basketId) => {
    try {
      // Delete basket via FastAPI
      await apiService.delete('/trading/basket-orders/' + basketId);
      
      // Update local state
      setBaskets((prev) => prev.filter((b) => b.id !== basketId));
      
      setError('Basket deleted successfully!');
      setTimeout(() => setError(''), 2000);
    } catch (err) {
      console.error('Error deleting basket:', err);
      setError('Failed to delete basket');
      setTimeout(() => setError(''), 2000);
    }
  };

  const handleDeleteLeg = (basketId, legId) => {
    setBaskets((prev) =>
      prev.map((b) =>
        b.id === basketId
          ? { ...b, legs: b.legs.filter((l) => l.id !== legId) }
          : b
      )
    );
  };

  // ---------- styles ----------
  const pageStyle = {
    minHeight: "100vh",
    margin: 0,
    padding: "24px",
    fontFamily:
      "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    backgroundColor: "#f3f4f6",
  };

  const mainCardStyle = {
    maxWidth: "1200px",
    margin: "0 auto",
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    boxShadow: "0 10px 30px rgba(15,23,42,0.12)",
    padding: "16px 16px 24px 16px",
    border: "1px solid #e5e7eb",
  };

  const basketWrapperStyle = {
    borderRadius: "10px",
    border: "1px solid #e5e7eb",
    marginTop: "8px",
    marginBottom: "12px",
    overflow: "hidden",
    backgroundColor: "#ffffff",
  };

  const basketHeaderStyle = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 14px",
    backgroundColor: "#f9fafb",
    borderBottom: "1px solid #e5e7eb",
  };

  const basketTitleStyle = {
    fontSize: "13px",
    fontWeight: 600,
    color: "#111827",
  };

  const marginInfoStyle = {
    fontSize: "11px",
    color: "#4b5563",
    marginRight: "8px",
  };

  const marginValueStyle = {
    fontWeight: 600,
  };

  const headerRightStyle = {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  };

  const executeButton = (canExecute) => ({
    padding: "4px 16px",
    borderRadius: "8px",
    border: "1px solid #c4b5fd",
    backgroundColor: canExecute ? "#eef2ff" : "#f3f4f6",
    color: canExecute ? "#4f46e5" : "#9ca3af",
    fontSize: "12px",
    fontWeight: 600,
    cursor: canExecute ? "pointer" : "default",
  });

  const deleteIconButton = {
    border: "none",
    background: "none",
    cursor: "pointer",
    padding: "4px",
    color: "#f97373",
    fontSize: "14px",
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

  const thStyle = {
    padding: "8px 14px",
    textAlign: "left",
    fontWeight: 600,
    color: "#6b7280",
    whiteSpace: "nowrap",
  };

  const thRight = { ...thStyle, textAlign: "right" };

  const rowStyle = {
    borderBottom: "1px solid #e5e7eb",
    backgroundColor: "#ffffff",
  };

  const tdStyle = {
    padding: "8px 14px",
    color: "#111827",
    verticalAlign: "middle",
    whiteSpace: "nowrap",
  };

  const tdRight = { ...tdStyle, textAlign: "right" };

  const sideBadge = (side) => {
    const base = {
      padding: "4px 10px",
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

  const deleteLegButton = {
    border: "none",
    background: "none",
    cursor: "pointer",
    padding: "4px",
    color: "#f97373",
    fontSize: "14px",
  };

  const formatMoney = (v) =>
    "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 0 });

  // ---------- render ----------
  return (
    <div style={pageStyle}>
      <div style={{...mainCardStyle, marginBottom: '16px'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px'}}>
          <h3 style={{margin: 0, fontSize: '16px', fontWeight: 'bold'}}>Basket Orders</h3>
          <button
            onClick={handleRefresh}
            style={{
              background: 'none',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              padding: '6px 12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '14px'
            }}
            title="Refresh baskets"
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>
      <div style={mainCardStyle}>
        {baskets.map((basket) => {
          const canExecute =
            basket.requiredMargin <= user.walletBalance &&
            basket.requiredMargin > 0;

          return (
            <div key={basket.id} style={basketWrapperStyle}>
              {/* Basket header */}
              <div style={basketHeaderStyle}>
                <div style={basketTitleStyle}>{basket.name}</div>
                <div style={headerRightStyle}>
                  <div style={marginInfoStyle}>
                    Required Margin:{" "}
                    <span style={marginValueStyle}>
                      {formatMoney(basket.requiredMargin)}
                    </span>{" "}
                    | Wallet:{" "}
                    <span style={marginValueStyle}>
                      {formatMoney(user.walletBalance)}
                    </span>
                  </div>
                  <button
                    style={executeButton(canExecute)}
                    onClick={() => canExecute && handleExecute(basket.id)}
                  >
                    Execute
                  </button>
                  <button
                    style={deleteIconButton}
                    onClick={() => handleDeleteBasket(basket.id)}
                    title="Delete basket"
                  >
                    🗑
                  </button>
                </div>
              </div>

              {/* Basket table */}
              <table style={tableStyle}>
                <thead style={theadStyle}>
                  <tr>
                    <th style={thStyle}>Type</th>
                    <th style={thStyle}>Symbol</th>
                    <th style={thStyle}>Product</th>
                    <th style={thRight}>Qty</th>
                    <th style={thRight}>Price</th>
                    <th style={thRight}></th>
                  </tr>
                </thead>
                <tbody>
                  {basket.legs.length === 0 ? (
                    <tr style={rowStyle}>
                      <td style={tdStyle} colSpan={6}>
                        {/* Empty basket, as in EXIT screenshot */}
                      </td>
                    </tr>
                  ) : (
                    basket.legs.map((leg) => (
                      <tr key={leg.id} style={rowStyle}>
                        <td style={tdStyle}>{sideBadge(leg.side)}</td>
                        <td style={tdStyle}>{leg.symbol}</td>
                        <td style={tdStyle}>{leg.productType}</td>
                        <td style={tdRight}>
                          {leg.qty.toLocaleString("en-IN")}
                        </td>
                        <td style={tdRight}>{leg.price.toFixed(2)}</td>
                        <td style={tdRight}>
                          <button
                            style={deleteLegButton}
                            onClick={() => handleDeleteLeg(basket.id, leg.id)}
                            title="Delete leg"
                          >
                            🗑
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default BasketsTab;
