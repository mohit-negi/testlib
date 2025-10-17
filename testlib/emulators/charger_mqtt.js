/* eslint-disable no-unused-vars */
import { useState, useCallback, useRef, useEffect } from "react";
import mqtt from "mqtt";
import data from "./mockData"; // Assuming this is used by handlers remaining in MqttCharger
import { v4 as uuidv4 } from "uuid";
import InverterEmulator from "./simulator/inverteremulator";
import ConnectionSettingsInternal from "./components/ConnectionSettingsInternal";
import MessageControls from "./components/MessageControls";
import MessageLog from "./components/MessageLog";
import Button from "@mui/material/Button";
import EnergyDisplay from "./components/EnergyDisplay";
import SpeedControls from "./components/SpeedControls";

const MQTTCharger = () => {
  const [client, setClient] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [messageStatus, setMessageStatus] = useState(false); // Used by MessageControls and handleOutgoingBootupSequence
  const emulatorRef = useRef(null);
  const [emulatorRunning, setEmulatorRunning] = useState(false);
  const [emulatorData, setEmulatorData] = useState(null);
  const [emulatorStartTime, setEmulatorStartTime] = useState(null);
  const [currentSpeedFactor, setCurrentSpeedFactor] = useState(2); // Default speed factor 2x
  const [gridPowerData, setGridPowerData] = useState(null);
  const [emulatorMode, setEmulatorMode] = useState(null); // 'inverter' or 'gridPower' or null

  const [connectionSettings, setConnectionSettings] = useState({
    name: "charger",
    clientId: "mqttx_" + uuidv4(),
    host: "13.127.194.179",
    port: "8000",
    username: "vikash",
    password: "password",
    ssl: false,
    chargerId: "INV-12345",
    publish: "inverterData234",
    subscribe: "serverToInverter234",
  });

  const MAX_LOG_MESSAGES = 500;

  const addMessage = useCallback((type, content) => {
    setMessages((prevMessages) => {
      let messageTimestamp;
      // Check if the message is from the emulator and has its own timestamp
      if (type === "EmulatorData" && content && content.timestamp) {
        messageTimestamp = content.timestamp; // Use emulator's virtual time
      } else {
        messageTimestamp = new Date().toISOString(); // Use current real time for other messages
      }

      const newMessage = {
        timestamp: messageTimestamp,
        type,
        content:
          typeof content === "object" ? JSON.stringify(content) : content,
      };
      const updatedMessages = [...prevMessages, newMessage];
      if (updatedMessages.length > MAX_LOG_MESSAGES) {
        return updatedMessages.slice(updatedMessages.length - MAX_LOG_MESSAGES);
      }
      return updatedMessages;
    });
  }, []);

  // Function to clear messages
  const handleClearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const requestMessageFormate = useCallback((messageName, data) => {
    const uuid = uuidv4();
    const timestamp = new Date().toISOString();
    const messageData = {
      ...data,
      timestamp: data.timestamp || timestamp,
    };
    return ["2", uuid, messageName, messageData];
  }, []);

  const publishMessage = useCallback(
    (payload) => {
      if (!client || !isConnected) {
        addMessage("Error", "Client not connected. Cannot publish message.");
        return;
      }
      const topic = `${connectionSettings.publish}/${connectionSettings.chargerId}`;
      client.publish(topic, JSON.stringify(payload), { qos: 1 }, (error) => {
        if (error) {
          addMessage(
            "Error",
            `Publish error to topic ${topic}: ${error.message}`
          );
        } else {
          addMessage("Sent", payload);
        }
      });
    },
    [client, isConnected, connectionSettings, addMessage]
  );

  const startEmulator = useCallback(
    (mode) => {
      if (emulatorRef.current) {
        addMessage("System", "Emulator is already running. Stop it first.");
        return;
      }

      // Start from 8 AM today
      const startDate = new Date();
      startDate.setHours(8, 0, 0, 0); // Set to 8 AM
      const startTimeISO = startDate.toISOString();

      setEmulatorStartTime(startTimeISO);
      setEmulatorMode(mode);
      const initialIntervalMs = 1000 / currentSpeedFactor;

      emulatorRef.current = new InverterEmulator({
        inverterId: "INV001",
        lat: 28.6139, // Delhi's latitude
        lon: 77.209, // Delhi's longitude
        timezone: "Asia/Kolkata", // IST timezone
        startTime: startTimeISO,
        faultEnabled: true,
        meanFaultInterval: 7,
        faultDurationMin: 10,
        faultDurationMax: 60,
        logger: console,
        mode: mode, // Pass the mode to the emulator
        onData: (msg) => {
          console.log("Emulator data received:", msg);

          if (msg.type === "gridPowerPeriodic") {
            // Handle grid power periodic data
            setGridPowerData(msg.data);
            const formattedMessage = requestMessageFormate(
              "GridPowerPeriodicData",
              msg.data
            );
            publishMessage(formattedMessage);
          } else {
            // Handle regular inverter data
            setEmulatorData({
              payload: msg.inverterData,
              timestamp: msg.timestamp,
              elapsedEmulationTimeMs: msg.elapsedEmulationTimeMs,
            });
            console.log("Updated emulatorData state:", {
              payload: msg.inverterData,
              timestamp: msg.timestamp,
              elapsedEmulationTimeMs: msg.elapsedEmulationTimeMs,
            });
            // Construct payload with original keys and virtual timestamp
            const payloadWithVirtualTimestamp = {
              timestamp: msg.timestamp,
              canComm: msg.canComm,
              inverterData: msg.inverterData,
            };
            const formattedMessage = requestMessageFormate(
              "InverterPeriodicData",
              payloadWithVirtualTimestamp
            );
            publishMessage(formattedMessage);
          }
        },
        initialTickIntervalMs: initialIntervalMs,
      });

      emulatorRef.current.start();
      addMessage(
        "System",
        `${mode === "inverter" ? "Inverter" : "Grid Power"} emulator started.`
      );
      setEmulatorRunning(true);
    },
    [addMessage, currentSpeedFactor, requestMessageFormate, publishMessage]
  );

  const stopEmulator = useCallback(() => {
    if (emulatorRef.current) {
      emulatorRef.current.stop();
      emulatorRef.current = null;
      addMessage("System", "Emulator stopped.");
      setEmulatorRunning(false);
      setEmulatorMode(null);
    }
  }, [addMessage]);

  const handleSetEmulatorSpeed = useCallback(
    (newIntervalMs) => {
      if (emulatorRef.current) {
        emulatorRef.current.updateTickInterval(newIntervalMs);
        const newFactor = 1000 / newIntervalMs;
        setCurrentSpeedFactor(newFactor);
        addMessage(
          "System",
          `Emulator speed set to ${newFactor}x (${newIntervalMs}ms interval).`
        );
      }
    },
    [addMessage]
  );

  const responseMessageFormate = useCallback((uuid, data) => {
    const timestamp = new Date().toISOString();
    const messageData = {
      ...data,
      timestamp: data.timestamp || timestamp,
    };
    return ["3", uuid, messageData];
  }, []);

  const errorMessageFormate = useCallback((errorDetail) => {
    const uuid = uuidv4();
    return [
      4,
      uuid,
      "GenericError",
      "Any other error not covered by the more specific error codes in this table",
      errorDetail,
    ];
  }, []);

  const connectToBroker = useCallback(() => {
    try {
      const protocol = connectionSettings.ssl ? "wss" : "ws"; // Corrected for wss
      const port =
        connectionSettings.port || (connectionSettings.ssl ? "8084" : "8083"); // Default port if not specified
      const brokerUrl = `${protocol}://${connectionSettings.host}:${port}/mqtt`;

      const mqttClient = mqtt.connect(brokerUrl, {
        clientId: connectionSettings.clientId,
        username: connectionSettings.username,
        password: connectionSettings.password,
        keepalive: 60,
        clean: true,
        protocolVersion: 5, // Optional: specify MQTT version if needed
        // rejectUnauthorized: false, // Only if using self-signed SSL certificates
      });

      mqttClient.on("connect", () => {
        setIsConnected(true);
        addMessage("System", "Connected to MQTT broker");
        const topic = `${connectionSettings.subscribe}/${connectionSettings.chargerId}`;
        addMessage("System", `Subscribing to topic ${topic}`);
        mqttClient.subscribe(topic, { qos: 1 }, (error) => {
          // Using object for options
          if (error) {
            addMessage(
              "System",
              `Failed to subscribe to topic ${topic}: ${error.message}`
            );
            return;
          }
          addMessage("System", `Subscribed to topic ${topic}`);
        });
      });

      mqttClient.on("message", (topic, message) => {
        try {
          const payload = JSON.parse(message.toString());
          if (!Array.isArray(payload) || payload.length < 3) {
            addMessage(
              "Error",
              `Invalid payload format: ${JSON.stringify(
                payload
              )} on topic ${topic}`
            );
            return;
          }

          const type = payload[0];
          const uuid = payload[1];
          addMessage("Receive", { topic, uuid, type, payload }); // Log entire received payload for context

          switch (type) {
            case 2: // Request from server
              const action = payload[2];
              const requestData = payload[3];
              // addMessage("Receive", { uuid, action, requestData }); // Already logged above
              const { component, id } = requestData;
              let responsePayload = null;
              switch (component) {
                case "1":
                  responsePayload =
                    id === 0 ? data.componentStatus1 : data.componentStatus1_1;
                  break;
                case "2":
                  responsePayload =
                    id === 0 ? data.componentStatus2 : data.componentStatus2_1;
                  break;
                case "3":
                  responsePayload = data.componentStatus3;
                  break;
                case "4":
                  responsePayload = data.componentStatus4;
                  break;
                default:
                  const errorMsg = errorMessageFormate(
                    `Invalid request with component id: ${component}`
                  );
                  publishMessage(errorMsg); // Send error message back
                  return; // Exit early
              }
              if (responsePayload) {
                const response = responseMessageFormate(uuid, responsePayload);
                publishMessage(response);
              }
              break;
            case 3: // Response from server
              // const responseData = payload[2];
              // addMessage("Receive", { uuid, responseData }); // Already logged above
              setMessageStatus(true); // Indicate a response was received, potentially for boot sequence
              break;
            case 4: // Error from server
              // const errorCode = payload[2];
              // const errorDescription = payload[3];
              // const errorDetails = payload[4] || {};
              // addMessage("Error", { uuid, errorCode, errorDescription, errorDetails }); // Already logged
              setMessageStatus(false);
              // handleIncomingError(uuid, errorCode, errorDescription, errorDetails); // Already logged
              break;
            default:
              addMessage(
                "Error",
                `Unknown message type: ${type} on topic ${topic}`
              );
              break;
          }
        } catch (e) {
          addMessage(
            "Error",
            `Failed to process message: ${
              e.message
            }. Original: ${message.toString()}`
          );
        }
      });

      mqttClient.on("error", (err) => {
        setError(`Connection error: ${err.message}`); // This will trigger useEffect for error
        setIsConnected(false); // Ensure connected state is false
      });

      mqttClient.on("close", () => {
        setIsConnected(false);
        addMessage("System", "Disconnected from broker");
      });

      mqttClient.on("offline", () => {
        setIsConnected(false);
        addMessage("System", "Client went offline");
      });

      setClient(mqttClient);
    } catch (err) {
      setError(`Failed to connect: ${err.message}`); // This will trigger useEffect for error
    }
  }, [
    connectionSettings,
    addMessage,
    errorMessageFormate,
    responseMessageFormate,
    publishMessage,
  ]); // Added missing dependencies

  const handleIncomingError = useCallback(
    (uuid, errorCode, errorDescription, message) => {
      // This function was empty, if specific logic is needed, it can be added here.
      // For now, errors are logged via the 'message' event handler.
      addMessage("Error", {
        uuid,
        errorCode,
        errorDescription,
        details: message,
      });
    },
    [addMessage]
  );

  const handleOutgoingBootupSequence = useCallback(async () => {
    if (!client || !isConnected) {
      addMessage(
        "Error",
        "Client not connected. Cannot start bootup sequence."
      );
      return;
    }

    const configMsg = requestMessageFormate(
      "ConfigurationData",
      data.configurationData
    );
    const chargerPeriodicMsg = requestMessageFormate(
      "ChargerPeriodicData",
      data.chargerPreodicData
    ); // Corrected: chargerPreodicData
    const pcmPeriodicMsg = requestMessageFormate(
      "PCMPeriodicData",
      data.PCMPeriodicData
    );

    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    try {
      addMessage("System", "Starting Boot Up Sequence...");
      setMessageStatus(true); // Indicate sequence is running

      publishMessage(configMsg);
      await delay(15000); // Wait for potential response or just timed delay

      // Loop while messageStatus is true, allowing external stop
      // This loop's logic might need review based on how `messageStatus` is controlled by server responses.
      // For now, it sends two messages periodically.
      let count = 0; // Limiter for example
      while (messageStatus && count < 5) {
        // Added count to prevent infinite loop if messageStatus isn't reset
        if (!isConnected) {
          addMessage("Error", "Disconnected during bootup sequence.");
          setMessageStatus(false);
          break;
        }
        publishMessage(chargerPeriodicMsg);
        await delay(30000);

        if (!messageStatus || !isConnected) {
          // Check again before next publish
          if (messageStatus)
            addMessage(
              "System",
              "Bootup sequence interrupted or client disconnected."
            );
          setMessageStatus(false);
          break;
        }

        publishMessage(pcmPeriodicMsg);
        await delay(30000);
        count++;
      }
      if (messageStatus) {
        // If loop finished due to count
        addMessage(
          "System",
          "Boot Up Sequence part completed (iteration limit)."
        );
      } else {
        addMessage("System", "Boot Up Sequence stopped or completed.");
      }
      // setMessageStatus(false); // Ensure status is reset if loop finishes naturally
    } catch (error) {
      addMessage("Error", `Bootup sequence error: ${error.message}`);
      setMessageStatus(false);
    }
  }, [
    client,
    isConnected,
    publishMessage,
    requestMessageFormate,
    addMessage,
    messageStatus,
  ]); // Added messageStatus

  const handleOutgoingRequest = useCallback(
    (messageName) => {
      let messagePayload = null;
      switch (messageName) {
        case "ConfigurationData":
          messagePayload = data.configurationData;
          break;
        case "ChargerPeriodicData":
          messagePayload = data.chargerPreodicData;
          break;
        case "PCMPeriodicData":
          messagePayload = data.PCMPeriodicData;
          break;
        case "ChargingSession":
          messagePayload = data.ChargingSession;
          break;
        case "InverterPeriodicData":
          if (!emulatorRef.current || emulatorMode !== "inverter") {
            addMessage(
              "Error",
              "Inverter emulator must be running to send InverterPeriodicData"
            );
            return;
          }
          // The emulator will handle sending the data through its onData callback
          return;
        case "GridPowerPeriodicData":
          if (!emulatorRef.current || emulatorMode !== "gridPower") {
            addMessage(
              "Error",
              "Grid Power emulator must be running to send GridPowerPeriodicData"
            );
            return;
          }
          // The emulator will handle sending the data through its onData callback
          return;
        case "StartInverterEmulator":
          startEmulator("inverter");
          return;
        case "StartGridPowerEmulator":
          startEmulator("gridPower");
          return;
        default:
          addMessage("Error", `Unknown outgoing request type: ${messageName}`);
          return;
      }
      if (messagePayload === null) {
        addMessage("Error", `No data for outgoing request: ${messageName}`);
        return;
      }
      const request = requestMessageFormate(messageName, messagePayload);
      publishMessage(request);
    },
    [
      publishMessage,
      requestMessageFormate,
      addMessage,
      startEmulator,
      emulatorMode,
    ]
  );

  const handleOutgoingResponse = useCallback(
    (messageName) => {
      let messagePayload = null;
      const localUuid = uuidv4(); // Generate UUID for responses not tied to an incoming request
      switch (messageName) {
        case "powerConverterModuleAll":
          messagePayload = data.componentStatus1;
          break;
        case "powerConverterModule":
          messagePayload = data.componentStatus1_1;
          break;
        case "communicationControllerAll":
          messagePayload = data.componentStatus2;
          break;
        case "communicationController":
          messagePayload = data.componentStatus2_1;
          break;
        case "controllerInfo":
          messagePayload = data.componentStatus3;
          break;
        case "gridStatus":
          messagePayload = data.componentStatus4;
          break;
        default:
          addMessage("Error", `Unknown outgoing response type: ${messageName}`);
          return;
      }
      if (messagePayload === null) {
        addMessage("Error", `No data for outgoing response: ${messageName}`);
        return;
      }
      const response = responseMessageFormate(localUuid, messagePayload);
      publishMessage(response);
    },
    [publishMessage, responseMessageFormate, addMessage]
  );

  useEffect(() => {
    if (error) {
      addMessage("Error", error); // Log error state changes
      setError(""); // Clear error after logging to prevent re-logging
    }
  }, [error, addMessage]);

  // Effect to clean up client on component unmount
  useEffect(() => {
    return () => {
      if (client) {
        addMessage("System", "Disconnecting MQTT client on component unmount.");
        client.end();
      }
      stopEmulator(); // Stop emulator on unmount
    };
  }, [client, addMessage, stopEmulator]); // Added stopEmulator

  return (
    <div className="flex space-x-4 p-4 bg-gray-100 min-h-screen">
      {/* Left Panel: Connection Settings and Message Controls */}
      <div className="w-1/3 pr-4 space-y-4 h-[calc(100vh-4rem)] bg-white rounded-lg shadow-lg p-4 overflow-y-auto">
        <ConnectionSettingsInternal
          connectionSettings={connectionSettings}
          setConnectionSettings={setConnectionSettings}
          isConnected={isConnected}
          connectToBroker={connectToBroker}
          client={client}
        />
        <hr className="my-4" />
        <MessageControls
          handleOutgoingRequest={handleOutgoingRequest}
          handleOutgoingResponse={handleOutgoingResponse}
          handleOutgoingBootupSequence={handleOutgoingBootupSequence}
          messageStatus={messageStatus}
          setMessageStatus={setMessageStatus}
        />
        <hr className="my-4" />
        {emulatorRunning && (
          <>
            <Button
              variant="contained"
              color="secondary"
              onClick={stopEmulator}
              sx={{ marginTop: 2 }}
            >
              Stop {emulatorMode === "inverter" ? "Inverter" : "Grid Power"}{" "}
              Emulator
            </Button>
            <SpeedControls
              onSetSpeed={handleSetEmulatorSpeed}
              currentSpeedFactor={currentSpeedFactor}
              disabled={!emulatorRunning}
            />
          </>
        )}
        <EnergyDisplay
          energyData={{
            ...emulatorData?.payload,
            elapsedEmulationTimeMs: emulatorData?.elapsedEmulationTimeMs,
            gridPowerData: gridPowerData,
          }}
          virtualTimeISO={emulatorData?.timestamp}
          timeWarpFactor={currentSpeedFactor}
        />
      </div>

      {/* Right Panel: Message Log */}
      <MessageLog messages={messages} onClearLog={handleClearMessages} />
    </div>
  );
};

export default MQTTCharger;
