import { v4 as uuidv4 } from 'uuid';
import SunCalc from 'suncalc';
import { DateTime } from 'luxon';

export default class InverterEmulator {
  constructor(options = {}) {
    this.options = Object.assign(
      {
        inverterId: "INV001",
        tenantId: 1,
        lat: 0,
        lon: 0,
        timezone: "UTC",
        startTime: new Date().toISOString(),
        faultEnabled: false,
        meanFaultInterval: 7, // days
        faultDurationMin: 10, // minutes
        faultDurationMax: 60, // minutes
        logger: console,
        onData: (data) => console.log("Data:", data),
        initialTickIntervalMs: 1000, // Default to 1 real second per tick
        mode: "inverter", // 'inverter' or 'gridPower'
      },
      options
    );

    this.virtualTime = DateTime.fromISO(this.options.startTime, {
      zone: this.options.timezone,
    });
    this.simulationConfiguredStartTimeEpoch = this.virtualTime.toMillis();
    this.running = false;
    this.intervalHandle = null;
    this.faultActive = false;
    this.nextFaultTime = this.scheduleNextFault();
    this.faultEndTime = null;
    this.currentTickIntervalMs = this.options.initialTickIntervalMs;

    this.energyCounters = {
      daily: 0,
      monthly: 0,
      yearly: 0,
    };

    // Initialize grid power data array with 288 elements (5-minute intervals for 24 hours)
    this.gridPowerData = new Array(288).fill(0);
    this.lastGridPowerUpdate = null;
  }

  scheduleNextFault() {
    if (!this.options.faultEnabled) return null;
    const intervalMinutes = this.options.meanFaultInterval * 24 * 60;
    const offset = Math.floor(Math.random() * intervalMinutes);
    return this.virtualTime.plus({ minutes: offset });
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.intervalHandle = setInterval(
      () => this.tick(),
      this.currentTickIntervalMs
    );
    this.options.logger.info(
      `InverterEmulator started with tick interval: ${this.currentTickIntervalMs}ms`
    );
  }

  stop() {
    this.running = false;
    if (this.intervalHandle) clearInterval(this.intervalHandle);
    this.options.logger.info("InverterEmulator stopped");
  }

  updateTickInterval(newIntervalMs) {
    if (newIntervalMs <= 0) {
      this.options.logger.warn(
        `Invalid tick interval: ${newIntervalMs}ms. Must be > 0.`
      );
      return;
    }
    this.currentTickIntervalMs = newIntervalMs;
    this.options.logger.info(
      `Updating tick interval to: ${this.currentTickIntervalMs}ms`
    );
    if (this.running) {
      clearInterval(this.intervalHandle);
      this.intervalHandle = setInterval(
        () => this.tick(),
        this.currentTickIntervalMs
      );
      this.options.logger.info("Emulator interval restarted with new speed.");
    }
  }

  getCurrentTimeWarpFactor() {
    if (
      this.currentTickIntervalMs <= 0 ||
      this.options.initialTickIntervalMs <= 0
    ) {
      // Avoid division by zero or non-positive intervals
      return 0;
    }
    return this.options.initialTickIntervalMs / this.currentTickIntervalMs;
  }

