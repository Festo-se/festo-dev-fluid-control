# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Hardcoded calibration coefficients for the eight-channel pipettor.

Each function returns a dict keyed by string channel index (``"1"``–``"8"``)
containing slope and offset coefficients used to compute VAEM valve-opening
times from requested volumes.
"""


def get_multichannel_interpolated_dispense_flow_coefficients() -> dict[str, dict[str, float]]:
    """Return the interpolated dispense slope coefficients for a multichannel pipettor."""
    return {
        "1": {"channel_index_coeff": 0.0038281, "flow_offset": 0.826181241},
        "2": {"channel_index_coeff": 0.002984967, "flow_offset": 0.878542698},
        "3": {"channel_index_coeff": 0.003853141, "flow_offset": 0.848381348},
        "4": {"channel_index_coeff": 0.003271288, "flow_offset": 0.845196102},
        "5": {"channel_index_coeff": 0.003353774, "flow_offset": 0.834688975},
        "6": {"channel_index_coeff": 0.003193659, "flow_offset": 0.846189041},
        "7": {"channel_index_coeff": 0.003502828, "flow_offset": 0.868563752},
        "8": {"channel_index_coeff": 0.003546353, "flow_offset": 0.825845567},
    }


def get_multichannel_interpolated_dispense_volume_coefficients() -> dict[str, dict[str, float]]:
    """Return the interpolated dispense offset coefficients for a multichannel pipettor."""
    return {
        "1": {"channel_index_coeff": 0.321305707, "volume_offset": -4.857648804},
        "2": {"channel_index_coeff": 0.536258682, "volume_offset": -5.947083862},
        "3": {"channel_index_coeff": 0.335656272, "volume_offset": -4.844234604},
        "4": {"channel_index_coeff": 0.447583845, "volume_offset": -6.775058281},
        "5": {"channel_index_coeff": 0.419307364, "volume_offset": -5.498337064},
        "6": {"channel_index_coeff": 0.445181147, "volume_offset": -5.76876463},
        "7": {"channel_index_coeff": 0.506617318, "volume_offset": -5.892657497},
        "8": {"channel_index_coeff": 0.419382823, "volume_offset": -6.829536741},
    }


def get_multichannel_interpolated_aspirate_flow_coefficients() -> dict[str, dict[str, float]]:
    """Return the interpolated dispense offset coefficients for a multichannel pipettor."""
    return {
        "1": {"channel_index_coeff": 0.006111421, "flow_offset": 1.312909499},
        "2": {"channel_index_coeff": 0.004794627, "flow_offset": 1.396112081},
        "3": {"channel_index_coeff": 0.006178665, "flow_offset": 1.348172353},
        "4": {"channel_index_coeff": 0.005257974, "flow_offset": 1.343057531},
        "5": {"channel_index_coeff": 0.005388912, "flow_offset": 1.326325254},
        "6": {"channel_index_coeff": 0.005131299, "flow_offset": 1.344640434},
        "7": {"channel_index_coeff": 0.005629979, "flow_offset": 1.380136015},
        "8": {"channel_index_coeff": 0.005685997, "flow_offset": 1.312297107},
    }


def get_multichannel_interpolated_aspirate_volume_coefficients() -> dict[str, dict[str, float]]:
    """Return the interpolated dispense offset coefficients for a multichannel pipettor."""
    return {
        "1": {"channel_index_coeff": 0.505804134, "volume_offset": -10.643569},
        "2": {"channel_index_coeff": 0.84392775, "volume_offset": -12.37390064},
        "3": {"channel_index_coeff": 0.524153843, "volume_offset": -10.61967208},
        "4": {"channel_index_coeff": 0.701143358, "volume_offset": -13.67848209},
        "5": {"channel_index_coeff": 0.65614762, "volume_offset": -11.64322993},
        "6": {"channel_index_coeff": 0.697958209, "volume_offset": -12.0802947},
        "7": {"channel_index_coeff": 0.79460032, "volume_offset": -12.2670195},
        "8": {"channel_index_coeff": 0.657661357, "volume_offset": -13.76288032},
    }
