# testlib/emulators/charger_emulator.py
import time
import threading
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Callable, Optional, List
from enum import Enum

class ChargerStatus(Enum):
    AVAILABLE = "Available"
    PREPARING = "Preparing"
    CHARGING = "Charging"
    SUSPENDED_EVSE = "SuspendedEVSE"
    SUSPENDED_EV = "SuspendedEV"
    FINISHING = "Finishing"
    RESERVED = "Reserved"
    UNAVAILABLE = "Unavailable"
    FAULTED = "Faulted"

class TransactionStatus(Enum):
    ACTIVE = "Active"
    STOPPED = "Stopped"
    COMPLETED = "Completed"

class ChargerEmulator:
    """
    Python MQTT-based charger emulator
    Simulates EV charger behavior with realistic charging patterns
    """
    
    def __init__(self, options: Dict = None):
        self.options = {
            "charger_id": "CHG001",
            "tenant_id": 1,
            "model": "AC_22kW",
            "vendor": "TestVendor",
            "serial_number": None,
            "firmware_version": "1.0.0",
            "connectors": 2,
            "max_power": 22000,  # watts
            "logger": print,
            "on_data": lambda data: print("Charger Data:", data),
            "on_status_change": lambda status: print("Status:", status),
            "tick_interval_ms": 5000,  # 5 seconds
            **(options or {})
        }
        
        if not self.options["serial_number"]:
            self.options["serial_number"] = f"SN_{self.options['charger_id']}_{int(time.time())}"
        
        self.running = False
        self.thread = None
        self.status = ChargerStatus.AVAILABLE
        self.connectors = {}
        self.active_transactions = {}
        self.energy_delivered = {}
        
        # Initialize connectors
        for i in range(1, self.options["connectors"] + 1):
            self.connectors[i] = {
                "connector_id": i,
                "status": ChargerStatus.AVAILABLE,
                "error_code": "NoError",
                "info": "",
                "vendor_id": "",
                "vendor_error_code": ""
            }
    
    def start(self):
        """Start the charger emulator"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.options["logger"](f"ChargerEmulator {self.options['charger_id']} started")
        
        # Send boot notification
        self._send_boot_notification()
    
    def stop(self):
        """Stop the charger emulator"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        self.options["logger"](f"ChargerEmulator {self.options['charger_id']} stopped")
    
    def _run_loop(self):
        """Main emulator loop"""
        while self.running:
            self._tick()
            time.sleep(self.options["tick_interval_ms"] / 1000.0)
    
    def _tick(self):
        """Single emulator tick"""
        # Send periodic data
        self._send_periodic_data()
        
        # Update active transactions
        self._update_transactions()
        
        # Send meter values for active transactions
        for transaction_id, transaction in self.active_transactions.items():
            if transaction["status"] == TransactionStatus.ACTIVE:
                self._send_meter_values(transaction_id)
    
    def _send_boot_notification(self):
        """Send boot notification message"""
        boot_data = {
            "messageType": "BootNotification",
            "chargerId": self.options["charger_id"],
            "chargePointModel": self.options["model"],
            "chargePointVendor": self.options["vendor"],
            "chargePointSerialNumber": self.options["serial_number"],
            "firmwareVersion": self.options["firmware_version"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self.options["on_data"](boot_data)
        self.options["logger"](f"Sent boot notification for {self.options['charger_id']}")
    
    def _send_periodic_data(self):
        """Send periodic charger data"""
        charger_data = {
            "messageType": "ChargerPeriodicData",
            "chargerId": self.options["charger_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": self.status.value,
            "connectors": [
                {
                    "connectorId": conn_id,
                    "status": conn_data["status"].value,
                    "errorCode": conn_data["error_code"],
                    "info": conn_data["info"],
                }
                for conn_id, conn_data in self.connectors.items()
            ],
            "activeTransactions": len([
                t for t in self.active_transactions.values() 
                if t["status"] == TransactionStatus.ACTIVE
            ]),
            "totalEnergyDelivered": sum(self.energy_delivered.values()),
        }
        
        self.options["on_data"](charger_data)
    
    def start_transaction(self, connector_id: int, id_tag: str, meter_start: float = 0) -> str:
        """Start a charging transaction"""
        if connector_id not in self.connectors:
            raise ValueError(f"Invalid connector ID: {connector_id}")
        
        if self.connectors[connector_id]["status"] != ChargerStatus.AVAILABLE:
            raise ValueError(f"Connector {connector_id} not available")
        
        transaction_id = str(uuid.uuid4())
        
        # Update connector status
        self.connectors[connector_id]["status"] = ChargerStatus.PREPARING
        self._send_status_notification(connector_id)
        
        # Create transaction
        self.active_transactions[transaction_id] = {
            "transaction_id": transaction_id,
            "connector_id": connector_id,
            "id_tag": id_tag,
            "start_time": datetime.now(timezone.utc),
            "meter_start": meter_start,
            "meter_stop": None,
            "status": TransactionStatus.ACTIVE,
            "energy_delivered": 0.0,
            "current_power": 0.0,
        }
        
        if connector_id not in self.energy_delivered:
            self.energy_delivered[connector_id] = 0.0
        
        # Simulate preparation time
        threading.Timer(3.0, self._start_charging, args=[transaction_id]).start()
        
        self.options["logger"](f"Started transaction {transaction_id} on connector {connector_id}")
        
        # Send transaction started message
        transaction_data = {
            "messageType": "TransactionStarted",
            "chargerId": self.options["charger_id"],
            "transactionId": transaction_id,
            "connectorId": connector_id,
            "idTag": id_tag,
            "meterStart": meter_start,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self.options["on_data"](transaction_data)
        
        return transaction_id
    
    def _start_charging(self, transaction_id: str):
        """Begin the actual charging process"""
        if transaction_id not in self.active_transactions:
            return
        
        transaction = self.active_transactions[transaction_id]
        connector_id = transaction["connector_id"]
        
        # Update connector status to charging
        self.connectors[connector_id]["status"] = ChargerStatus.CHARGING
        self._send_status_notification(connector_id)
        
        # Set initial charging power (ramp up simulation)
        transaction["current_power"] = self.options["max_power"] * 0.1  # Start at 10%
        
        self.options["logger"](f"Charging started for transaction {transaction_id}")
    
    def stop_transaction(self, transaction_id: str, reason: str = "Local") -> bool:
        """Stop a charging transaction"""
        if transaction_id not in self.active_transactions:
            return False
        
        transaction = self.active_transactions[transaction_id]
        connector_id = transaction["connector_id"]
        
        # Update transaction
        transaction["status"] = TransactionStatus.STOPPED
        transaction["meter_stop"] = transaction["meter_start"] + transaction["energy_delivered"]
        transaction["stop_time"] = datetime.now(timezone.utc)
        
        # Update connector status
        self.connectors[connector_id]["status"] = ChargerStatus.FINISHING
        self._send_status_notification(connector_id)
        
        # Send transaction stopped message
        transaction_data = {
            "messageType": "TransactionStopped",
            "chargerId": self.options["charger_id"],
            "transactionId": transaction_id,
            "connectorId": connector_id,
            "meterStop": transaction["meter_stop"],
            "reason": reason,
            "energyDelivered": transaction["energy_delivered"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self.options["on_data"](transaction_data)
        
        # Simulate finishing time
        threading.Timer(2.0, self._finish_transaction, args=[transaction_id]).start()
        
        self.options["logger"](f"Stopped transaction {transaction_id}")
        return True
    
    def _finish_transaction(self, transaction_id: str):
        """Complete transaction cleanup"""
        if transaction_id not in self.active_transactions:
            return
        
        transaction = self.active_transactions[transaction_id]
        connector_id = transaction["connector_id"]
        
        # Update connector status back to available
        self.connectors[connector_id]["status"] = ChargerStatus.AVAILABLE
        self._send_status_notification(connector_id)
        
        # Mark transaction as completed
        transaction["status"] = TransactionStatus.COMPLETED
        
        self.options["logger"](f"Transaction {transaction_id} completed")
    
    def _update_transactions(self):
        """Update active transactions (simulate charging progress)"""
        for transaction_id, transaction in self.active_transactions.items():
            if transaction["status"] != TransactionStatus.ACTIVE:
                continue
            
            connector_id = transaction["connector_id"]
            if self.connectors[connector_id]["status"] != ChargerStatus.CHARGING:
                continue
            
            # Simulate power ramp-up and charging curve
            elapsed_minutes = (
                datetime.now(timezone.utc) - transaction["start_time"]
            ).total_seconds() / 60
            
            # Charging curve: ramp up to full power, then taper off
            if elapsed_minutes < 5:  # Ramp up phase
                power_factor = 0.1 + (elapsed_minutes / 5) * 0.9
            elif elapsed_minutes < 30:  # Full power phase
                power_factor = 1.0
            else:  # Taper phase
                power_factor = max(0.3, 1.0 - ((elapsed_minutes - 30) / 60) * 0.7)
            
            transaction["current_power"] = self.options["max_power"] * power_factor
            
            # Calculate energy delivered (kWh for this tick)
            tick_hours = (self.options["tick_interval_ms"] / 1000.0) / 3600.0
            energy_increment = (transaction["current_power"] / 1000.0) * tick_hours
            
            transaction["energy_delivered"] += energy_increment
            self.energy_delivered[connector_id] += energy_increment
    
    def _send_meter_values(self, transaction_id: str):
        """Send meter values for an active transaction"""
        if transaction_id not in self.active_transactions:
            return
        
        transaction = self.active_transactions[transaction_id]
        
        meter_data = {
            "messageType": "MeterValues",
            "chargerId": self.options["charger_id"],
            "transactionId": transaction_id,
            "connectorId": transaction["connector_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meterValue": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sampledValue": [
                        {
                            "value": str(round(transaction["energy_delivered"], 3)),
                            "context": "Sample.Periodic",
                            "measurand": "Energy.Active.Import.Register",
                            "unit": "kWh"
                        },
                        {
                            "value": str(round(transaction["current_power"], 1)),
                            "context": "Sample.Periodic", 
                            "measurand": "Power.Active.Import",
                            "unit": "W"
                        },
                        {
                            "value": str(round(transaction["current_power"] / 230, 2)),
                            "context": "Sample.Periodic",
                            "measurand": "Current.Import", 
                            "unit": "A"
                        },
                        {
                            "value": "230",
                            "context": "Sample.Periodic",
                            "measurand": "Voltage",
                            "unit": "V"
                        }
                    ]
                }
            ]
        }
        
        self.options["on_data"](meter_data)
    
    def _send_status_notification(self, connector_id: int):
        """Send status notification for a connector"""
        if connector_id not in self.connectors:
            return
        
        connector = self.connectors[connector_id]
        
        status_data = {
            "messageType": "StatusNotification",
            "chargerId": self.options["charger_id"],
            "connectorId": connector_id,
            "status": connector["status"].value,
            "errorCode": connector["error_code"],
            "info": connector["info"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self.options["on_data"](status_data)
        self.options["on_status_change"](connector["status"])
    
    def get_status(self) -> Dict:
        """Get current charger status"""
        return {
            "charger_id": self.options["charger_id"],
            "running": self.running,
            "status": self.status.value,
            "connectors": {
                conn_id: {
                    "status": conn_data["status"].value,
                    "error_code": conn_data["error_code"]
                }
                for conn_id, conn_data in self.connectors.items()
            },
            "active_transactions": {
                txn_id: {
                    "connector_id": txn["connector_id"],
                    "status": txn["status"].value,
                    "energy_delivered": txn["energy_delivered"],
                    "current_power": txn["current_power"]
                }
                for txn_id, txn in self.active_transactions.items()
                if txn["status"] == TransactionStatus.ACTIVE
            },
            "total_energy_delivered": sum(self.energy_delivered.values())
        }
    
    def get_transaction(self, transaction_id: str) -> Optional[Dict]:
        """Get transaction details"""
        return self.active_transactions.get(transaction_id)
    
    def get_active_transactions(self) -> Dict:
        """Get all active transactions"""
        return {
            txn_id: txn for txn_id, txn in self.active_transactions.items()
            if txn["status"] == TransactionStatus.ACTIVE
        }