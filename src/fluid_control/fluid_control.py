# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Fluid control abstractions and the PressureOverLiquidControl implementation.

Provides the base class hierarchy for all pipettor and dispenser fluid-handling
operations, including pressure management, valve timing, tip pickup, and ejection.
"""

from abc import ABC
from collections.abc import Callable, Iterator, KeysView
from time import sleep
import json
import math
import logging
from pgva import PGVA, PGVATCPConfig
from vaem import VAEM, VAEMTCPConfig
from applied_motion import Axis


# Configure logging with timestamps
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler("fluid_control.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class FluidControl(ABC):  # noqa: B024
    """Marker base class for all fluid-control implementations."""

    pass


# class MassFlowControl(FluidControl):
#     """Abstract Flow Control."""

#     pass


class PressureOverLiquidControl(FluidControl):
    """
    Abstract Pressure Over Liquid Control.

    Attributes:
        component_type (str): Class identifier for this component
            (e.g. ``"dispenser"`` or ``"pipettor"``). Used for logging.
        is_static (bool): Boolean delineated a statically mounted PoLControl device.

    """

    component_type: str = ""
    is_static: bool
    _STATIC_ERROR = (
        "Axis not configured, this instance of the fluid controller is configured to be static. "
        "Pass in the attachment axis to the constructor during instantiation or specify the attached "
        "axis via the configuration file if this was done in error."
    )

    def __init__(
        self,
        config: dict,  # TODO: SUPPORT CONFIG FILENAME IMPORT
        component_id: str = "",  # TODO: Optional args to directly pass in existing pressure and valve control and skip config
        mount_arm: Axis | None = None,  # TODO: Take from config
        disable_axes: tuple[Axis, ...] = (),  # TODO: Take from config
        pressure_control=None,
        valve_control=None,
    ) -> None:
        """
        Initialize a pressure-over-liquid fluid control module.

        Args:
            config (dict): Full instrument configuration dict; the component
                keyed by ``component_id`` is extracted and used.
            mount_arm: Axis object used for tip pickup/eject motion. If ``None``
                the instance is treated as static. Defaults to None.
            disable_axes (tuple): Axes to disable during tip engagement moves.
                Defaults to ``()``.
            component_id (str): Instance name used to look up this component
                inside ``config["components"]``. Defaults to ``""``.
            pressure_control: Instance of already-instantiated pressure control device.
                Opinionated choice that this is a PGVA with some support for
                PLC-controlled VEAB at present.
            valve_control: Instance of already-instantiated valve control device.
                Opinionated choice that this is a VAEM with some support for single valves controlled
                by the DO pin on the PGVA at present.

        """
        # TODO: If neither config nor pressure/valve control passed in, init error

        self.component_id = component_id
        logger.info(f"Initializing {self.component_type} (id={component_id!r})")
        parsed_config = config.get("component_config", config)
        self.config = parsed_config["components"][component_id]
        self.active_channels = self.config["control_modules"]["valve"]["active_valve_terminals"]
        self.active_valve_count = len(self.active_channels)

        if pressure_control is not None:
            self.pressure_control = pressure_control
        else:
            self._init_pressure_control()

        if valve_control is not None:
            self.valve_control = valve_control
            self._set_valve_error_handling(self.config, component_id)
        else:
            self._init_valve_control()

        self.fluid_control_status = Status()
        self.channel_count = self.config["fluid-channel-count"]
        self.is_static = mount_arm is None  # TODO: make this a param input via config
        if not self.is_static:
            self.mount_arm = mount_arm
        self.disable_axes = disable_axes
        for valve in self.active_channels:  # TODO for valve in self.active_channels
            self.valve_control.deselect_valve(valve_id=valve)  # TODO
        self.set_pressures()
        # self.aspiration_pressure = self.config["calibration"]["aspirate"][
        #     "pressure"
        # ]  # TODO: in json config figure out how to do multiple calibrations at different pressures
        # self.dispense_pressure = self.config["calibration"]["dispense"]["pressure"]  # TODO: ditto
        self.valve_control_timing_functions = {}

        self._set_all_calibrations()  # TODO: modify config such that multiple pressures can have calibration per process  in the json
        logger.info(
            f"{self.component_type} initialization complete — channels={self.active_channels}, "
            f"liquid_classes={list(self.config['calibration'].keys())}, "
            f"static={self.is_static}"
        )

    def set_pressures(self) -> None:
        """Populate ``self.pressures`` from the calibration config for each liquid class and process."""
        self.pressures = {}
        calibration = self.config["calibration"]

        for liquid_class in calibration.keys():
            if liquid_class not in self.pressures:
                self.pressures[liquid_class] = {}
            for process in calibration[liquid_class].keys():
                self.pressures[liquid_class][process] = calibration[liquid_class][process]["parameters"]["pressure"]

    def get_liquid_classes(self) -> KeysView[str]:
        """Return the liquid-class keys present in the current calibration config."""
        return self.config["calibration"].keys()

    def _init_pressure_control(self, config: dict | None = None) -> None:
        name = self.config["control_modules"]["valve"]["name"]
        logger.debug(f"Initializing Pressure Controller {name}.")
        """
        Initialize the PGVA with the given configuration.

        Inputs:

            config: From overall configuration file,
                the dictionary that contains the PGVA configuration.
        """
        if "pgva" not in self.config["control_modules"]["pressure"]["name"]:
            raise NotImplementedError("Pressure control without a PGVA is not implemented")

        # pressure_configs = {
        #     self.config["control_modules"]["pressure"]["channel"]: "pressure",
        #     self.config["control_modules"]["regulator"]["channel"]: "regulator",
        # }

        if config is None:
            config = self.config
        ip = config["control_modules"]["pressure"]["interface"]["ip"]  # TODO: Unhardcode from TCP backend
        port = config["control_modules"]["pressure"]["interface"]["port"]
        self.pressure_control_config = PGVATCPConfig(
            interface=config["control_modules"]["pressure"]["interface"]["type"],
            unit_id=config["control_modules"]["pressure"]["uuid"],
            ip=ip,
            port=port,
        )
        self.pressure_control = PGVA(config=self.pressure_control_config)
        logger.debug(f"Pressure controller {name} initialized at {ip}:{port}")

    def _init_valve_control(
        self, config: dict | None = None
    ) -> None:  # TODO: Make sure active_valve_terminals is being used appropriately
        name = self.config["control_modules"]["valve"]["name"]
        logger.debug(f"Initializing valve control module {name}.")
        """
        Initialize the VAEM with the given configuration.

        Inputs:
            config: From overall configuration file,
                the dictionary that contains the PGVA configuration.
        """
        if "vaem" not in self.config["control_modules"]["valve"]["name"]:
            raise NotImplementedError("Pressure control without a VAEM is not implemented")

        if config is None:
            config = self.config
        ip = config["control_modules"]["valve"]["interface"]["ip"]
        port = config["control_modules"]["valve"]["interface"]["port"]
        self.valve_control_config = VAEMTCPConfig(
            interface=config["control_modules"]["valve"]["interface"]["type"],
            unit_id=1,  # config["control_modules"]["valve"]["uuid"],
            ip=config["control_modules"]["valve"]["interface"]["ip"],
            port=config["control_modules"]["valve"]["interface"]["port"],
        )
        self.valve_control = VAEM(config=self.valve_control_config)
        logger.debug(f"Valve controller {name} initialized at {ip}:{port}")
        self._set_valve_error_handling(config, name)

    def _set_valve_error_handling(self, config, name):
        logger.debug(f"Valve controller {name} set error handling config: {self.config}")
        error_handling = [
            valve_info["type"]["error-handling"]
            for valve_info in self.config["control_modules"]["valve"]["valve_type"].values()
        ]

        self._valve_error_handling_status = all(error_handling)
        self.valve_control.set_error_handling(activate=int(self._valve_error_handling_status))
        logger.debug(f"Valve controller {name} module-set error handling status: {self._valve_error_handling_status}")
        logger.debug(
            f"Valve controller {name} actual error handling status: {self.valve_control.get_error_handling_status()}"
        )

    def _get_calibration_values(self, liquid_class: str, process: str) -> tuple[dict, dict]:
        """Get the calibration values from the calibration curves."""
        self.flow_offset_vars = self.config["calibration"][liquid_class][process]["flow_coefficients"]
        self.volume_offset_vars = self.config["calibration"][liquid_class][process]["volume_offset_coefficients"]

        return (self.flow_offset_vars, self.volume_offset_vars)

    def set_new_calibration(self, calib: dict):
        """Set the calibration values from the calibration curves."""
        self.config["calibration"] = calib
        self._set_all_calibrations()

    def _set_all_calibrations(self) -> None:
        liquid_classes = list(self.config["calibration"].keys())
        logger.debug(f"Building timing functions for {len(liquid_classes)} liquid class(es): {liquid_classes}")
        for liquid_class in liquid_classes:
            for process in self.config["calibration"][liquid_class].keys():
                self._set_calibration(liquid_class=liquid_class, process=process)
        logger.debug("Timing functions built for all liquid classes and processes")

    def _set_calibration(self, liquid_class: str, process: str) -> None:
        logger.debug(f"Setting calibration: liquid_class={liquid_class!r}, process={process!r}")
        flow_calib, volume_calib = self._get_calibration_values(liquid_class, process)
        self._set_timing_functions(flow_calib, volume_calib, liquid_class, process)

    def _set_timing_functions(
        self, flow_offset_coefficients: dict, volume_offset_coefficients: dict, liquid_class: str, process: str
    ) -> None:
        """
        Translate the slope and offset coefficients into timing functions for each channel.

        Inputs:
            flow_coefficients: Dictionary of slope coefficients for each channel
            volume_offset_coefficients: Dictionary of offset coefficients for each channel
            process: "aspirate" or "dispense"
        """
        slope_intercept_coeffs = {}
        for key, value in flow_offset_coefficients.items():
            if key not in slope_intercept_coeffs:
                slope_intercept_coeffs[key] = {}
            channel_index_coeff = value["channel_index_coeff"]
            flow_offset = value["flow_offset"]
            slope_intercept_coeffs[key]["slope"] = self._slope_intercept_func(channel_index_coeff, flow_offset)

        for key, value in volume_offset_coefficients.items():
            channel_index_coeff = value["channel_index_coeff"]
            volume_offset = value["volume_offset"]
            slope_intercept_coeffs[key]["intercept"] = self._slope_intercept_func(channel_index_coeff, volume_offset)
        if liquid_class not in self.valve_control_timing_functions:
            self.valve_control_timing_functions[liquid_class] = {}
        self.valve_control_timing_functions[liquid_class][process] = slope_intercept_coeffs

    def _slope_intercept_func(self, channel_index_coeff: float, volume_offset: float) -> Callable[[float], float]:
        def slope_map(var: float) -> float:
            return channel_index_coeff * var + volume_offset

        return slope_map

    def _set_timing(self, channel: int, volume: float, active_channels: int, liquid_class: str, process: str) -> int:
        logger.debug(
            f"Setting timing: channel={channel}, volume={volume}uL, active_channels={active_channels}, liquid_class={liquid_class}, process={process}"
        )
        """
        Set the timing for the VAEM valve based on the channel, volume, and number of active channels.

            Inputs:
                channel: Channel ID (1 or 2)
                volume: Volume in uL
                active_channels: Number of active channels (1 to 8 for VAEM)
                process: "aspirate" or "dispense"
        """
        self.valve_control.select_valve(valve_id=channel)
        slope = self.valve_control_timing_functions[liquid_class][process][str(channel)]["slope"](active_channels)
        intercept = self.valve_control_timing_functions[liquid_class][process][str(channel)]["intercept"](
            active_channels
        )
        volume_opening_time = int(slope * volume + intercept)
        logger.debug(f"Calculated opening time: {volume_opening_time}ms (slope={slope:.4f}, intercept={intercept:.4f})")
        # volume_opening_time = volume_opening_time / 0.2
        self.valve_control.set_valve_switching_time(valve_id=channel, opening_time=volume_opening_time)
        return volume_opening_time

    def _validate_liquid_class(self, liquid_class: str) -> None:
        current_classes = self.get_liquid_classes()
        if liquid_class not in current_classes:
            raise ValueError(f"""Liquid class {liquid_class} not contained in current configuration \
                Current configuration contains {tuple(current_classes)}.
            """)

    def _handle_liquid(self, liquid_dict: dict, process: str) -> list[int | str]:
        # try:
        logger.info(
            f"HANDLE LIQUID START: process={process}, "
            f"channels={list(liquid_dict.keys())}, "
            f"volumes={[p['volume'] for p in liquid_dict.values()]}"
        )
        self.fluid_control_status.set_busy()
        # TODO: Mix command doesn't work well with this formulation of the liquid handlinng algorithm

        longest_open_time = 0

        for channel, command_params in liquid_dict.items():
            liquid_class = command_params["liquid_class"]
            self._validate_liquid_class(liquid_class=liquid_class)
            self._validate_channel_command((channel, command_params["volume"]))

            logger.debug(f"Valve controller status before configuring timing for channel {channel}")
            vc_status = self.valve_control.get_status()
            logger.debug(f"{vc_status}")
            new_time = self._set_timing(  # TODO: Check if _set_timing has sign guard
                channel=channel,
                volume=command_params["volume"],
                active_channels=self.active_valve_count,
                liquid_class=liquid_class,
                process=process,
            )
            longest_open_time = max(new_time, longest_open_time)
        logger.debug(f"Waiting for {process} pressure: {self.pressures[liquid_class][process]}")
        self._wait_output_pressure(
            self.pressures[liquid_class][process]
        )  # This will use the presssure for the last liquid class which isn't technically correct.
        # Need to group timing commands by liquid class, set pressure and execute for "correct" operation. In practice, this will never happen though.
        # Could also throw error when multiple liquid classes are part of input and say this is not strictly supported. Would need seperate pressure control modules or separable pressure reservoirs with in and out valves.

        logger.debug("Opening valve (waiting for readiness)")
        if process == "dispense":
            repeat = True  # TODO: What is this doing? Why is this here?
            while repeat:
                self.valve_control.open_selected_valves()
                status = self.valve_control.get_status()
                if status["Readiness"] == 0:
                    repeat = False
        else:
            self.valve_control.open_selected_valves()
        logger.debug("Valve controller status after opening valve")
        vc_status = self.valve_control.get_status()
        logger.debug(f"{vc_status}")
        """
        status = self.valve_control.get_status()
        while status['Readiness'] == 1:
            self.valve_control.open_selected_valves()
            status = self.valve_control.get_status()
        """

        logger.debug(f"Waiting for valve timing to complete: {longest_open_time}ms")
        sleep(longest_open_time / 1000)
        self._wait_output_pressure(
            0
        )  # TODO: Is this necessary? What happens if we hold the closed valves at pressure over time?
        for channel, _ in liquid_dict.items():
            logger.debug(f"Deselecting valve {channel} (VC channel {channel})")
            self.valve_control.deselect_valve(channel)
        self.fluid_control_status.set_clear()
        logger.info("LIQUID HANDLING OPERATION COMPLETE")
        return [self.fluid_control_status.get_status(), f"{process}".capitalize() + " process executed successfully"]
        # except Exception as e:
        #     self.fluid_control_status.set_error()
        #     logger.error(f"LIQUID HANDLING OPERATION FAILED: {e}")
        #     return [self.fluid_control_status.get_status(), str(e)]

    def direct_command(self, channel_times: dict, pressure: int) -> list[int | str]:
        """
        Send raw pressure and valve-timing commands, bypassing volume calibration.

        Direct command of pressure and valve controllers. Used to *build* calibration.

        Args:
            channel_times (dict): Mapping of channel ID to valve opening time in ms.
            pressure (int): Output pressure in mbar to hold during the operation.

        Returns:
            list: ``[status_code, message]`` describing the outcome.

        """
        logger.info(f"DIRECT COMMAND START: {channel_times}")
        try:
            self.fluid_control_status.set_busy()
            self._validate_pressure(pressure)
            logger.debug(f"Setting pressure: {pressure} mbar")
            self._wait_output_pressure(pressure)

            longest_open_time = 0
            for channel, opening_time in channel_times.items():
                self._validate_channel(channel)
                self._validate_opening_time(opening_time, channel)
                self.valve_control.select_valve(valve_id=channel)
                self.valve_control.set_valve_switching_time(valve_id=channel, opening_time=opening_time)
                longest_open_time = max(opening_time, longest_open_time)
                logger.debug(f"Channel {channel} (Valve contoller {channel}): opening_time={opening_time}ms")
            self.valve_control.open_selected_valves()
            # Wait for valve operation to complete (Readiness==1 means ready)
            while True:
                status = self.valve_control.get_status()
                if status["Readiness"] == 1:
                    break
            # Return pressure to neutral and wait for it to stabilize
            self._wait_output_pressure(-1)
            for channel in channel_times:
                self.valve_control.deselect_valve(channel)

            self.fluid_control_status.set_clear()
            logger.info("DIRECT COMMAND COMPLETE")
            return [self.fluid_control_status.get_status(), "Direct command executed successfully"]
        except Exception as e:
            logger.error(f"DIRECT COMMAND FAILED: {e}")
            self.fluid_control_status.set_error()
            return [self.fluid_control_status.get_status(), str(e)]

    def _pressure_status_dispath(self):
        pressure_control = self.pressure_control
        if hasattr(pressure_control, "get_status_word"):
            return pressure_control.get_status_word()
        else:
            return "TODO: implement other status getter"

    def get_status(self) -> dict:
        """Return the status of the fluid_control."""
        status = {
            "pressure": self._pressure_status_dispath(),
            "valve": self.valve_control.get_status(),
            "fluid_control_status": self.fluid_control_status.get_status(),
        }
        logger.debug(f"get_status: {status}")
        return status

    def _wait_output_pressure(self, pressure: int) -> None:
        logger.debug(f"Setting and waiting for pressure: {pressure}")
        logger.debug(f"Calling set_output_pressure({pressure})")
        self.pressure_control.set_output_pressure(pressure=pressure)
        logger.debug("set_output_pressure returned, starting poll loop")
        current = self.pressure_control.get_output_pressure()
        while True:
            if math.isclose(self.pressure_control.get_output_pressure(), pressure, abs_tol=1):
                logger.debug(f"Pressure reached: {current}")
                break
            current = self.pressure_control.get_output_pressure()
        return None

    def _wait_valve_control_ready(self) -> None:
        logger.debug("Waiting for valve control ready")
        while True:
            status = self.valve_control.get_status()
            if status["Readiness"]:
                break

    def _require_arm(self) -> None:
        """Raise if no motion axis is configured for tip/mix operations."""
        if self.is_static or getattr(self, "mount_arm", None) is None:
            raise NotImplementedError(self._STATIC_ERROR)

    def _disable_xy_axes(self) -> None:
        logger.debug("Disabling target axes")
        self._require_arm()

        for axis in self.disable_axes:
            axis.acknowledge_faults()
            axis.disable_powerstage()

    def _enable_xy_axes(self) -> None:
        logger.debug("Enabling the axes in action disable list")
        self._require_arm()
        for axis in self.disable_axes:
            axis.acknowledge_faults()
            axis.enable_powerstage()

    # TODO change to dictionary input
    # TODO change error handling with more clarification of error
    # TODO CHANGE PROTO TO HANDLE MIX WITH CYCLES

    def _validate_channel_command(self, chan_vol: tuple[int, float]) -> None:
        (channel, volume) = chan_vol
        self._validate_volume(volume, channel)
        self._validate_channel(channel)

    def _validate_volume(self, volume: float, channel: int) -> None:
        if volume < 0:
            raise ValueError(
                f"Error: Volume must greater than or equal to zero. \
                Input volume: {volume} on channel {channel}"
            )

    def _validate_channel(self, channel: int) -> None:
        if channel not in self.active_channels:
            raise ValueError(
                f"Error: Channel numbers must have an ID contained \
            in the active channel configuration parameter. Requested channel \
            {channel} (type: {type(channel)})received, current active channel config has channels \
            {self.active_channels}."
            )

    def _validate_opening_time(self, time: int, channel: int) -> None:
        if time <= 0:
            raise ValueError(
                f"Error: Valve opening time must greater than zero. Input time: {time} on channel {channel}"
            )

    def _validate_pressure(self, pressure: int) -> None:
        pass
        # TODO: Make sure pressure limits are exposed in e.g. pgva library and read them in to compare here

    def __repr__(self) -> str:
        """Return representation of control class."""
        return f"{type(self).__name__}: component_type={self.component_type!r}, component_id={self.component_id} "

    def __len__(self) -> int:
        """Return the number of fluid channels."""
        return self.channel_count

    def __iter__(self) -> Iterator[int]:
        """Iterate over active channel IDs."""
        return iter(self.active_channels)

    def __contains__(self, channel: int) -> bool:
        """Return True if channel is an active channel."""
        return channel in self.active_channels

    def __eq__(self, other: object) -> bool:
        """Return True if both instances represent the same hardware controller."""
        if not isinstance(other, PressureOverLiquidControl):
            return NotImplemented
        return self.component_type == other.component_type and self.config == other.config

    def __hash__(self) -> int:
        """Return hash derived from component type and config."""
        return hash((self.component_type, json.dumps(self.config, sort_keys=True)))

    def __enter__(self):
        """Entry for context manager."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool:
        """Return hardware to a safe state on context exit."""
        self.pressure_control.set_output_pressure(0)
        for valve in range(1, self.channel_count + 1):
            self.valve_control.deselect_valve(valve_id=valve)
        self.fluid_control_status.set_clear()
        return False


