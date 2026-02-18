"""
WebSocket Manager for distributing subscriptions across 5 connections.
Each connection handles max 5,000 instruments.
Deterministic load balancing and auto-reconnect.
"""

import threading
import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

class WebSocketManager:
    """
    Manages 5 WebSocket connections to Dhan API.
    - Max 5,000 instruments per connection
    - Total capacity: 25,000 instruments
    - Deterministic distribution (always assign to least-loaded)
    - Auto-reconnect on failure
    """
    
    def __init__(self, max_connections: int = 5, max_per_connection: int = 5000):
        self.max_connections = max_connections
        self.max_per_connection = max_per_connection
        self.max_total = max_connections * max_per_connection  # 25,000
        
        # Per-connection state
        self.connections = {}  # ws_id -> {"active": bool, "instruments": set(), "handle": None, "reconnect_attempts": int}
        self.instrument_to_ws = {}  # token -> ws_id
        self.lock = threading.RLock()
        
        # Initialize connection slots
        for i in range(1, max_connections + 1):
            self.connections[i] = {
                "active": False,
                "instruments": set(),
                "handle": None,
                "reconnect_attempts": 0,
                "last_error": None,
                "last_connected": None
            }
    
    def get_next_ws(self) -> int:
        """Return the least-loaded active WS connection ID (fallback to any if none active)."""
        with self.lock:
            active_ws = [
                ws_id
                for ws_id in range(1, self.max_connections + 1)
                if self.connections[ws_id]["active"]
            ]
            candidate_ws = active_ws or list(range(1, self.max_connections + 1))
            ws_id = min(candidate_ws, key=lambda w: len(self.connections[w]["instruments"]))
            return ws_id
    
    def can_accommodate(self, count: int = 1) -> bool:
        """Check if we can add `count` more instruments"""
        with self.lock:
            current = sum(len(self.connections[w]["instruments"]) for w in range(1, self.max_connections + 1))
            return current + count <= self.max_total
    
    def add_instrument(self, token: str, ws_id: Optional[int] = None) -> Tuple[bool, int]:
        """
        Add instrument to a WS connection.
        If ws_id not specified, assigns to least-loaded.
        
        Returns: (success, assigned_ws_id)
        """
        with self.lock:
            # Check if already added
            if token in self.instrument_to_ws:
                existing_ws = self.instrument_to_ws[token]
                return (True, existing_ws)
            
            # Check capacity
            current = sum(len(self.connections[w]["instruments"]) for w in range(1, self.max_connections + 1))
            if current >= self.max_total:
                return (False, None)
            
            # Assign to specified WS or find least-loaded active WS.
            if ws_id is None:
                ws_id = self.get_next_ws()
            else:
                # If caller forced an inactive WS while active ones exist, reroute.
                if (not self.connections[ws_id]["active"]) and any(
                    self.connections[w]["active"] for w in range(1, self.max_connections + 1)
                ):
                    ws_id = self.get_next_ws()
            
            # Check if this specific WS can accommodate; fallback to another candidate if needed.
            if len(self.connections[ws_id]["instruments"]) >= self.max_per_connection:
                fallback_candidates = [
                    w for w in range(1, self.max_connections + 1)
                    if len(self.connections[w]["instruments"]) < self.max_per_connection
                    and (self.connections[w]["active"] or not any(self.connections[x]["active"] for x in range(1, self.max_connections + 1)))
                ]
                if not fallback_candidates:
                    return (False, None)
                ws_id = min(fallback_candidates, key=lambda w: len(self.connections[w]["instruments"]))
            
            # Add instrument
            self.connections[ws_id]["instruments"].add(token)
            self.instrument_to_ws[token] = ws_id
            
            return (True, ws_id)
    
    def remove_instrument(self, token: str) -> bool:
        """Remove instrument from its WS connection"""
        with self.lock:
            if token not in self.instrument_to_ws:
                return False
            
            ws_id = self.instrument_to_ws[token]
            self.connections[ws_id]["instruments"].discard(token)
            del self.instrument_to_ws[token]
            
            return True
    
    def get_ws_for_instrument(self, token: str) -> Optional[int]:
        """Get WS ID for an instrument"""
        with self.lock:
            return self.instrument_to_ws.get(token)
    
    def connect(self, ws_id: int, ws_handle) -> bool:
        """Mark a WS connection as active"""
        with self.lock:
            if ws_id not in self.connections:
                return False
            
            self.connections[ws_id]["active"] = True
            self.connections[ws_id]["handle"] = ws_handle
            self.connections[ws_id]["reconnect_attempts"] = 0
            self.connections[ws_id]["last_connected"] = time.time()
            
            return True
    
    def disconnect(self, ws_id: int, error: Optional[str] = None) -> bool:
        """Mark a WS connection as inactive"""
        with self.lock:
            if ws_id not in self.connections:
                return False
            
            self.connections[ws_id]["active"] = False
            self.connections[ws_id]["handle"] = None
            self.connections[ws_id]["last_error"] = error
            self.connections[ws_id]["reconnect_attempts"] += 1
            
            return True
    
    def is_connected(self, ws_id: int) -> bool:
        """Check if a WS is currently connected"""
        with self.lock:
            return self.connections[ws_id]["active"]
    
    def get_status(self) -> Dict:
        """Get overall status and per-connection stats"""
        with self.lock:
            ws_stats = {}
            total_instruments = 0
            connected_count = 0
            
            for ws_id in range(1, self.max_connections + 1):
                conn = self.connections[ws_id]
                count = len(conn["instruments"])
                total_instruments += count
                
                ws_stats[f"ws_{ws_id}"] = {
                    "active": conn["active"],
                    "instruments": count,
                    "utilization_percent": (count / self.max_per_connection) * 100,
                    "last_connected": conn["last_connected"],
                    "reconnect_attempts": conn["reconnect_attempts"],
                    "last_error": conn["last_error"]
                }
                
                if conn["active"]:
                    connected_count += 1
            
            return {
                "total_subscriptions": total_instruments,
                "max_capacity": self.max_total,
                "utilization_percent": (total_instruments / self.max_total) * 100,
                "connected_connections": connected_count,
                "total_connections": self.max_connections,
                "per_connection": ws_stats
            }
    
    def get_instruments_for_ws(self, ws_id: int) -> List[str]:
        """Get list of instruments for a specific WS"""
        with self.lock:
            return list(self.connections[ws_id]["instruments"])
    
    def should_reconnect(self, ws_id: int, max_attempts: int = 5) -> bool:
        """Check if a WS should attempt reconnection"""
        with self.lock:
            conn = self.connections[ws_id]
            if conn["active"]:
                return False  # Already connected
            
            if conn["reconnect_attempts"] >= max_attempts:
                return False  # Too many attempts
            
            return True
    
    def rebalance(self) -> Dict:
        """
        Rebalance instruments across connections if one becomes unavailable.
        Returns: {moved_count, details}
        """
        with self.lock:
            moved_count = 0
            details = []
            
            # Find disconnected WS with instruments
            for ws_id in range(1, self.max_connections + 1):
                if self.connections[ws_id]["active"]:
                    continue  # Skip connected
                
                instruments = list(self.connections[ws_id]["instruments"])
                if not instruments:
                    continue  # No instruments to move
                
                # Move instruments to least-loaded connected WS
                for token in instruments:
                    # Find best target WS
                    best_ws = None
                    best_count = float('inf')
                    
                    for target_ws in range(1, self.max_connections + 1):
                        if not self.connections[target_ws]["active"]:
                            continue  # Skip disconnected
                        
                        target_count = len(self.connections[target_ws]["instruments"])
                        if target_count < best_count:
                            best_count = target_count
                            best_ws = target_ws
                    
                    if best_ws and best_count < self.max_per_connection:
                        # Move
                        self.connections[ws_id]["instruments"].discard(token)
                        self.connections[best_ws]["instruments"].add(token)
                        self.instrument_to_ws[token] = best_ws
                        moved_count += 1
                        details.append(f"{token}: {ws_id} -> {best_ws}")
            
            return {
                "moved_count": moved_count,
                "details": details
            }


# Global WS manager
WS_MANAGER = WebSocketManager()

def get_ws_manager() -> WebSocketManager:
    """Get global WebSocket manager"""
    return WS_MANAGER
