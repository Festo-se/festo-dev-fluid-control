# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Data from calibration_curves.py is simplified and captured in multi_channel_index_calibration.property.

multi_channel_index_calibration.py uses an implied linear interpolation with the channel index i as the independent
variable, and using all channels and single channel here to be the i=8 and i=1 endpoints for the
interpolated fit, respectively.
"""


def get_head_2_dispense_curve_all_channels() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients and offsets for the dispense curve for all channels."""
    return {
        "1": {"flow_coeff": 0.856806042, "volume_offset": -2.287203147},
        "2": {"flow_coeff": 0.902422437, "volume_offset": -1.657014402},
        "3": {"flow_coeff": 0.87920648, "volume_offset": -2.158984425},
        "4": {"flow_coeff": 0.87136641, "volume_offset": -3.194387521},
        "5": {"flow_coeff": 0.861519164, "volume_offset": -2.143878149},
        "6": {"flow_coeff": 0.871738312, "volume_offset": -2.20731545},
        "7": {"flow_coeff": 0.896586375, "volume_offset": -1.83971895},
        "8": {"flow_coeff": 0.854216389, "volume_offset": -3.474474155},
    }


def get_head_2_dispense_curve_single_channel() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients and offsets for the aspiration curve for single channels."""
    return {
        "1": {"flow_coeff": 0.830009342, "volume_offset": -4.536343097},
        "2": {"flow_coeff": 0.881527665, "volume_offset": -5.410825179},
        "3": {"flow_coeff": 0.85223449, "volume_offset": -4.508578331},
        "4": {"flow_coeff": 0.84846739, "volume_offset": -6.327474436},
        "5": {"flow_coeff": 0.838042749, "volume_offset": -5.0790297},
        "6": {"flow_coeff": 0.849382699, "volume_offset": -5.323583483},
        "7": {"flow_coeff": 0.87206658, "volume_offset": -5.386040179},
        "8": {"flow_coeff": 0.82939192, "volume_offset": -6.410153918},
    }


def get_head_2_aspirate_curve_all_channels() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients and offsets for the aspiration curve for all channels."""
    return {
        "1": {"flow_coeff": 1.361800864, "volume_offset": -6.597135931},
        "2": {"flow_coeff": 1.434469099, "volume_offset": -5.622478642},
        "3": {"flow_coeff": 1.397601675, "volume_offset": -6.42644133},
        "4": {"flow_coeff": 1.385121322, "volume_offset": -8.069335219},
        "5": {"flow_coeff": 1.369436554, "volume_offset": -6.394048971},
        "6": {"flow_coeff": 1.385690825, "volume_offset": -6.496629027},
        "7": {"flow_coeff": 1.425175843, "volume_offset": -5.910216939},
        "8": {"flow_coeff": 1.357785079, "volume_offset": -8.50158947},
    }


def get_head_2_aspirate_curve_single_channel() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients and offsets for the aspiration curve for single channels."""
    return {
        "1": {"flow_coeff": 1.319020919, "volume_offset": -10.13776487},
        "2": {"flow_coeff": 1.400906708, "volume_offset": -11.52997289},
        "3": {"flow_coeff": 1.354351018, "volume_offset": -10.09551823},
        "4": {"flow_coeff": 1.348315504, "volume_offset": -12.97733873},
        "5": {"flow_coeff": 1.331714167, "volume_offset": -10.98708231},
        "6": {"flow_coeff": 1.349771733, "volume_offset": -11.38233649},
        "7": {"flow_coeff": 1.385765993, "volume_offset": -11.47241918},
        "8": {"flow_coeff": 1.317983103, "volume_offset": -13.10521897},
    }


def get_head_1_aspirate_curve_single_channel() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients for the aspiration curve for single channel aspiration for head 1."""
    return {
        "1": {"flow_coeff": 1.302560198, "volume_offset": -13.81502772},
        "2": {"flow_coeff": 1.276280999, "volume_offset": -13.09101157},
        "3": {"flow_coeff": 1.323343584, "volume_offset": -13.26558119},
        "4": {"flow_coeff": 1.313160194, "volume_offset": -15.37803803},
        "5": {"flow_coeff": 1.276341709, "volume_offset": -15.49019277},
        "6": {"flow_coeff": 1.269744904, "volume_offset": -15.2145785},
        "7": {"flow_coeff": 1.288707875, "volume_offset": -14.75109341},
        "8": {"flow_coeff": 1.290294155, "volume_offset": -17.52151983},
    }


def get_head_1_dispense_curve_single_channel() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients for the dispense curve for single channel dispensing for head 1."""
    return {
        "1": {"flow_coeff": 0.847723025, "volume_offset": -8.796876715},
        "2": {"flow_coeff": 0.830600684, "volume_offset": -8.322078361},
        "3": {"flow_coeff": 0.861234179, "volume_offset": -8.436627575},
        "4": {"flow_coeff": 0.854694298, "volume_offset": -9.82726595},
        "5": {"flow_coeff": 0.830677995, "volume_offset": -9.89050841},
        "6": {"flow_coeff": 0.826524733, "volume_offset": -9.737363307},
        "7": {"flow_coeff": 0.838739575, "volume_offset": -9.411938574},
        "8": {"flow_coeff": 0.839795961, "volume_offset": -11.2194961},
    }


def get_head_1_dispense_curve_all_channels() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients and offsets for the dispense curve for all channels."""
    return {
        "1": {"flow_coeff": 0.858873117, "volume_offset": -6.721032547},
        "2": {"flow_coeff": 0.854197735, "volume_offset": -5.073319224},
        "3": {"flow_coeff": 0.88472154, "volume_offset": -4.608803382},
        "4": {"flow_coeff": 0.873117333, "volume_offset": -5.707125131},
        "5": {"flow_coeff": 0.854436879, "volume_offset": -5.954236346},
        "6": {"flow_coeff": 0.85246621, "volume_offset": -6.305039976},
        "7": {"flow_coeff": 0.866826952, "volume_offset": -5.440226239},
        "8": {"flow_coeff": 0.873638307, "volume_offset": -6.2636651},
    }


def get_head_1_aspirate_curve_all_channels() -> dict[str, dict[str, float]]:
    """Return a dictionary containing the coefficients and offsets for the aspiration curve for all channels."""
    return {
        "1": {"flow_coeff": 1.318858492, "volume_offset": -10.40199499},
        "2": {"flow_coeff": 1.313019485, "volume_offset": -8.183346918},
        "3": {"flow_coeff": 1.359942153, "volume_offset": -7.469893319},
        "4": {"flow_coeff": 1.342152883, "volume_offset": -9.16646092},
        "5": {"flow_coeff": 1.313413429, "volume_offset": -9.542092277},
        "6": {"flow_coeff": 1.310331753, "volume_offset": -10.07203158},
        "7": {"flow_coeff": 1.332467915, "volume_offset": -8.753509341},
        "8": {"flow_coeff": 1.343079103, "volume_offset": -10.04368077},
    }
