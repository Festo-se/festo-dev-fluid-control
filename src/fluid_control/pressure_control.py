# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Generic Pressure control class."""


class PressureControl:
    """Thin adapter exposing a uniform pressure-control interface over a backend controller."""

    def __init__(self, controller):
        """
        Store the backing controller.

        Args:
            controller: Backend pressure-control device exposing ``set_veab`` and ``get_veab``.

        """
        self.controller = controller

    def set_output_pressure(self, pressure: int):
        """
        Set the output pressure on the backing controller.

        Args:
            pressure (int): Target output pressure in mbar.

        """
        self.controller.set_veab(pressure)

    def get_output_pressure(self):
        """
        Return the current output pressure from the backing controller.

        Returns:
            The controller's current output pressure reading.

        """
        return self.controller.get_veab()

    def get_status(self):
        """
        Return the controller status.

        Raises:
            NotImplementedError: Status reporting is not yet implemented for this generic adapter.

        """
        raise NotImplementedError("PressureControl.get_status is not implemented for the generic adapter")
