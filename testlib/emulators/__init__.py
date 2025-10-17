# testlib/emulators/__init__.py
from .inverter_emulator import InverterEmulator
from .charger_emulator import ChargerEmulator, ChargerStatus, TransactionStatus

# Import OCPP emulator if available
try:
    from .charger_ocpp import ChargePoint, var as ocpp_var
    __all__ = ["InverterEmulator", "ChargerEmulator", "ChargerStatus", "TransactionStatus", "ChargePoint", "ocpp_var"]
except ImportError:
    __all__ = ["InverterEmulator", "ChargerEmulator", "ChargerStatus", "TransactionStatus"]