// src/App.tsx
import React, { useEffect, useMemo, useState } from "react";
import { apiService } from "../services/apiService";
import { useAuth } from "../contexts/AuthContext";

// ---------- EXPIRY HELPER FUNCTION ----------

const generateExpiryDates = () => {
  const now = new Date();
  const currentYear = now.getFullYear().toString().slice(-2); // Get last 2 digits
  const currentMonth = now.getMonth();
  
  // Get current expiry (last Thursday of current month)
  const currentExpiry = new Date(now.getFullYear(), currentMonth + 1, 0);
  while (currentExpiry.getDay() !== 4) {
    currentExpiry.setDate(currentExpiry.getDate() - 1);
  }
  
  // Get next expiry (last Thursday of next month)
  const nextExpiry = new Date(now.getFullYear(), currentMonth + 2, 0);
  while (nextExpiry.getDay() !== 4) {
    nextExpiry.setDate(nextExpiry.getDate() - 1);
  }
  
  const formatExpiry = (date: Date) => {
    const day = date.getDate();
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    return `${day}${months[date.getMonth()]}`;
  };
  
  return {
    current: formatExpiry(currentExpiry),
    next: formatExpiry(nextExpiry),
    currentYear: currentYear
  };
};

// ---------- DEFAULT USER + HELPERS ----------

const DEFAULT_USER = {
  id: 7521,
  userId: "7521",
  name: "Sufyan Ahmed Ansari",
  mobile: "919967595222",
  email: "correspond9@gmail.com",
  aadhar: "764188319360",
  pan: "AOIPA0516K",
  upi: "9967595222@apl",
  address:
    "373, Adam Ali Bldg, Room No1, 1st Floor, Bapty Road, Mumbai, Maharashtra, India",
  walletBalance: 716608.3,
  profitTargetPct: 0,
  slPct: 5,
  status: "APPROVED", // APPROVED | BLOCKED | ON_HOLD
  mfaEnabled: true,
  allocatedMargin: 3000000,
};

const toDateOnly = (isoLike: string) => {
  const d = new Date(isoLike);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
};

const inDateRange = (
  d: string,
  fromDate: Date | null,
  toDate: Date | null
): boolean => {
  if (!fromDate && !toDate) return true;
  const dd = toDateOnly(d);
  if (fromDate && dd < fromDate) return false;
  if (toDate && dd > toDate) return false;
  return true;
};

const formatINR = (n: number) =>
  `₹${n.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })}`;

const formatDateDisplay = (isoLike: string) =>
  new Date(isoLike).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

// ---------- DEFAULT DATA ----------

const expiries = generateExpiryDates();
const DEFAULT_TRADES: TradeRow[] = [];

type PnLRow = {
  id: number;
  date: string;
  symbol: string;
  instrumentType: "OPTION" | "FUTURE";
  buyQty: number;
  buyPrice: number;
  buyValue: number;
  sellQty: number;
  sellPrice: number;
  sellValue: number;
  platformCost: number;
  tradeExpense: number;
  netPnL: number;
};

type TradeRow = {
  id: number;
  date: string;
  time: string;
  side: "BUY" | "SELL";
  symbol: string;
  product: string;
  qty: number;
  price: number;
  status: string;
};

type LedgerRow = {
  id: number;
  date: string;
  particular: string;
  type: string;
  remarks: string;
  credit: number;
  debit: number;
};

type FundsRow = {
  id: number;
  date: string;
  amount: number;
  status: string;
  method: string;
};

const buildPnLRows = (trades: TradeRow[]): PnLRow[] =>
  trades.map((t, idx) => {
    const isOption = t.symbol.includes("CE") || t.symbol.includes("PE");
    const instrumentType: "OPTION" | "FUTURE" = isOption ? "OPTION" : "FUTURE";

    const qty = t.qty;
    const basePrice = t.price;
    const buyQty = t.side === "BUY" ? qty : 0;
    const sellQty = t.side === "SELL" ? qty : 0;
    const buyPrice = t.side === "BUY" ? basePrice : 0;
    const sellPrice = t.side === "SELL" ? basePrice : 0;

    const buyValue = buyQty * buyPrice;
    const sellValue = sellQty * sellPrice;
    const platformCost = 0;
    const tradeExpense = 0;
    const net = sellValue - buyValue;

    return {
      id: t.id,
      date: t.date,
      symbol: t.symbol,
      instrumentType,
      buyQty,
      buyPrice,
      buyValue,
      sellQty,
      sellPrice,
      sellValue,
      platformCost,
      tradeExpense,
      netPnL: net,
    };
  });
