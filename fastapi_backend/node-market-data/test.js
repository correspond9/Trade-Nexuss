// Quick test to verify environment variables and binary packet structure

console.log("🔍 Environment Check:");
console.log("DHAN_ACCESS_TOKEN:", process.env.DHAN_ACCESS_TOKEN ? "✅ Set" : "❌ Missing");
console.log("DHAN_CLIENT_ID:", process.env.DHAN_CLIENT_ID ? "✅ Set" : "❌ Missing");

// Test binary packet construction
const packet = Buffer.allocUnsafe(2 + 3 * 5);
let offset = 0;

packet.writeUInt8(15, offset++);  // RequestCode
packet.writeUInt8(3, offset++);   // Count

// NIFTY
packet.writeUInt8(1, offset++);
packet.writeUInt32BE(13, offset);
offset += 4;

// SENSEX
packet.writeUInt8(1, offset++);
packet.writeUInt32BE(25, offset);
offset += 4;

// CRUDEOIL
packet.writeUInt8(4, offset++);
packet.writeUInt32BE(1140000005, offset);
offset += 4;

console.log("\n📦 Subscription packet (hex):");
console.log(packet.toString('hex'));
console.log("\n📦 Subscription packet (bytes):", Array.from(packet));

// Test tick parsing
const testTick = Buffer.allocUnsafe(13);
testTick.writeUInt8(1, 0);              // IDX_I segment
testTick.writeUInt32BE(13, 1);          // NIFTY token
testTick.writeDoubleBE(23456.75, 5);    // LTP

console.log("\n🧪 Test tick (hex):", testTick.toString('hex'));
console.log("Parsed:");
console.log("  Segment:", testTick.readUInt8(0));
console.log("  Token:", testTick.readUInt32BE(1));
console.log("  LTP:", testTick.readDoubleBE(5));
