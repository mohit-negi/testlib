# testlib/emulators/inverter_emulator.py
import time
import math
import threading
from datetime import datetime, timezone
from typing import Dict, Callable, Optional
import uuid
import json

try:
    from astral import LocationInfo
    from astral.sun import sun
except ImportError:
    print("Warning: astral not available. Install with: pip install astral")
    LocationInfo = None
    sun = None

class InverterEmulator:
    """
    Python equivalent of the JavaScript InverterEmulator
    Simulates solar inverter behavior with realistic power generation patterns
    """
    
    def __init__(self, options: Dict = None):
        self.options = {
            "inverter_id": "INV001",
            "tenant_id": 1,
            "lat": 28.6139,  # Delhi latitude
            "lon": 77.209,   # Delhi longitude
            "timezone": "Asia/Kolkata",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "fault_enabled": False,
            "mean_fault_interval": 7,  # days
            "fault_duration_min": 10,  # minutes
            "fault_duration_max": 60,  # minutes
            "logger": print,
            "on_data": lambda data: print("Data:", data),
            "initial_tick_interval_ms": 1000,  # Default to 1 real second per tick
            "mode": "inverter",  # 'inverter' or 'gridPower'
            **(options or {})
        }
        
        self.virtual_time = datetime.fromisoformat(self.options["start_time"].replace('Z', '+00:00'))
        self.simulation_start_time = self.virtual_time.timestamp() * 1000
        self.running = False
        self.thread = None
        self.fault_active = False
        self.next_fault_time = self._schedule_next_fault()
        self.fault_end_time = None
        self.current_tick_interval_ms = self.options["initial_tick_interval_ms"]
        
        self.energy_counters = {
            "daily": 0.0,
            "monthly": 0.0,
            "yearly": 0.0,
        }
        
        # Initialize grid power data array with 288 elements (5-minute intervals for 24 hours)
        self.grid_power_data = [0.0] * 288
        self.last_grid_power_update = None
        
    def _schedule_next_fault(self) -> Optional[datetime]:
        """Schedule the next fault occurrence"""
        if not self.options["fault_enabled"]:
            return None
        
        interval_minutes = self.options["mean_fault_interval"] * 24 * 60
        offset_minutes = int(math.floor(time.time() * 1000) % interval_minutes)
        
        fault_time = self.virtual_time.timestamp() + (offset_minutes * 60)
        return datetime.fromtimestamp(fault_time, tz=timezone.utc)
    
    def start(self):
        """Start the emulator"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.options["logger"](f"InverterEmulator started with tick interval: {self.current_tick_interval_ms}ms")
    
    def stop(self):
        """Stop the emulator"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        self.options["logger"]("InverterEmulator stopped")
    
    def update_tick_interval(self, new_interval_ms: int):
        """Update the tick interval for speed control"""
        if new_interval_ms <= 0:
            self.options["logger"](f"Invalid tick interval: {new_interval_ms}ms. Must be > 0.")
            return
        
        self.current_tick_interval_ms = new_interval_ms
        self.options["logger"](f"Updating tick interval to: {self.current_tick_interval_ms}ms")
    
    def get_current_time_warp_factor(self) -> float:
        """Get the current time warp factor"""
        if self.current_tick_interval_ms <= 0 or self.options["initial_tick_interval_ms"] <= 0:
            return 0
        return self.options["initial_tick_interval_ms"] / self.current_tick_interval_ms
    
    def _run_loop(self):
        """Main emulator loop"""
        while self.running:
            self._tick()
            time.sleep(self.current_tick_interval_ms / 1000.0)
    
    def _tick(self):
        """Single emulator tick - advance time by 5 minutes"""
        # Advance virtual time by 5 minutes
        self.virtual_time = datetime.fromtimestamp(
            self.virtual_time.timestamp() + (5 * 60), 
            tz=timezone.utc
        )
        
        # Reset counters at appropriate times
        if self.virtual_time.hour == 0 and self.virtual_time.minute == 0:
            self.energy_counters["daily"] = 0.0
            self.grid_power_data = [0.0] * 288
            
        if (self.virtual_time.day == 1 and 
            self.virtual_time.hour == 0 and 
            self.virtual_time.minute == 0):
            self.energy_counters["monthly"] = 0.0
            
        if (self.virtual_time.month == 1 and 
            self.virtual_time.day == 1 and 
            self.virtual_time.hour == 0 and 
            self.virtual_time.minute == 0):
            self.energy_counters["yearly"] = 0.0
        
        # Calculate solar position and power
        is_daylight, solar_power = self._calculate_solar_power()
        
        # Handle fault simulation
        self._update_fault_status()
        
        # Calculate grid power and other metrics
        grid_power = solar_power * 0.98 if not self.fault_active else 0
        reactive_power = grid_power * 0.05 if not self.fault_active else 0
        
        # Generate realistic grid voltages and currents
        grid_voltages = [
            230 + (time.time() % 10 - 5),  # ±5V variation
            231 + (time.time() % 8 - 4),   # ±4V variation
            229 + (time.time() % 6 - 3),   # ±3V variation
        ]
        
        grid_currents = [
            solar_power / voltage if voltage > 0 else 0 
            for voltage in grid_voltages
        ]
        
        # Update grid power data array
        current_index = self.virtual_time.hour * 12 + (self.virtual_time.minute // 5)
        if 0 <= current_index < 288:
            self.grid_power_data[current_index] = grid_power / 1000  # Convert to kW
        
        # Generate grid power periodic data if needed
        if (self.options["mode"] == "gridPower" and 
            (self.last_grid_power_update is None or 
             (self.virtual_time.timestamp() - self.last_grid_power_update.timestamp()) >= 300)):
            
            grid_power_periodic_data = {
                "gridPower": self.grid_power_data.copy(),
                "timestamp": self.virtual_time.isoformat(),
            }
            
            self.options["on_data"]({
                "type": "gridPowerPeriodic",
                "data": grid_power_periodic_data,
            })
            
            self.last_grid_power_update = self.virtual_time
        
        # Update energy counters
        if not self.fault_active:
            energy_increment = (solar_power * 5) / 60 / 1000  # kWh for 5 minutes
            self.energy_counters["daily"] += energy_increment
            self.energy_counters["monthly"] += energy_increment
            self.energy_counters["yearly"] += energy_increment
        
        # Calculate elapsed emulation time
        elapsed_emulation_time_ms = (
            self.virtual_time.timestamp() * 1000 - self.simulation_start_time
        )
        
        # Send inverter data if in inverter mode
        if self.options["mode"] == "inverter":
            inverter_data = {
                "gridStatus": 1,
                "pvStatus": 1 if is_daylight else 0,
                "inverterOn": 0 if self.fault_active else 1,
                "gridVoltages": grid_voltages,
                "gridCurrents": grid_currents,
                "gridFrequencies": [
                    50 + (time.time() % 0.2 - 0.1),  # ±0.1Hz variation
                    50 + (time.time() % 0.15 - 0.075),
                    50 + (time.time() % 0.1 - 0.05),
                ],
                "gridPower": grid_power,
                "reactivePower": reactive_power,
                "solarPower": solar_power,
                "dcLinkVoltage": 800 + (time.time() % 100 - 50),  # ±50V variation
                "residualCurrent": abs(time.time() % 1 - 0.5),  # 0-0.5A variation
                "vdcp": 400 + (time.time() % 50 - 25),  # ±25V variation
                "vdcn": 400 + (time.time() % 50 - 25),
                "loadCurrent": solar_power / 400 if solar_power > 0 else 0,
                "heatSinkTemperature": 45 + (time.time() % 20 - 10),  # ±10°C variation
                "gridInductorTemperature": 50 + (time.time() % 30 - 15),
                "pvInductorTemperature": 55 + (time.time() % 40 - 20),
                "rIsoN": abs(time.time() % 2000),  # 0-2000Ω variation
                "rIsoP": abs(time.time() % 2000),
                "faultCode": 1 if self.fault_active else 0,
                "vpv": [600 + (time.time() % 200 - 100)],  # ±100V variation
                "ipv": [solar_power / 600 if solar_power > 0 else 0],
                "dailyEnergy": self.energy_counters["daily"],
                "monthlyEnergy": self.energy_counters["monthly"],
                "yearlyEnergy": self.energy_counters["yearly"],
            }
            
            data = {
                "timestamp": self.virtual_time.isoformat(),
                "canComm": 1,
                "elapsedEmulationTimeMs": elapsed_emulation_time_ms,
                "inverterData": inverter_data,
            }
            
            self.options["on_data"](data)
    
    def _calculate_solar_power(self) -> tuple[bool, float]:
        """Calculate solar power based on time and location"""
        try:
            if LocationInfo and sun:
                # Use astral library for accurate sun calculations
                location = LocationInfo(
                    "Location", 
                    "Region", 
                    self.options["timezone"],
                    self.options["lat"], 
                    self.options["lon"]
                )
                
                sun_times = sun(location.observer, date=self.virtual_time.date())
                sunrise = sun_times['sunrise']
                sunset = sun_times['sunset']
                
                is_daylight = sunrise <= self.virtual_time <= sunset
            else:
                # Fallback: simple daylight calculation (6 AM to 6 PM)
                is_daylight = 6 <= self.virtual_time.hour <= 18
        except:
            # Fallback if astral fails
            is_daylight = 6 <= self.virtual_time.hour <= 18
        
        if not is_daylight or self.fault_active:
            return is_daylight, 0.0
        
        # Calculate solar power using sine wave approximation
        cloud_factor = 0.7 + (time.time() % 0.6)  # 0.7-1.3 cloud variation
        hour_angle = math.pi * ((self.virtual_time.hour - 6) / 12)
        peak_output = 5000  # watts
        
        solar_power = max(0, peak_output * math.sin(hour_angle) * cloud_factor)
        
        return is_daylight, solar_power
    
    def _update_fault_status(self):
        """Update fault simulation status"""
        if not self.options["fault_enabled"]:
            return
        
        current_time = self.virtual_time
        
        # Check if we should start a fault
        if (not self.fault_active and 
            self.next_fault_time and 
            current_time >= self.next_fault_time):
            
            duration_minutes = (
                self.options["fault_duration_min"] + 
                (time.time() % (self.options["fault_duration_max"] - 
                               self.options["fault_duration_min"]))
            )
            
            self.fault_end_time = datetime.fromtimestamp(
                current_time.timestamp() + (duration_minutes * 60),
                tz=timezone.utc
            )
            
            self.fault_active = True
            self.options["logger"](f"Fault injected at {current_time.isoformat()}")
        
        # Check if we should end a fault
        elif (self.fault_active and 
              self.fault_end_time and 
              current_time >= self.fault_end_time):
            
            self.fault_active = False
            self.next_fault_time = self._schedule_next_fault()
            self.options["logger"](f"Fault ended at {current_time.isoformat()}")
    
    def get_status(self) -> Dict:
        """Get current emulator status"""
        return {
            "running": self.running,
            "virtual_time": self.virtual_time.isoformat(),
            "fault_active": self.fault_active,
            "energy_counters": self.energy_counters.copy(),
            "mode": self.options["mode"],
            "tick_interval_ms": self.current_tick_interval_ms,
        }