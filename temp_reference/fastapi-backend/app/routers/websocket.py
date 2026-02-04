"""
WebSocket Router
Handles WebSocket connections for real-time data
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import json
import asyncio

from app.database import get_db
from app.dependencies import get_current_active_user

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/market-data")
async def websocket_market_data(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for market data"""
    client_id = f"client_{id(websocket)}"
    
    try:
        await manager.connect(websocket, client_id)
        
        # Send welcome message
        await manager.send_personal_message(
            json.dumps({"type": "welcome", "message": "Connected to market data stream"}),
            client_id
        )
        
        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "subscribe":
                # TODO: Implement subscription logic
                await manager.send_personal_message(
                    json.dumps({"type": "subscription_ack", "symbol": message.get("symbol")}),
                    client_id
                )
            elif message.get("type") == "unsubscribe":
                # TODO: Implement unsubscription logic
                await manager.send_personal_message(
                    json.dumps({"type": "unsubscription_ack", "symbol": message.get("symbol")}),
                    client_id
                )
            elif message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({"type": "pong"}),
                    client_id
                )
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)

@router.get("/connections")
async def get_active_connections():
    """Get number of active WebSocket connections"""
    return {
        "active_connections": len(manager.active_connections),
        "connections": list(manager.active_connections.keys())
    }

# Mock data stream for testing
async def start_mock_data_stream():
    """Start mock market data stream"""
    while True:
        # Mock market data
        mock_data = {
            "type": "market_data",
            "symbol": "NIFTY",
            "price": 19500.0 + (asyncio.get_event_loop().time() % 100),
            "change": 0.5,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await manager.broadcast(json.dumps(mock_data))
        await asyncio.sleep(1)  # Send data every second