class Status:
    """
    Simple status code container used by fluid-control operations.

    Attributes:
        code (int): Current status — ``0`` clear, ``1`` error, ``2`` busy.
        message (str): Optional human-readable status message.

    """

    def __init__(self) -> None:
        """Initialise status to the clear (0) state."""
        self.code = 0
        self.message = ""

    def get_status(self) -> int:
        """Return the current status code."""
        return self.code

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        return f"Status(code={self.code}, message={self.message!r})"

    def __str__(self) -> str:
        """Return human-readable status label."""
        return {0: "clear", 1: "error", 2: "busy"}.get(self.code, f"unknown({self.code})")

    def __bool__(self) -> bool:
        """Return True when status is clear (0)."""
        return self.code == 0

    def __eq__(self, other: object) -> bool:
        """Return True if status codes are equal; also supports comparison with int."""
        if isinstance(other, Status):
            return self.code == other.code
        if isinstance(other, int):
            return self.code == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return hash of the status code."""
        return hash(self.code)

    def set_clear(self) -> None:
        """Set status to clear (0)."""
        self.code = 0

    def set_error(self) -> None:
        """Set status to error (1)."""
        self.code = 1

    def set_busy(self) -> None:
        """Set status to busy (2)."""
        self.code = 2


def validate_config(config: dict) -> bool:
    """
    Validate an instrument configuration dict.

    Args:
        config (dict): Configuration dict to validate.

    Returns:
        bool: ``True`` if the configuration is valid.

    Raises:
        ValueError: If any required field is absent or has an invalid value.

    """
    # TODO: This is better situated in the configurator module, probably.
    pass
    valid_config = False

    incorrect_field_value = {}
    if not valid_config:
        raise ValueError(f"""Bad configuration detected. \
            Please check {incorrect_field_value} and your configuration for consistency.""")
    return True
