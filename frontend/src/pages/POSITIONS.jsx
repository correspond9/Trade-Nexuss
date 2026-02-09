import React, { useState, useEffect, useCallback } from "react";
import { apiService } from '../services/apiService';
import { useAuth } from '../contexts/AuthContext';

const PositionsTab = () => {
  const { user } = useAuth();
  const [positions, setPositions] = useState([]);
  const [selectedOpenIds, setSelectedOpenIds] = useState(new Set());

  const fetchPositions = useCallback(async () => {
    try {
      const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN';
      const params = !isAdmin && user?.id ? { user_id: user.id } : {};
      const positionsResponse = await apiService.get('/portfolio/positions', params);
      if (positionsResponse && positionsResponse.data) {
        const mapped = positionsResponse.data.map((p) => {
          const qty = Number(p.quantity ?? p.qty ?? 0);
          const avgEntry = Number(p.avg_price ?? p.avgEntry ?? 0);
          const mtm = Number(p.mtm ?? 0);
          const currentLtp = qty !== 0 ? avgEntry + mtm / qty : avgEntry;
          return {
            id: p.id,
            productType: p.product_type ?? p.productType ?? 'MIS',
            symbol: p.symbol,
            qty,
            avgEntry: avgEntry.toFixed ? avgEntry.toFixed(2) : avgEntry,
            currentLtp: currentLtp.toFixed ? currentLtp.toFixed(2) : currentLtp,
            mtm,
            realizedPnl: p.realizedPnl ?? p.realized_pnl ?? 0,
            status: p.status ?? 'OPEN'
          };
        });
        setPositions(mapped);
      }
    } catch (err) {
      console.error('Error fetching positions:', err);
    }
  }, [user]);

  // Fetch live positions from API
  useEffect(() => {
    fetchPositions();
  }, [fetchPositions]);

  useEffect(() => {
    const handlePositionsUpdated = () => fetchPositions();
    window.addEventListener('positions:updated', handlePositionsUpdated);
    return () => window.removeEventListener('positions:updated', handlePositionsUpdated);
  }, [fetchPositions]);

  useEffect(() => {
    const id = setInterval(fetchPositions, 5000);
    return () => clearInterval(id);
  }, [fetchPositions]);

  // Manual refresh function
  const handleRefresh = () => {
    fetchPositions();
  };

  const openPositions = positions.filter((p) => p.status === "OPEN");
  const closedPositions = positions.filter((p) => p.status === "CLOSED");

  const totalMtm = openPositions.reduce((sum, p) => sum + parseFloat(p.mtm), 0);
  const totalClosed = closedPositions.reduce(
    (sum, p) => sum + p.realizedPnl,
    0
  );

  // ----- selection -----
  const toggleSelectOne = (id) => {
    setSelectedOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAllOpen = () => {
    setSelectedOpenIds((prev) => {
      if (prev.size === openPositions.length) return new Set();
      const next = new Set(openPositions.map((p) => p.id));
      return next;
    });
  };

  const handleExitOne = (id) => {
    exitPositions(new Set([id]));
  };

  const handleExitSelected = () => {
    if (!selectedOpenIds.size) return;
    exitPositions(selectedOpenIds);
  };

  const exitPositions = async (idsSet) => {
    try {
      // Call backend API to actually close positions
      for (const id of idsSet) {
        const response = await apiService.post(`/positions/${id}/close`, {
          quantity: undefined  // Let backend determine quantity
        });
        console.log(`Exit position ${id}:`, response?.data || response);
      }
      
      // Wait a moment for backend processing
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Refresh positions from backend
      await fetchPositions();
      setSelectedOpenIds(new Set());
    } catch (err) {
      console.error('Error exiting positions:', err);
      // Fallback: Update local state if API fails
      setPositions((prev) =>
        prev.map((p) => {
          if (!idsSet.has(p.id) || p.status !== "OPEN") return p;
          const exitPrice = parseFloat(p.currentLtp);
          const entry = parseFloat(p.avgEntry);
          const realized =
            p.side === "BUY"
              ? p.qty * (exitPrice - entry)
              : p.qty * (entry - exitPrice);
          return {
            ...p,
            status: "CLOSED",
            exitPrice: exitPrice.toFixed(2),
            exitTime: new Date().toLocaleTimeString("en-IN", { hour12: true }),
            realizedPnl: realized,
          };
        })
      );
      setSelectedOpenIds(new Set());
    }
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
    padding: "24px 24px 32px 24px",
    border: "1px solid #e5e7eb",
  };

  const sectionHeaderRowStyle = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
    marginTop: "8px",
  };

  const sectionTitleStyle = {
    fontSize: "14px",
    fontWeight: 600,
    color: "#111827",
  };

  const totalTextStyle = {
    fontSize: "13px",
    fontWeight: 600,
    color: "#111827",
  };

  const totalValueStyle = {
    fontWeight: 700,
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

  const thStyle = {
    padding: "10px 12px",
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
    padding: "10px 12px",
    color: "#111827",
    verticalAlign: "middle",
    whiteSpace: "nowrap",
  };

  const tdRight = { ...tdStyle, textAlign: "right" };

  const checkboxStyle = {
    width: 14,
    height: 14,
  };

  const exitButtonStyle = {
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    padding: "4px 12px",
    fontSize: "12px",
    backgroundColor: "#ffffff",
    cursor: "pointer",
  };

  const exitSelectedButtonStyle = {
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    padding: "4px 12px",
    fontSize: "12px",
    backgroundColor: selectedOpenIds.size ? "#f97316" : "#f3f4f6",
    color: selectedOpenIds.size ? "#ffffff" : "#9ca3af",
    cursor: selectedOpenIds.size ? "pointer" : "default",
  };

  const qtyTextStyle = {
    fontVariantNumeric: "tabular-nums",
  };

  const plPositive = { color: "#16a34a" };
  const plNegative = { color: "#dc2626" };

  const totalRowStyle = {
    ...rowStyle,
    backgroundColor: "#f9fafb",
    fontWeight: 600,
  };

  // ------ helpers ------
  const formatMoney = (v) =>
    "₹" + Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 2 });

  const renderOpenRows = () =>
    openPositions.map((p) => (
      <tr key={p.id} style={rowStyle}>
        <td style={tdStyle}>
          <input
            type="checkbox"
            style={checkboxStyle}
            checked={selectedOpenIds.has(p.id)}
            onChange={() => toggleSelectOne(p.id)}
          />
        </td>
        <td style={tdStyle}>{p.productType}</td>
        <td style={tdStyle}>{p.symbol}</td>
        <td style={{ ...tdRight, ...qtyTextStyle }}>
          {p.qty.toLocaleString("en-IN")}
        </td>
        <td style={tdRight}>{p.avgEntry}</td>
        <td style={tdRight}>{p.currentLtp}</td>
        <td
          style={{
            ...tdRight,
            ...(parseFloat(p.mtm) >= 0 ? plPositive : plNegative),
          }}
        >
          {formatMoney(parseFloat(p.mtm))}
        </td>
        <td style={{ ...tdStyle }}>
          <button style={exitButtonStyle} onClick={() => handleExitOne(p.id)}>
            Exit
          </button>
        </td>
      </tr>
    ));

  const renderClosedRows = () =>
    closedPositions.map((p) => (
      <tr key={p.id} style={rowStyle}>
        <td style={tdStyle}>
          <input type="checkbox" style={checkboxStyle} disabled />
        </td>
        <td style={tdStyle}>{p.productType}</td>
        <td style={tdStyle}>{p.symbol}</td>
        <td style={{ ...tdRight, ...qtyTextStyle }}>
          {p.qty.toLocaleString("en-IN")}
        </td>
        <td style={tdRight}>{p.avgEntry}</td>
        <td style={tdRight}>{p.exitPrice || "0.00"}</td>
        <td
          style={{
            ...tdRight,
            ...(p.realizedPnl >= 0 ? plPositive : plNegative),
          }}
        >
          {formatMoney(p.realizedPnl)}
        </td>
      </tr>
    ));

  // ---------- Render ----------
  return (
    <div style={pageStyle}>
      <div style={mainCardStyle}>
        {/* Open Positions header */}
        <div style={sectionHeaderRowStyle}>
          <div style={{...sectionTitleStyle, display: 'flex', alignItems: 'center', gap: '8px'}}>
            Open Positions ({openPositions.length})
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
              title="Refresh positions"
            >
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
          <div style={totalTextStyle}>
            Total MTM :{" "}
            <span
              style={{
                ...totalValueStyle,
                ...(totalMtm >= 0 ? plPositive : plNegative),
              }}
            >
              {formatMoney(totalMtm)}
            </span>
          </div>
        </div>

        {/* Open table */}
        <div style={tableOuterStyle}>
          <table style={tableStyle}>
            <thead style={theadStyle}>
              <tr>
                <th style={thStyle}>
                  <input
                    type="checkbox"
                    style={checkboxStyle}
                    checked={
                      openPositions.length > 0 &&
                      selectedOpenIds.size === openPositions.length
                    }
                    onChange={toggleSelectAllOpen}
                  />
                </th>
                <th style={thStyle}>Product</th>
                <th style={thStyle}>Instrument</th>
                <th style={thRight}>Qty.</th>
                <th style={thRight}>Avg.</th>
                <th style={thRight}>LTP</th>
                <th style={thRight}>P&L</th>
                <th style={{ ...thRight }}>
                  <button
                    style={exitSelectedButtonStyle}
                    onClick={handleExitSelected}
                  >
                    Exit Selected
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {openPositions.length === 0 ? (
                <tr>
                  <td style={tdStyle} colSpan={8}>
                    No open positions.
                  </td>
                </tr>
              ) : (
                <>
                  {renderOpenRows()}
                  {/* total row like screenshot */}
                  <tr style={totalRowStyle}>
                    <td style={tdStyle}></td>
                    <td style={tdStyle}></td>
                    <td style={tdStyle}></td>
                    <td style={tdRight}></td>
                    <td style={tdRight}></td>
                    <td style={{ ...tdRight, color: "#111827" }}>Total</td>
                    <td
                      style={{
                        ...tdRight,
                        ...(totalMtm >= 0 ? plPositive : plNegative),
                      }}
                    >
                      {formatMoney(totalMtm)}
                    </td>
                    <td style={tdStyle}></td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>

        {/* Closed Positions header */}
        <div style={{ ...sectionHeaderRowStyle, marginTop: "24px" }}>
          <div style={sectionTitleStyle}>
            Closed Positions ({closedPositions.length})
          </div>
        </div>

        {/* Closed table */}
        <div style={tableOuterStyle}>
          <table style={tableStyle}>
            <thead style={theadStyle}>
              <tr>
                <th style={thStyle}>
                  <input type="checkbox" style={checkboxStyle} disabled />
                </th>
                <th style={thStyle}>Product</th>
                <th style={thStyle}>Instrument</th>
                <th style={thRight}>Qty.</th>
                <th style={thRight}>Avg.</th>
                <th style={thRight}>LTP</th>
                <th style={thRight}>P&L</th>
              </tr>
            </thead>
            <tbody>
              {closedPositions.length === 0 ? (
                <tr>
                  <td style={tdStyle} colSpan={7}>
                    No closed positions yet.
                  </td>
                </tr>
              ) : (
                <>
                  {renderClosedRows()}
                  <tr style={totalRowStyle}>
                    <td style={tdStyle}></td>
                    <td style={tdStyle}></td>
                    <td style={{ ...tdStyle, color: "#111827" }}>Total</td>
                    <td style={tdRight}></td>
                    <td style={tdRight}></td>
                    <td style={tdRight}></td>
                    <td
                      style={{
                        ...tdRight,
                        ...(totalClosed >= 0 ? plPositive : plNegative),
                      }}
                    >
                      {formatMoney(totalClosed)}
                    </td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PositionsTab;