const DEFAULT_PNL_ROWS: PnLRow[] = [];
const DEFAULT_LEDGER: LedgerRow[] = [];
const DEFAULT_FUNDS_PAYIN: FundsRow[] = [];
const DEFAULT_FUNDS_PAYOUT: FundsRow[] = [];

// ---------- SMALL PRESENTATION HELPERS ----------

const TradeHistoryTable: React.FC<{
  fromDate: Date | null;
  toDate: Date | null;
  trades: TradeRow[];
}> = ({ fromDate, toDate, trades }) => {
  const rows = useMemo(
    () => trades.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [trades, fromDate, toDate]
  );
  return (
    <div className="table-card">
      <h3 className="card-title" style={{ fontSize: 14, marginBottom: 8 }}>
        Trade History
      </h3>
      <table>
        <thead>
          <tr>
            <th>Date / Time</th>
            <th>Type</th>
            <th>Symbol</th>
            <th>Product</th>
            <th style={{ textAlign: "right" }}>Qty</th>
            <th style={{ textAlign: "right" }}>Price</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={7}>No trades found for the selected date range.</td>
            </tr>
          ) : (
            rows.map((r) => (
              <tr key={r.id}>
                <td>
                  {formatDateDisplay(r.date)} {r.time}
                </td>
                <td>
                  <span
                    className={r.side === "BUY" ? "badge-buy" : "badge-sell"}
                  >
                    {r.side}
                  </span>
                </td>
                <td>{r.symbol}</td>
                <td>{r.product}</td>
                <td style={{ textAlign: "right" }}>
                  {r.qty.toLocaleString("en-IN")}
                </td>
                <td style={{ textAlign: "right" }}>{r.price.toFixed(2)}</td>
                <td>{r.status}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

const PnLReportsTable: React.FC<{
  fromDate: Date | null;
  toDate: Date | null;
  pnlRows: PnLRow[];
}> = ({ fromDate, toDate, pnlRows }) => {
  const rows = useMemo(
    () => pnlRows.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [pnlRows, fromDate, toDate]
  );

  const totals = useMemo(
    () =>
      rows.reduce(
        (acc, r) => {
          acc.buyValue += r.buyValue;
          acc.sellValue += r.sellValue;
          acc.netPnL += r.netPnL;
          return acc;
        },
        { buyValue: 0, sellValue: 0, netPnL: 0 }
      ),
    [rows]
  );

  return (
    <div className="table-card">
      <h3 className="card-title" style={{ fontSize: 14, marginBottom: 8 }}>
        P and L Reports
      </h3>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Symbol</th>
            <th style={{ textAlign: "right" }}>Buy Qty</th>
            <th style={{ textAlign: "right" }}>Buy Price</th>
            <th style={{ textAlign: "right" }}>Buy Value</th>
            <th style={{ textAlign: "right" }}>Sell Qty</th>
            <th style={{ textAlign: "right" }}>Sell Price</th>
            <th style={{ textAlign: "right" }}>Sell Value</th>
            <th style={{ textAlign: "right" }}>Platform Cost</th>
            <th style={{ textAlign: "right" }}>Trade Expense</th>
            <th style={{ textAlign: "right" }}>net P&amp;L</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={11}>
                No P&amp;L entries for the selected date range.
              </td>
            </tr>
          ) : (
            rows.map((r) => (
              <tr key={r.id}>
                <td>{formatDateDisplay(r.date)}</td>
                <td>{r.symbol}</td>
                <td style={{ textAlign: "right" }}>
                  {r.buyQty.toLocaleString("en-IN")}
                </td>
                <td style={{ textAlign: "right" }}>{r.buyPrice.toFixed(2)}</td>
                <td style={{ textAlign: "right" }}>
                  {r.buyValue.toLocaleString("en-IN", {
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td style={{ textAlign: "right" }}>
                  {r.sellQty.toLocaleString("en-IN")}
                </td>
                <td style={{ textAlign: "right" }}>{r.sellPrice.toFixed(2)}</td>
                <td style={{ textAlign: "right" }}>
                  {r.sellValue.toLocaleString("en-IN", {
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td style={{ textAlign: "right" }}>
                  {r.platformCost.toFixed(2)}
                </td>
                <td style={{ textAlign: "right" }}>
                  {r.tradeExpense.toFixed(2)}
                </td>
                <td
                  style={{
                    textAlign: "right",
                    color: r.netPnL >= 0 ? "#16a34a" : "#dc2626",
                    fontWeight: 600,
                  }}
                >
                  {r.netPnL.toFixed(2)}
                </td>
              </tr>
            ))
          )}
        </tbody>
        {rows.length > 0 && (
          <tfoot>
            <tr>
              <td colSpan={4} />
              <td style={{ textAlign: "right", fontWeight: 600 }}>
                {totals.buyValue.toLocaleString("en-IN", {
                  maximumFractionDigits: 2,
                })}
              </td>
              <td colSpan={2} />
              <td style={{ textAlign: "right", fontWeight: 600 }}>
                {totals.sellValue.toLocaleString("en-IN", {
                  maximumFractionDigits: 2,
                })}
              </td>
              <td />
              <td />
              <td
                style={{
                  textAlign: "right",
                  fontWeight: 600,
                  color: totals.netPnL >= 0 ? "#16a34a" : "#dc2626",
                }}
              >
                {totals.netPnL.toFixed(2)}
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
};

const LedgerTable: React.FC<{
  fromDate: Date | null;
  toDate: Date | null;
  ledgerEntries: LedgerRow[];
  startBalance: number;
}> = ({ fromDate, toDate, ledgerEntries, startBalance }) => {
  const sorted = useMemo(
    () =>
      [...ledgerEntries].sort(
        (a, b) => toDateOnly(b.date).getTime() - toDateOnly(a.date).getTime()
      ),
    [ledgerEntries]
  );

  const filtered = useMemo(
    () => sorted.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [sorted, fromDate, toDate]
  );

  let running = startBalance;
  const rowsWithBalance = filtered.map((r) => {
    running = running + (r.credit || 0) - (r.debit || 0);
    return { ...r, balance: running };
  });

  const summary = rowsWithBalance.reduce(
    (acc, r) => {
      acc.credit += r.credit || 0;
      acc.debit += r.debit || 0;
      acc.balance = r.balance;
      return acc;
    },
    { credit: 0, debit: 0, balance: startBalance }
  );

  return (
    <div className="table-card">
      <h3 className="card-title" style={{ fontSize: 14, marginBottom: 8 }}>
        Ledger
      </h3>
      <div
        style={{
          fontSize: 11,
          marginBottom: 8,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <div>
          Credits:{" "}
          <strong style={{ color: "#16a34a" }}>
            {formatINR(summary.credit)}
          </strong>{" "}
          &nbsp; Debits:{" "}
          <strong style={{ color: "#dc2626" }}>
            {formatINR(summary.debit)}
          </strong>
        </div>
        <div>
          Balance: <strong>{formatINR(summary.balance)}</strong>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Particular</th>
            <th>Type</th>
            <th>Remarks</th>
            <th style={{ textAlign: "right" }}>Credit</th>
            <th style={{ textAlign: "right" }}>Debit</th>
            <th style={{ textAlign: "right" }}>Balance</th>
          </tr>
        </thead>
        <tbody>
          {rowsWithBalance.length === 0 ? (
            <tr>
              <td colSpan={7}>No ledger entries yet.</td>
            </tr>
          ) : (
            rowsWithBalance.map((r) => (
              <tr key={r.id}>
                <td>{formatDateDisplay(r.date)}</td>
                <td>{r.particular}</td>
                <td>{r.type}</td>
                <td>{r.remarks}</td>
                <td style={{ textAlign: "right", color: "#16a34a" }}>
                  {r.credit ? formatINR(r.credit) : "-"}
                </td>
                <td style={{ textAlign: "right", color: "#dc2626" }}>
                  {r.debit ? formatINR(r.debit) : "-"}
                </td>
                <td style={{ textAlign: "right" }}>{formatINR(r.balance)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

// simple Funds and Margin views (same as before, plain styling)

const FundsView: React.FC<{
  fromDate: Date | null;
  toDate: Date | null;
  fundsPayin: FundsRow[];
  fundsPayout: FundsRow[];
  balance: number;
}> = ({ fromDate, toDate, fundsPayin, fundsPayout, balance }) => {
  const [subTab, setSubTab] = useState<"PAYIN" | "PAYOUT">("PAYIN");

  const payInRows = useMemo(
    () => fundsPayin.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [fundsPayin, fromDate, toDate]
  );
  const payOutRows = useMemo(
    () =>
      fundsPayout.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [fundsPayout, fromDate, toDate]
  );

  return (
    <div className="table-card">
      <h3 className="card-title" style={{ fontSize: 14, marginBottom: 8 }}>
        Funds
      </h3>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
          marginBottom: 10,
        }}
      >
        <div>
          <button
            onClick={() => setSubTab("PAYIN")}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              marginRight: 8,
              border: "1px solid #d1d5db",
              background: subTab === "PAYIN" ? "#ffffff" : "#f3f4f6",
              fontWeight: subTab === "PAYIN" ? 600 : 400,
            }}
          >
            Pay In
          </button>
          <button
            onClick={() => setSubTab("PAYOUT")}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #d1d5db",
              background: subTab === "PAYOUT" ? "#ffffff" : "#f3f4f6",
              fontWeight: subTab === "PAYOUT" ? 600 : 400,
            }}
          >
            Pay Out
          </button>
        </div>
        <div>
          Credits: <strong style={{ color: "#16a34a" }}>₹1,460,825.95</strong>
          &nbsp; Debits:{" "}
          <strong style={{ color: "#dc2626" }}>₹744,217.65</strong> &nbsp;
          Balance: <strong>{formatINR(balance)}</strong>
        </div>
      </div>

      {subTab === "PAYIN" ? (
        <div
          style={{ display: "grid", gap: 20, gridTemplateColumns: "1fr 1fr" }}
        >
          <div className="card" style={{ boxShadow: "none" }}>
            <h4
              className="card-title"
              style={{ fontSize: 13, marginBottom: 8 }}
            >
              Pay via NEFT / IMPS
            </h4>
            <p style={{ fontSize: 11 }}>
              Account name: xxxxxxxx
              <br />
              Bank A/c Number: xxxxxxxxxxxx
              <br />
              Bank Name: xxxxxxxxx
              <br />
              Branch: xxxxxxxxx
              <br />
              IFSC: xxxxxxxx
            </p>
            <p style={{ fontSize: 11, marginTop: 10, fontWeight: 600 }}>UPI</p>
            <p style={{ fontSize: 11 }}>xxxxxx@xxxxx</p>
          </div>
          <div className="card" style={{ boxShadow: "none" }}>
            <h4
              className="card-title"
              style={{ fontSize: 13, marginBottom: 8 }}
            >
              Recent Pay In
            </h4>
            <table>
              <thead>
                <tr>
                  <th>Date/Time</th>
                  <th style={{ textAlign: "right" }}>Amount</th>
                  <th>Method</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {payInRows.length === 0 ? (
                  <tr>
                    <td colSpan={4}>No Pay In records for selected dates.</td>
                  </tr>
                ) : (
                  payInRows.map((r) => (
                    <tr key={r.id}>
                      <td>{formatDateDisplay(r.date)}</td>
                      <td style={{ textAlign: "right" }}>
                        {formatINR(r.amount)}
                      </td>
                      <td>{r.method}</td>
                      <td>{r.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div
          style={{ display: "grid", gap: 20, gridTemplateColumns: "1fr 1fr" }}
        >
          <div className="card" style={{ boxShadow: "none" }}>
            <h4
              className="card-title"
              style={{ fontSize: 13, marginBottom: 8 }}
            >
              Pay Out
            </h4>
            <p style={{ fontSize: 11, marginBottom: 4 }}>Amount</p>
            <input
              type="number"
              defaultValue={0}
              style={{
                width: 120,
                padding: "4px 6px",
                borderRadius: 6,
                border: "1px solid #d1d5db",
                fontSize: 11,
              }}
            />
            <br />
            <button
              style={{
                marginTop: 10,
                padding: "6px 12px",
                borderRadius: 6,
                border: "none",
                background: "#4f46e5",
                color: "#ffffff",
                fontSize: 11,
                fontWeight: 600,
                cursor: "pointer",
              }}
              onClick={() =>
                alert(
                  "Payout request placed. This will be saved and visible in admin Payouts tab."
                )
              }
            >
              Place request
            </button>
          </div>
          <div className="card" style={{ boxShadow: "none" }}>
            <h4
              className="card-title"
              style={{ fontSize: 13, marginBottom: 8 }}
            >
              Previous Pay Out Requests
            </h4>
            <table>
              <thead>
                <tr>
                  <th>Date/Time</th>
                  <th style={{ textAlign: "right" }}>Amount</th>
                  <th>Method</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {payOutRows.length === 0 ? (
                  <tr>
                    <td colSpan={4}>No Pay Out requests for selected dates.</td>
                  </tr>
                ) : (
                  payOutRows.map((r) => (
                    <tr key={r.id}>
                      <td>{formatDateDisplay(r.date)}</td>
                      <td style={{ textAlign: "right" }}>
                        {formatINR(r.amount)}
                      </td>
                      <td>{r.method}</td>
                      <td>{r.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

const MarginView: React.FC<{ allowedMargin: number }> = ({ allowedMargin }) => {
  const snapshots = [
    { time: "09:15", used: 175000 },
    { time: "09:20", used: 569500 },
    { time: "09:25", used: 2100500 },
    { time: "09:30", used: 1800000 },
    { time: "09:35", used: 180000 },
    { time: "09:40", used: 450000 },
    { time: "09:45", used: 650000 },
    { time: "09:50", used: 900000 },
    { time: "09:55", used: 1200000 },
    { time: "10:00", used: 523900 },
  ];
  return (
    <div className="table-card">
      <h3 className="card-title" style={{ fontSize: 14, marginBottom: 8 }}>
        Margin Used
      </h3>
      <div
        style={{
          fontSize: 11,
          marginBottom: 8,
          textAlign: "right",
        }}
      >
        Allowed Margin: <strong>{formatINR(allowedMargin)}</strong>
      </div>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th style={{ textAlign: "right" }}>Margin</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.map((r, idx) => (
            <tr key={idx}>
              <td>{r.time}</td>
              <td style={{ textAlign: "right" }}>{formatINR(r.used)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ fontSize: 10, marginTop: 8, color: "#6b7280" }}>
        Margin values are sampled every 5 minutes. In live app, these will come
        from the broker/data API.
      </p>
    </div>
  );
};

// ---------- PROFILE VIEW + REPORTS SHELL ----------

const ProfileView: React.FC<{
  user: typeof DEFAULT_USER;
  onUpdateTargets: (p: number, s: number) => void;
}> = ({ user, onUpdateTargets }) => {
  const [profit, setProfit] = useState<number | string>(user.profitTargetPct);
  const [sl, setSl] = useState<number | string>(user.slPct);

  const statusLabel =
    user.status === "BLOCKED"
      ? "BLOCKED"
      : user.status === "ON_HOLD"
      ? "ON-HOLD"
      : "APPROVED";

  const handleSave = () => {
    const p = Number(profit) || 0;
    const s = Number(sl) || 0;
    onUpdateTargets(p, s);
  };

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <div>
          <div className="card-title">Profile</div>
          <div className="card-subtitle">
            Please fill in your information below.
          </div>
        </div>
        <span className="status-pill">{statusLabel}</span>
      </div>

      <div className="profile-grid">
        <div>
          <span className="field-label">UserId</span>
          <span className="field-value">{user.userId}</span>
        </div>
        <div>
          <span className="field-label">Name</span>
          <span className="field-value">{user.name}</span>
        </div>
        <div>
          <span className="field-label">Mobile</span>
          <span className="field-value">{user.mobile}</span>
        </div>
        <div>
          <span className="field-label">Email</span>
          <span className="field-value">{user.email}</span>
        </div>
        <div>
          <span className="field-label">Aadhar</span>
          <span className="field-value">{user.aadhar}</span>
        </div>
        <div>
          <span className="field-label">PAN</span>
          <span className="field-value">{user.pan}</span>
        </div>
        <div>
          <span className="field-label">UPI</span>
          <span className="field-value">{user.upi}</span>
        </div>
        <div>
          <span className="field-label">Address</span>
          <span className="field-value">{user.address}</span>
        </div>
        <div>
          <span className="field-label">Wallet</span>
          <span className="field-value">{formatINR(user.walletBalance)}</span>
        </div>
      </div>

      <div className="target-row">
        <span className="field-label">Target</span>
        <span>
          Profit %{" "}
          <input
            className="target-input"
            type="number"
            value={profit}
            onChange={(e) => setProfit(e.target.value)}
          />
        </span>
        <span style={{ marginLeft: 12 }}>
          SL %{" "}
          <input
            className="target-input"
            type="number"
            value={sl}
            onChange={(e) => setSl(e.target.value)}
          />
        </span>
        <button className="button-primary" onClick={handleSave}>
          Update Target
        </button>
      </div>

      <p style={{ fontSize: 10, marginTop: 6, color: "#6b7280" }}>
        Profit and SL represent percentage of your current wallet balance.
      </p>
    </div>
  );
};

const ReportsShell: React.FC<{
  trades: TradeRow[];
  pnlRows: PnLRow[];
  ledgerEntries: LedgerRow[];
  fundsPayin: FundsRow[];
  fundsPayout: FundsRow[];
  balance: number;
  allowedMargin: number;
}> = ({ trades, pnlRows, ledgerEntries, fundsPayin, fundsPayout, balance, allowedMargin }) => {
  const [reportType, setReportType] = useState<
    "TRADE_HISTORY" | "PNL" | "LEDGER" | "FUNDS" | "MARGIN"
  >("LEDGER");
  const [from, setFrom] = useState<Date | null>(null);
  const [to, setTo] = useState<Date | null>(null);

  const today = new Date();
  const defaultFromISO = `${today.getFullYear()}-${String(
    today.getMonth() + 1
  ).padStart(2, "0")}-01`;
  const defaultToISO = `${today.getFullYear()}-${String(
    today.getMonth() + 1
  ).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  const handleFrom = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setFrom(v ? new Date(v + "T00:00:00") : null);
  };
  const handleTo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setTo(v ? new Date(v + "T23:59:59") : null);
  };

  return (
    <>
      <div
        style={{
          marginTop: 20,
          marginBottom: 10,
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
        }}
      >
        <div>
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value as typeof reportType)}
            style={{
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #d1d5db",
              fontSize: 11,
            }}
          >
            <option value="TRADE_HISTORY">Trade History</option>
            <option value="PNL">P&amp;L Reports</option>
            <option value="LEDGER">Ledger</option>
            <option value="FUNDS">Funds</option>
            <option value="MARGIN">Margin</option>
          </select>
        </div>
        {reportType !== "MARGIN" && (
          <div>
            From{" "}
            <input
              type="date"
              defaultValue={defaultFromISO}
              onChange={handleFrom}
            />{" "}
            To{" "}
            <input
              type="date"
              defaultValue={defaultToISO}
              onChange={handleTo}
            />
          </div>
        )}
      </div>

      {reportType === "TRADE_HISTORY" && (
        <TradeHistoryTable fromDate={from} toDate={to} trades={trades} />
      )}
      {reportType === "PNL" && (
        <PnLReportsTable fromDate={from} toDate={to} pnlRows={pnlRows} />
      )}
      {reportType === "LEDGER" && (
        <LedgerTable
          fromDate={from}
          toDate={to}
          ledgerEntries={ledgerEntries}
          startBalance={balance}
        />
      )}
      {reportType === "FUNDS" && (
        <FundsView
          fromDate={from}
          toDate={to}
          fundsPayin={fundsPayin}
          fundsPayout={fundsPayout}
          balance={balance}
        />
      )}
      {reportType === "MARGIN" && <MarginView allowedMargin={allowedMargin} />}
    </>
  );
};

// ---------- MAIN APP (PROFILE + REPORTS SWITCH) ----------

const App: React.FC = () => {
  const { user: authUser } = useAuth();
  const [activeMenu, setActiveMenu] = useState<"PROFILE" | "REPORTS">(
    "PROFILE"
  );
  const [user, setUser] = useState(DEFAULT_USER);
  const [trades, setTrades] = useState<TradeRow[]>(DEFAULT_TRADES);
  const [pnlRows, setPnlRows] = useState<PnLRow[]>(DEFAULT_PNL_ROWS);
  const [ledgerEntries, setLedgerEntries] = useState<LedgerRow[]>(DEFAULT_LEDGER);
  const [fundsPayin, setFundsPayin] = useState<FundsRow[]>(DEFAULT_FUNDS_PAYIN);
  const [fundsPayout, setFundsPayout] = useState<FundsRow[]>(DEFAULT_FUNDS_PAYOUT);
  const [allowedMargin, setAllowedMargin] = useState(DEFAULT_USER.allocatedMargin);

  useEffect(() => {
    const loadProfileData = async () => {
      if (!authUser?.id) {
        return;
      }

      try {
        const [usersResponse, ordersResponse, ledgerResponse, payinsResponse, payoutsResponse] = await Promise.all([
          apiService.get('/admin/users'),
          apiService.get('/trading/orders', { user_id: authUser.id }),
          apiService.get('/admin/ledger', { user_id: authUser.id }),
          apiService.get('/admin/payins'),
          apiService.get('/admin/payouts')
        ]);

        const users = usersResponse?.data || [];
        const dbUser = users.find((u) => u.id === authUser.id);
        if (dbUser) {
          setUser((prev) => ({
            ...prev,
            id: dbUser.id,
            userId: String(dbUser.id),
            name: dbUser.username || prev.name,
            email: dbUser.email || prev.email,
            status: dbUser.status || prev.status,
            walletBalance: Number(dbUser.wallet_balance || prev.walletBalance),
            allocatedMargin: Number(dbUser.wallet_balance || prev.allocatedMargin)
          }));
          setAllowedMargin(Number(dbUser.wallet_balance || DEFAULT_USER.allocatedMargin));
        }

        const orders = ordersResponse?.data || [];
        const mappedTrades: TradeRow[] = orders.map((o) => {
          const createdAt = o.created_at || new Date().toISOString();
          const dateObj = new Date(createdAt);
          return {
            id: o.id,
            date: createdAt,
            time: dateObj.toLocaleTimeString('en-IN'),
            side: (o.transaction_type || 'BUY').toUpperCase(),
            symbol: o.symbol || 'UNKNOWN',
            product: o.product_type || 'MIS',
            qty: Number(o.quantity || 0),
            price: Number(o.price || 0),
            status: o.status || 'PENDING'
          } as TradeRow;
        });
        setTrades(mappedTrades);
        setPnlRows(buildPnLRows(mappedTrades));

        const ledger = ledgerResponse?.data || [];
        const mappedLedger: LedgerRow[] = ledger.map((entry) => ({
          id: entry.id,
          date: entry.created_at || new Date().toISOString(),
          particular: entry.entry_type || 'ENTRY',
          type: entry.entry_type || 'ENTRY',
          remarks: entry.remarks || '',
          credit: Number(entry.credit || 0),
          debit: Number(entry.debit || 0)
        }));
        setLedgerEntries(mappedLedger);

        const payins = (payinsResponse?.data || []).filter((e) => e.user_id === authUser.id);
        const payouts = (payoutsResponse?.data || []).filter((e) => e.user_id === authUser.id);
        const mappedPayins: FundsRow[] = payins.map((entry) => ({
          id: entry.id,
          date: entry.created_at || new Date().toISOString(),
          amount: Number(entry.credit || 0),
          status: 'SUCCESS',
          method: entry.entry_type || 'PAYIN'
        }));
        const mappedPayouts: FundsRow[] = payouts.map((entry) => ({
          id: entry.id,
          date: entry.created_at || new Date().toISOString(),
          amount: Number(entry.debit || 0),
          status: 'COMPLETED',
          method: entry.entry_type || 'PAYOUT'
        }));
        setFundsPayin(mappedPayins);
        setFundsPayout(mappedPayouts);
      } catch (error) {
        console.error('Failed to load profile data:', error);
      }
    };

    loadProfileData();
  }, [authUser]);

  const handleUpdateTargets = (p: number, s: number) => {
    setUser((u) => ({ ...u, profitTargetPct: p, slPct: s }));
  };

  return (
    <div className="App">
      <div className="profile-page">
        <div className="profile-topbar">
          <div>
            <div style={{ fontSize: 12, fontWeight: 600 }}>{user.name}</div>
            <div style={{ fontSize: 11 }}>UserId: {user.userId}</div>
          </div>
          <select
            value={activeMenu}
            onChange={(e) => setActiveMenu(e.target.value as typeof activeMenu)}
          >
            <option value="PROFILE">Your Profile</option>
            <option value="REPORTS">Reports</option>
          </select>
        </div>

        {activeMenu === "PROFILE" && (
          <ProfileView user={user} onUpdateTargets={handleUpdateTargets} />
        )}

        {activeMenu === "REPORTS" && (
          <ReportsShell
            trades={trades}
            pnlRows={pnlRows}
            ledgerEntries={ledgerEntries}
            fundsPayin={fundsPayin}
            fundsPayout={fundsPayout}
            balance={user.walletBalance}
            allowedMargin={allowedMargin}
          />
        )}
      </div>
    </div>
  );
};

export default App;