  tick() {
    this.virtualTime = this.virtualTime.plus({ minutes: 5 });

    // Reset counters if needed
    if (this.virtualTime.hour === 0 && this.virtualTime.minute === 0) {
      this.energyCounters.daily = 0;
      // Reset grid power data array at midnight
      this.gridPowerData = new Array(288).fill(0);
    }
    if (
      this.virtualTime.day === 1 &&
      this.virtualTime.hour === 0 &&
      this.virtualTime.minute === 0
    )
      this.energyCounters.monthly = 0;
    if (
      this.virtualTime.month === 1 &&
      this.virtualTime.day === 1 &&
      this.virtualTime.hour === 0 &&
      this.virtualTime.minute === 0
    )
      this.energyCounters.yearly = 0;

    const { lat, lon } = this.options;
    const times = SunCalc.getTimes(this.virtualTime.toJSDate(), lat, lon);

    // Debug logging for time and sun position
    this.options.logger.info(
      `Current Virtual Time: ${this.virtualTime.toISO()}`
    );
    this.options.logger.info(`Current Hour: ${this.virtualTime.hour}`);
    this.options.logger.info(`Sunrise: ${times.sunrise.toISOString()}`);
    this.options.logger.info(`Sunset: ${times.sunset.toISOString()}`);

    const isDaylight =
      this.virtualTime >= DateTime.fromJSDate(times.sunrise) &&
      this.virtualTime <= DateTime.fromJSDate(times.sunset);

    this.options.logger.info(`Is Daylight: ${isDaylight}`);

    let solarPower = 0;
    if (isDaylight && !this.faultActive) {
      const cloudFactor = 0.7 + Math.random() * 0.3;
      const hourAngle = Math.PI * ((this.virtualTime.hour - 6) / 12);
      const peakOutput = 5000; // watts
      solarPower = Math.max(0, peakOutput * Math.sin(hourAngle) * cloudFactor);
      this.options.logger.info(`Hour Angle: ${hourAngle}`);
      this.options.logger.info(`Cloud Factor: ${cloudFactor}`);
      this.options.logger.info(`Calculated Solar Power: ${solarPower}W`);
    }

    if (this.options.faultEnabled) {
      if (!this.faultActive && this.virtualTime >= this.nextFaultTime) {
        const duration =
          this.options.faultDurationMin +
          Math.random() *
            (this.options.faultDurationMax - this.options.faultDurationMin);
        this.faultEndTime = this.virtualTime.plus({ minutes: duration });
        this.faultActive = true;
        this.options.logger.warn(
          `Fault injected at ${this.virtualTime.toISO()}`
        );
      } else if (this.faultActive && this.virtualTime >= this.faultEndTime) {
        this.faultActive = false;
        this.nextFaultTime = this.scheduleNextFault();
        this.options.logger.info(`Fault ended at ${this.virtualTime.toISO()}`);
      }
    }

    const gridPower = solarPower * 0.98;
    const reactivePower = gridPower * 0.05;
    const gridVoltages = [
      230 + Math.random() * 5,
      231 + Math.random() * 5,
      229 + Math.random() * 5,
    ];
    const gridCurrents = gridVoltages.map((v) => solarPower / v);

    // Update grid power data array
    const currentIndex =
      this.virtualTime.hour * 12 + Math.floor(this.virtualTime.minute / 5);
    if (currentIndex >= 0 && currentIndex < 288) {
      this.gridPowerData[currentIndex] = this.faultActive
        ? 0
        : gridPower / 1000; // Convert to kW
    }

    // Generate grid power periodic data if it's time (every 5 minutes)
    if (
      this.options.mode === "gridPower" &&
      (!this.lastGridPowerUpdate ||
        this.virtualTime.diff(this.lastGridPowerUpdate, "minutes").minutes >= 5)
    ) {
      const gridPowerPeriodicData = {
        gridPower: [...this.gridPowerData],
        timestamp: this.virtualTime.toISO(),
      };
      this.options.onData({
        type: "gridPowerPeriodic",
        data: gridPowerPeriodicData,
      });
      this.lastGridPowerUpdate = this.virtualTime;
    }

    if (!this.faultActive) {
      const energyIncrement = (solarPower * 5) / 60 / 1000; // kWh
      this.energyCounters.daily += energyIncrement;
      this.energyCounters.monthly += energyIncrement;
      this.energyCounters.yearly += energyIncrement;
      this.options.logger.info(`Energy Increment: ${energyIncrement}kWh`);
      this.options.logger.info(`Daily Energy: ${this.energyCounters.daily}kWh`);
    }

    const elapsedEmulationTimeMs =
      this.virtualTime.toMillis() - this.simulationConfiguredStartTimeEpoch;

    // Debug log the energy counters
    this.options.logger.info("Energy Counters:", {
      daily: this.energyCounters.daily,
      monthly: this.energyCounters.monthly,
      yearly: this.energyCounters.yearly,
    });

    // Only send inverter data if in inverter mode
    if (this.options.mode === "inverter") {
      const data = {
        timestamp: this.virtualTime.toISO(),
        canComm: 1,
        elapsedEmulationTimeMs: elapsedEmulationTimeMs,
        inverterData: {
          gridStatus: 1,
          pvStatus: isDaylight ? 1 : 0,
          inverterOn: this.faultActive ? 0 : 1,
          gridVoltages,
          gridCurrents,
          gridFrequencies: [
            50 + Math.random() * 0.1,
            50 + Math.random() * 0.1,
            50 + Math.random() * 0.1,
          ],
          gridPower: this.faultActive ? 0 : gridPower,
          reactivePower: this.faultActive ? 0 : reactivePower,
          solarPower: this.faultActive ? 0 : solarPower,
          dcLinkVoltage: 800 + Math.random() * 50,
          residualCurrent: Math.random() * 0.5,
          vdcp: 400 + Math.random() * 25,
          vdcn: 400 + Math.random() * 25,
          loadCurrent: solarPower / 400,
          heatSinkTemperature: 45 + Math.random() * 10,
          gridInductorTemperature: 50 + Math.random() * 15,
          pvInductorTemperature: 55 + Math.random() * 20,
          rIsoN: Math.random() * 1000,
          rIsoP: Math.random() * 1000,
          faultCode: this.faultActive ? 1 : 0,
          vpv: [600 + Math.random() * 100],
          ipv: [solarPower / 600],
          dailyEnergy: this.energyCounters.daily,
          monthlyEnergy: this.energyCounters.monthly,
          yearlyEnergy: this.energyCounters.yearly,
        },
      };

      // Debug log the final payload
      this.options.logger.info("Emulator Payload:", {
        dailyEnergy: data.inverterData.dailyEnergy,
        monthlyEnergy: data.inverterData.monthlyEnergy,
        yearlyEnergy: data.inverterData.yearlyEnergy,
      });

      this.options.onData(data);
    }
  }
}



