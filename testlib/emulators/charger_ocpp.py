import asyncio
import logging
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print(" $ pip install we*sockets")
    import sys
    sys.exit(1)


from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call
from ocpp.v16.enums import Action,RegistrationStatus
from ocpp.v16 import datatypes as dt
from ocpp.v16 import enums
from ocpp.v16 import call_result
from ocpp.routing import on,after
import time
from inputimeout import inputimeout,TimeoutOccurred
logging.basicConfig(level=logging.INFO)

class var():
    transactionId : int
    idTag : str
    transactionMap : dict = {}
    chargingOnGoing : bool = False
    voltage : int
    current : int
    power : int 
    energy : int
    soc : int
    start_time : time
    vendorId : str
    messageId : str
    data : str
    evccId: str
    
var.idTag = "5887d3"
var.voltage =  260
var.current =  22
var.power = var.voltage*var.current 
var.energy =  2
var.soc = 0
var.start_time =time.time()
var.vendorId = "PyramidElectronics"
var.messageId = "AutoChargeRequest"
var.data = "Start"
var.evccId = "CH01CQ1233"

class ChargePoint(cp):
    
    async def localTrigger(self):
       while(not var.chargingOnGoing):
            try:
                if inputimeout(prompt="Trigger Authorize Request: ", timeout=3):
                    await self.send_authorize(var.idTag)
            except TimeoutOccurred:
                await asyncio.sleep(5)

    async def autoChargeTrigger(self):
       while(not var.chargingOnGoing):
            try:
                if inputimeout(prompt="Trigger AutoCharge: ", timeout=3):
                    await self.send_authorize(var.evccId)
            except TimeoutOccurred:
                await asyncio.sleep(5)            
                
        
    async def send_boot_notification(self):
        request = call.BootNotification(
            charge_point_model="pevcms_ccs1", charge_point_vendor="Pyramid electronics"
        )
        response = await self.call(request)
        
        if response.status == RegistrationStatus.accepted:
            print("Connected to central system.")
            # await self.send_statusNotfication(connectorId=0,connectorStatus=enums.ChargePointStatus.faulted)
            await self.send_statusNotfication(connectorId=1,connectorStatus=enums.ChargePointStatus.available)
            await self.send_statusNotfication(connectorId=2,connectorStatus=enums.ChargePointStatus.available)
            await self.send_heartbeat(response.interval)
            
    async def send_heartbeat(self,interval):
        request = call.HeartbeatPayload()
        while(True):
            await self.call(request)
            await asyncio.sleep(interval) 
            
    async def send_statusNotfication(self, connectorId,connectorStatus):
        
        request = call.StatusNotification(
            connector_id=connectorId,
            error_code=enums.ChargePointErrorCode.no_error,
            status=connectorStatus
            )
        response = await self.call(request)
        
    async def send_authorize(self, idTag):
        request = call.AuthorizePayload(id_tag=idTag)
        response = await self.call(request) 
        print("At authorize ",response)
        if response.id_tag_info.get('status') == enums.AuthorizationStatus.accepted:
            await self.send_statusNotfication(connectorId=1,connectorStatus=enums.ChargePointStatus.preparing)
            await asyncio.sleep(10)
            await self.send_startTransaction(connectorId=1,idTag=idTag)
            # await self.send_startTransaction(connectorId=1,idTag=idTag)
        else:
            print("authorization failed")
            
    async def send_startTransaction(self,connectorId,idTag):
        request = call.StartTransactionPayload(
            connector_id=connectorId,
            id_tag=idTag,
            meter_start=0,
            timestamp=datetime.utcnow().isoformat()+'Z'
        )
        print("Sending start transaction for connector:",connectorId)
        response = await self.call(request)
        var.transactionId = int(response.transaction_id)
        var.transactionMap[int(response.transaction_id)] = connectorId
        
        
        if response.id_tag_info.get('status') == enums.AuthorizationStatus.accepted:
            print("Accepted received for the ",connectorId, "for the transaction id:",var.transactionId)
            var.chargingOnGoing = True
            print("waiting for 3 seconds before sending status notification as charging")
            await asyncio.sleep(3)
            await self.send_statusNotfication(connectorId=connectorId,connectorStatus=enums.ChargePointStatus.charging)

            var.start_time = time.time()
            while(var.chargingOnGoing):
                await self.try_send_meterValues(connectorId=1)
                try:
                    if inputimeout(prompt="Trigger StopTx Request: ", timeout=3):
                        await self.send_stopTransaction()
                except TimeoutOccurred:
                    pass
            
                await asyncio.sleep(27)
            
    async def try_send_meterValues(self,connectorId):
        end_time = time.time()
        elapsed_time_hours = (end_time - var.start_time) / 3600 
        var.energy = int(var.power*elapsed_time_hours)
        var.soc += 1
    
        request = call.MeterValues(
            connector_id=connectorId,
            transaction_id=var.transactionId,
            meter_value=[{
                    "timestamp": datetime.utcnow().isoformat()+'Z',
                    "sampledValue": [
                    {"value":str(var.energy), "context":"Sample.Periodic", "measurand":"Energy.Active.Import.Register", "unit":"Wh"},
                    {"value":str(var.power), "context":"Sample.Periodic", "measurand":"Power.Active.Import", "unit":"W"},
                    {"value":str(var.current), "context":"Sample.Periodic", "measurand":"Current.Import", "unit":"A"},
                    {"value":str(var.soc), "context":"Sample.Periodic", "measurand":"SoC", "unit":"Percent"},
                    {"value":str(var.voltage), "context":"Sample.Periodic", "measurand":"Voltage", "unit":"V"}
                    ]
                }]
        )

        response = await self.call(request)
        print("-----------------charging session -------------------------",var.transactionId)
        print("---------- :",var.energy)
        print("---------- :",var.power)
        print("---------- :",var.current)
        print("---------- :",var.voltage)
        print("---------- :",var.soc)
        print("-----------------charging session -------------------------",var.transactionId)
    
    async def send_stopTransaction(self):
        print("Waiting for 3 seconds before sending stop transaction")
        print("Sending stop transaction for transaction id:",var.transactionId)
        await asyncio.sleep(3)
        request = call.StopTransactionPayload(
            meter_stop=int(var.energy),
            timestamp=datetime.utcnow().isoformat()+'Z',
            reason=enums.Reason.local,
            id_tag=var.idTag,
            transaction_id=var.transactionId
        )
        connectorId = var.transactionMap.get(var.transactionId)
        response = await self.call(request)
        var.chargingOnGoing = False
        var.energy = 0
        var.soc = 0
        print("Stopped transaction for connector:",connectorId, "waiting for 2 seconds before sending status notification")
        await asyncio.sleep(2)
        await self.send_statusNotfication(connectorId=connectorId,connectorStatus=enums.ChargePointStatus.finishing)
        print("Connector status sent to finishing for waiting for 2 seconds before sending status notification")

        await asyncio.sleep(2)
        await self.send_statusNotfication(connectorId=connectorId,connectorStatus=enums.ChargePointStatus.available)

        
        
    @on(Action.RemoteStartTransaction)
    async def on_remoteStartTransaction(self,id_tag,**kwargs):
        connectorId = kwargs.get("connector_id")
        dur = 5
        print("Remote start arrived for connector:",connectorId, "------------ wating ",dur," seconds")
        await asyncio.sleep(dur)
        return call_result.RemoteStartTransactionPayload(status=enums.RemoteStartStopStatus.accepted)
    @after(Action.RemoteStartTransaction)
    async def after_remoteStartTransaction(self,id_tag,**kwargs):
        dur = 3;
        connectorId = kwargs.get("connector_id")
        print("Remote start accepted sent for ",connectorId, "------------ wating ",dur," seconds")
        await asyncio.sleep(3)
        await self.send_statusNotfication(connectorId=connectorId,connectorStatus=enums.ChargePointStatus.preparing)
        print("connector",connectorId, "--status preparing sent ---------- wating ",dur," seconds")
        await asyncio.sleep(3)
        await self.send_startTransaction(connectorId=connectorId,idTag=id_tag)
        
    @on(Action.RemoteStopTransaction)
    async def on_remoteStopTransaction(self,transaction_id, **kwargs):
        print("Remote stop arrived for transaction id:",transaction_id, "------------ wating 5 seconds")
        await asyncio.sleep(5)
        if transaction_id == var.transactionId:
            print("Transactuin stopped")
            return call_result.RemoteStopTransactionPayload(status=enums.RemoteStartStopStatus.accepted)
        else:
            return call_result.RemoteStopTransactionPayload(status=enums.RemoteStartStopStatus.rejected)
    @after(Action.RemoteStopTransaction)
    async def after_remoteStopTransaction(self,transaction_id, **kwargs):
        await self.send_stopTransaction()

    @on(Action.DataTransfer)
    async def on_dataTransfer(self,**kwargs):
        return call_result.DataTransferPayload(status=enums.DataTransferStatus.accepted)
    @after(Action.DataTransfer)
    async def after_datatransfer(self,**kwargs):
        print(kwargs)
        print(kwargs.get('data'))
        if kwargs.get('data') == 'Start':
            await self.auto_charge()

    async def auto_charge(self):
        request = call.DataTransferPayload(
            vendor_id= "PyramidElectronics",
            message_id= "AutoChargeGunStatus",
            data= "GunPluggedIn"
        )
        print("at autocharge ")
        response = await self.call(request)  
        print("------",response.status)
        if(response.status == enums.DataTransferStatus.accepted):
            await self.auto_charge2()

    async def auto_charge2(self):
        request = call.DataTransferPayload(
            vendor_id= "PyramidElectronics",
            message_id= "AutoChargeEVCCID",
            data= var.evccId
        )
        response = await self.call(request)  

        if(response.status == enums.DataTransferStatus.accepted):
            print("hello")

        
        
async def main():
    
    async with websockets.connect(
        "ws://a285870195a5d4f9da391367ccd284a7-2128649528.ap-south-1.elb.amazonaws.com:8080/ZTB00741001001I2500067:8080"
    ) as ws:




        cp = ChargePoint("ZTB00741001001I2500067", ws)

        await asyncio.gather(cp.start(), cp.send_boot_notification(), cp.localTrigger(), cp.autoChargeTrigger())


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())     