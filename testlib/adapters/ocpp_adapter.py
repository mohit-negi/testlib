# testlib/adapters/ocpp_adapter.py
import asyncio
from typing import Dict, Optional
import sys
import os

# Add the emulators directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emulators'))

try:
    from charger_ocpp import ChargePoint, var
    import websockets
except ImportError as e:
    print(f"Warning: OCPP emulator dependencies not available: {e}")
    ChargePoint = None
    var = None
    websockets = None

class OCPPAdapter:
    def __init__(self, websocket_url: str = None):
        self._simulators: Dict[str, ChargePoint] = {}
        self._websocket_url = websocket_url or "ws://a285870195a5d4f9da391367ccd284a7-2128649528.ap-south-1.elb.amazonaws.com:8080"
        self._active_transactions: Dict[str, Dict] = {}  # Track active transactions

    async def _ensure_connected(self, charger_id: str):
        """Ensure charger is connected via WebSocket"""
        if ChargePoint is None:
            raise RuntimeError("OCPP emulator dependencies not available")
            
        if charger_id not in self._simulators:
            # Create WebSocket connection for this charger
            ws_url = f"{self._websocket_url}/{charger_id}:8080"
            try:
                ws = await websockets.connect(ws_url)
                cp = ChargePoint(charger_id, ws)
                self._simulators[charger_id] = cp
                
                # Start the charger (boot notification, etc.)
                await cp.send_boot_notification()
                
            except Exception as e:
                raise RuntimeError(f"Failed to connect charger {charger_id}: {e}")
                
        return self._simulators[charger_id]

    def create(self, resource_type: str, data: Dict) -> str:
        """Start a transaction = 'create' a transaction resource"""
        if resource_type == "charger":
            return self._create_charger(data)
        elif resource_type == "transaction":
            return self._create_transaction(data)
        else:
            raise ValueError("OCPP adapter supports 'charger' and 'transaction' resource types")
    
    def _create_charger(self, data: Dict) -> str:
        """Initialize a charger connection"""
        charger_id = data.get("charger_id") or data.get("id")
        if not charger_id:
            raise ValueError("charger_id is required for charger creation")
        
        # Run async connection in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            cp = loop.run_until_complete(self._ensure_connected(charger_id))
            return charger_id
        finally:
            loop.close()
    
    def _create_transaction(self, data: Dict) -> str:
        """Start a charging transaction"""
        charger_id = data["charger_id"]
        user_id = data.get("user_id", data.get("id_tag", "default_user"))
        
        # Run async in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            cp = loop.run_until_complete(self._ensure_connected(charger_id))
            
            # Set the user ID in the global var for the emulator
            if var:
                var.idTag = user_id
            
            # Trigger authorization and start transaction
            loop.run_until_complete(cp.send_authorize(user_id))
            
            # Generate transaction ID
            txn_id = f"txn_{charger_id}_{user_id}_{len(self._active_transactions)}"
            
            # Track the transaction
            self._active_transactions[txn_id] = {
                "charger_id": charger_id,
                "user_id": user_id,
                "status": "active"
            }
            
            return txn_id
            
        except Exception as e:
            raise RuntimeError(f"Failed to start transaction: {e}")
        finally:
            loop.close()

    def delete(self, resource_type: str, resource_id: str) -> bool:
        """Delete/stop a resource"""
        if resource_type == "transaction":
            return self._delete_transaction(resource_id)
        elif resource_type == "charger":
            return self._delete_charger(resource_id)
        else:
            return False
    
    def _delete_transaction(self, resource_id: str) -> bool:
        """Stop a charging transaction"""
        if resource_id not in self._active_transactions:
            return False
            
        transaction = self._active_transactions[resource_id]
        charger_id = transaction["charger_id"]
        
        if charger_id in self._simulators:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                cp = self._simulators[charger_id]
                # Stop the transaction using the emulator's method
                loop.run_until_complete(cp.send_stopTransaction())
                
                # Mark transaction as stopped
                self._active_transactions[resource_id]["status"] = "stopped"
                
                return True
            except Exception as e:
                print(f"Error stopping transaction {resource_id}: {e}")
                return False
            finally:
                loop.close()
        return False
    
    def _delete_charger(self, charger_id: str) -> bool:
        """Disconnect a charger"""
        if charger_id in self._simulators:
            # Stop all active transactions for this charger first
            for txn_id, txn in list(self._active_transactions.items()):
                if txn["charger_id"] == charger_id and txn["status"] == "active":
                    self._delete_transaction(txn_id)
            
            # Remove the simulator
            del self._simulators[charger_id]
            return True
        return False

    def read(self, resource_type: str, resource_id: str) -> Dict:
        """Read resource status"""
        if resource_type == "transaction":
            if resource_id in self._active_transactions:
                return self._active_transactions[resource_id]
            else:
                raise ValueError(f"Transaction {resource_id} not found")
        elif resource_type == "charger":
            if resource_id in self._simulators:
                return {
                    "charger_id": resource_id,
                    "status": "connected",
                    "active_transactions": [
                        txn_id for txn_id, txn in self._active_transactions.items()
                        if txn["charger_id"] == resource_id and txn["status"] == "active"
                    ]
                }
            else:
                raise ValueError(f"Charger {resource_id} not found")
        else:
            raise NotImplementedError(f"Read not supported for resource type: {resource_type}")

    def update(self, resource_type: str, resource_id: str, data: Dict):
        """Update resource (limited support)"""
        if resource_type == "transaction":
            if resource_id in self._active_transactions:
                self._active_transactions[resource_id].update(data)
                return self._active_transactions[resource_id]
            else:
                raise ValueError(f"Transaction {resource_id} not found")
        else:
            raise NotImplementedError(f"Update not supported for resource type: {resource_type}")
    
    def get_active_transactions(self) -> Dict:
        """Get all active transactions"""
        return {k: v for k, v in self._active_transactions.items() if v["status"] == "active"}
    
    def get_connected_chargers(self) -> List[str]:
        """Get list of connected charger IDs"""
        return list(self._simulators.keys())