"""Generic Pressure control class."""


class PressureControl:
    def __init__(self, controller):
        self.controller = controller

    def set_output_pressure(self, pressure: int):
        self.controller.set_veab(pressure)

    def get_output_pressure(self):
        self.controller.get_veab()

    def get_status(self):
        pass
