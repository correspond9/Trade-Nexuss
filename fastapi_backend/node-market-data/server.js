import express from "express";
import { start, prices } from "./DhanSocket.js";

const app = express();
const PORT = 9100;

app.get("/prices", (req, res) => {
  res.json(prices);
});

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

start();

app.listen(PORT, () => {
  console.log("🚀 Node Market Data running on :" + PORT);
});
