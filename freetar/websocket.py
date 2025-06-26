import asyncio
import json
from typing import List, Dict
from datetime import datetime
import uuid

class Connection:
    def __init__(self, websocket):
        self.websocket = websocket
        self.connected_at = datetime.now()
        self.id = str(uuid.uuid4())  # Unique identifier
    
    def __eq__(self, other):
        return isinstance(other, Connection) and self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

class WebSocketManager:
    def __init__(self):
        self.connections: List[Connection] = []
    
    async def register(self, websocket):
        connection = Connection(websocket)
        self.connections.append(connection)
        print(f"Client connected. Total connections: {len(self.connections)}")
        try:
            await self.handle_connection(connection)
        finally:
            self._remove_connection(connection)
            print(f"Client disconnected. Total connections: {len(self.connections)}")
    
    def _remove_connection(self, connection):
        # Use ID-based removal to avoid comparison issues
        self.connections = [conn for conn in self.connections if conn.id != connection.id]
    
    async def handle_connection(self, connection):
        try:
            async for message in connection.websocket:
                data = json.loads(message)
                if data["type"] == "share_page":
                    print(f"Broadcasting page share: {data['url']}")
                    # Broadcast to all other connections
                    await self.broadcast(data, exclude=connection)
        except Exception as e:
            print(f"Error handling connection: {e}")
    
    async def broadcast(self, data: Dict, exclude: Connection = None):
        # Create a copy of connections list to avoid modification during iteration
        connections_copy = self.connections.copy()
        successful_broadcasts = 0
        
        for conn in connections_copy:
            if exclude and conn.id == exclude.id:
                continue
                
            try:
                await conn.websocket.send(json.dumps(data))
                successful_broadcasts += 1
            except Exception as e:
                print(f"Error broadcasting to connection {conn.id}: {e}")
                # Mark for removal by removing from original list
                self._remove_connection(conn)
        
        print(f"Successfully broadcasted to {successful_broadcasts} clients")

# Global WebSocket manager instance
ws_manager = WebSocketManager() 