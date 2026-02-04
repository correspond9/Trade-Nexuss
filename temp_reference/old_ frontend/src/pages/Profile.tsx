// src/App.tsx
import React, { useMemo, useState } from "react";

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

// ---------- MOCK USER + HELPERS ----------

const MOCK_USER = {
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

// ---------- MOCK DATA ----------

const expiries = generateExpiryDates();

const MOCK_TRADES = [
  {
    id: 1,
    date: new Date().toISOString().split('T')[0] + "T09:25:00",
    time: "09:25:00",
    side: "BUY",
    symbol: `NIFTY${expiries.currentYear}${expiries.current}2518000CE`,
    product: "NRML",
    qty: 50,
    price: 112.5,
    status: "Executed",
  },
  {
    id: 2,
    date: new Date().toISOString().split('T')[0] + "T10:05:00",
    time: "10:05:00",
    side: "SELL",
    symbol: `BANKNIFTY${expiries.currentYear}${expiries.current}2518500PE`,
    product: "MIS",
    qty: 25,
    price: 245.8,
    status: "Executed",
  },
  {
    id: 3,
    date: new Date(Date.now() - 86400000).toISOString().split('T')[0] + "T09:45:00",
    time: "09:45:00",
    side: "SELL",
    symbol: `NIFTY${expiries.currentYear}${expiries.current}2518200PE`,
    product: "NRML",
    qty: 75,
    price: 178.3,
    status: "Executed",
  },
  {
    id: 4,
    date: new Date(Date.now() - 86400000).toISOString().split('T')[0] + "T13:15:00",
    time: "13:15:00",
    side: "BUY",
    symbol: `BANKNIFTY${expiries.currentYear}${expiries.current}2518800CE`,
    product: "MIS",
    qty: 30,
    price: 156.7,
    status: "Executed",
  },
  {
    id: 5,
    date: new Date(Date.now() - 172800000).toISOString().split('T')[0] + "T11:05:00",
    time: "11:05:00",
    side: "BUY",
    symbol: `FINNIFTY${expiries.currentYear}${expiries.current}2519800CE`,
    product: "NRML",
    qty: 40,
    price: 89.2,
    status: "Executed",
  },
];

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

// simple mock P&L with brokerage + expenses
const buildMockPnL = (): PnLRow[] =>
  MOCK_TRADES.map((t, idx) => {
    const isOption = t.symbol.includes("CE") || t.symbol.includes("PE");
    const instrumentType: "OPTION" | "FUTURE" = isOption ? "OPTION" : "FUTURE";

    const qty = t.qty;
    const basePrice = t.price;
    const buyPrice = t.side === "BUY" ? basePrice : basePrice - (10 + idx * 2);
    const sellPrice =
      t.side === "SELL" ? basePrice : basePrice + (12 + idx * 2);

    const buyValue = qty * buyPrice;
    const sellValue = qty * sellPrice;
    const turnover = buyValue + sellValue;

    const platformRate = isOption ? 0.0005 : 0.00025; // 0.05% or 0.025%
    const platformCost = turnover * platformRate;

    const stt = sellValue * (isOption ? 0.0005 : 0.000125);
    const exchangeTxn = turnover * 0.000053; // approx
    const sebiFees = turnover * 0.000001;
    const stampDuty = buyValue * 0.00003;
    const gstBase = platformCost + exchangeTxn + sebiFees;
    const gst = gstBase * 0.18;

    const tradeExpense = stt + exchangeTxn + sebiFees + stampDuty + gst;
    const net = sellValue - buyValue - platformCost - tradeExpense;

    return {
      id: t.id,
      date: t.date,
      symbol: t.symbol,
      instrumentType,
      buyQty: qty,
      buyPrice,
      buyValue,
      sellQty: qty,
      sellPrice,
      sellValue,
      platformCost,
      tradeExpense,
      netPnL: net,
    };
  });

const MOCK_PNL_ROWS = buildMockPnL();

const MOCK_LEDGER = [
  {
    id: 1,
    date: "2025-12-18T10:00:00",
    particular: "PayIn",
    type: "IMPS",
    remarks: "Funds added via IMPS",
    credit: 200000,
    debit: 0,
  },
  {
    id: 2,
    date: "2025-12-18T15:30:00",
    particular: "Trade P&L",
    type: "Derivatives",
    remarks: "Net profit for the day",
    credit: 16551.35,
    debit: 0,
  },
  {
    id: 3,
    date: "2025-12-19T15:30:00",
    particular: "Trade P&L",
    type: "Derivatives",
    remarks: "Net loss for the day",
    credit: 0,
    debit: 1769.31,
  },
  {
    id: 4,
    date: "2025-12-19T16:00:00",
    particular: "PayOut",
    type: "NEFT",
    remarks: "Withdrawal to bank",
    credit: 0,
    debit: 50000,
  },
];

const MOCK_FUNDS_PAYIN = [
  {
    id: 1,
    date: "2025-12-18T10:00:00",
    amount: 200000,
    status: "SUCCESS",
    method: "IMPS",
  },
  {
    id: 2,
    date: "2025-12-20T09:45:00",
    amount: 150000,
    status: "PENDING",
    method: "NEFT",
  },
];

const MOCK_FUNDS_PAYOUT = [
  {
    id: 1,
    date: "2025-12-19T16:00:00",
    amount: 50000,
    status: "APPROVED",
    method: "NEFT",
  },
];

// ---------- SMALL PRESENTATION HELPERS ----------

const TradeHistoryTable: React.FC<{
  fromDate: Date | null;
  toDate: Date | null;
}> = ({ fromDate, toDate }) => {
  const rows = useMemo(
    () => MOCK_TRADES.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [fromDate, toDate]
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
}> = ({ fromDate, toDate }) => {
  const rows = useMemo(
    () => MOCK_PNL_ROWS.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [fromDate, toDate]
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
}> = ({ fromDate, toDate }) => {
  const sorted = useMemo(
    () =>
      [...MOCK_LEDGER].sort(
        (a, b) => toDateOnly(b.date).getTime() - toDateOnly(a.date).getTime()
      ),
    []
  );

  const filtered = useMemo(
    () => sorted.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [sorted, fromDate, toDate]
  );

  let running = MOCK_USER.walletBalance;
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
    { credit: 0, debit: 0, balance: MOCK_USER.walletBalance }
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
}> = ({ fromDate, toDate }) => {
  const [subTab, setSubTab] = useState<"PAYIN" | "PAYOUT">("PAYIN");

  const payInRows = useMemo(
    () => MOCK_FUNDS_PAYIN.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [fromDate, toDate]
  );
  const payOutRows = useMemo(
    () =>
      MOCK_FUNDS_PAYOUT.filter((r) => inDateRange(r.date, fromDate, toDate)),
    [fromDate, toDate]
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
          Balance: <strong>{formatINR(MOCK_USER.walletBalance)}</strong>
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
                  "Payout request placed (mock). In real app this will be saved and visible in admin Payouts tab."
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

const MarginView: React.FC = () => {
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
        Allowed Margin: <strong>{formatINR(MOCK_USER.allocatedMargin)}</strong>
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
  user: typeof MOCK_USER;
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

const ReportsShell: React.FC = () => {
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
        <TradeHistoryTable fromDate={from} toDate={to} />
      )}
      {reportType === "PNL" && <PnLReportsTable fromDate={from} toDate={to} />}
      {reportType === "LEDGER" && <LedgerTable fromDate={from} toDate={to} />}
      {reportType === "FUNDS" && <FundsView fromDate={from} toDate={to} />}
      {reportType === "MARGIN" && <MarginView />}
    </>
  );
};

// ---------- MAIN APP (PROFILE + REPORTS SWITCH) ----------

const App: React.FC = () => {
  const [activeMenu, setActiveMenu] = useState<"PROFILE" | "REPORTS">(
    "PROFILE"
  );
  const [user, setUser] = useState(MOCK_USER);

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

        {activeMenu === "REPORTS" && <ReportsShell />}
      </div>
    </div>
  );
};

export default App;
