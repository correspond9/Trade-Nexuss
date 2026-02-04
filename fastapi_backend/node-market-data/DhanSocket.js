import WebSocket from "ws";

const prices = {
  NIFTY: 0,
  SENSEX: 0,
  CRUDEOIL: 0
};

let socket = null;

// Exchange segment constants
const EXCHANGE_IDX_I = 1;   // IDX_I
const EXCHANGE_MCX = 4;     // MCX_FO

// Security IDs
const NIFTY_TOKEN = 13;
const SENSEX_TOKEN = 25;
const CRUDEOIL_TOKEN = 1140000005;

function start() {
  const accessToken = process.env.DHAN_ACCESS_TOKEN;
  const clientId = process.env.DHAN_CLIENT_ID;

  if (!accessToken || !clientId) {
    console.error("❌ Missing DHAN_ACCESS_TOKEN or DHAN_CLIENT_ID");
    return;
  }

  const url =
    `wss://api-feed.dhan.co?version=2` +
    `&token=${accessToken}` +
    `&clientId=${clientId}` +
    `&authType=2`;

  socket = new WebSocket(url);
  socket.binaryType = "arraybuffer";

  socket.on("open", () => {
    console.log("✅ Dhan WS Connected");
    subscribe();
  });

  socket.on("message", (data) => {
    parsePacket(data);
  });

  socket.on("close", () => {
    console.log("⚠️ Dhan WS Closed, reconnecting...");
    setTimeout(start, 5000);
  });

  socket.on("error", (err) => {
    console.error("❌ WS Error:", err.message);
  });
}

function subscribe() {
  // Binary subscription packet structure:
  // [1B RequestCode][1B InstrumentCount]
  // For each instrument: [1B ExchangeSegment][4B SecurityId (BE uint32)]
  
  const packet = Buffer.allocUnsafe(2 + 3 * 5); // Header + 3 instruments
  let offset = 0;

  // Header
  packet.writeUInt8(15, offset++);  // RequestCode = 15
  packet.writeUInt8(3, offset++);   // InstrumentCount = 3

  // NIFTY (IDX_I, token 13)
  packet.writeUInt8(EXCHANGE_IDX_I, offset++);
  packet.writeUInt32BE(NIFTY_TOKEN, offset);
  offset += 4;

  // SENSEX (IDX_I, token 25)
  packet.writeUInt8(EXCHANGE_IDX_I, offset++);
  packet.writeUInt32BE(SENSEX_TOKEN, offset);
  offset += 4;

  // CRUDEOIL (MCX, token 1140000005)
  packet.writeUInt8(EXCHANGE_MCX, offset++);
  packet.writeUInt32BE(CRUDEOIL_TOKEN, offset);
  offset += 4;

  socket.send(packet);
  console.log("📡 Binary subscription sent:", {
    NIFTY: NIFTY_TOKEN,
    SENSEX: SENSEX_TOKEN,
    CRUDEOIL: CRUDEOIL_TOKEN
  });
}

function parsePacket(data) {
  // Convert ArrayBuffer to Buffer if needed
  const buffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
  
  // Each tick is 13 bytes:
  // [1B ExchangeSegment][4B SecurityId (BE)][8B LTP (BE double)]
  const TICK_SIZE = 13;
  
  if (buffer.length < TICK_SIZE) return;

  let offset = 0;
  while (offset + TICK_SIZE <= buffer.length) {
    const segment = buffer.readUInt8(offset);
    const securityId = buffer.readUInt32BE(offset + 1);
    const ltp = buffer.readDoubleBE(offset + 5);
    offset += TICK_SIZE;

    if (ltp <= 0) continue;

    // Update prices based on security ID
    if (securityId === NIFTY_TOKEN) {
      prices.NIFTY = Math.round(ltp * 100) / 100;
      console.log(`📈 NIFTY: ${prices.NIFTY}`);
    } else if (securityId === SENSEX_TOKEN) {
      prices.SENSEX = Math.round(ltp * 100) / 100;
      console.log(`📈 SENSEX: ${prices.SENSEX}`);
    } else if (securityId === CRUDEOIL_TOKEN) {
      prices.CRUDEOIL = Math.round(ltp * 100) / 100;
      console.log(`📈 CRUDEOIL: ${prices.CRUDEOIL}`);
    }
  }
}

export { start, prices };
