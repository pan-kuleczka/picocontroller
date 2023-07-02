import board
import time
import struct
import digitalio
import analogio
import bitbangio
import usb_hid
import adafruit_hid
import microcontroller

from lib.display import Display as LedDisplay

### SETTINGS ###
button_count = 8
i2c_sda = board.GP0
i2c_scl = board.GP1
io_expander_addresses = [
    0x38
]  # Buttons will be assigned sequentially, from least significant bit

analog_pins = [board.A0]  # Each analog pin is a separate axis
################

button_byte_count = int(button_count / 8) if button_count % 8 == 0 else int(button_count / 8) + 1  # button_bytes = button_count / 8 rounded up
axes_byte_count = len(analog_pins)  # Each axis needs a separate byte
report_byte_count = button_byte_count + axes_byte_count

class IOExpander:
    def __init__(self, i2c, address=0x38, bytes=1):
        # Default address for PCF8574A with address pins pulled down
        self.i2c = i2c
        self.address = address
        self.bytes = bytes

    def read_bytes(self):
        buffer = bytearray(self.bytes)
        while not self.i2c.try_lock():
            time.sleep(0.1)
        self.i2c.readfrom_into(self.address, buffer)
        self.i2c.unlock()
        return buffer


class AnalogInput:
    def __init__(self, pin, min_input=0, max_input=65535):
        self.pin = analogio.AnalogIn(pin)
        self.min_input = min_input
        self.max_input = max_input

    def get_input(self):
        raw_value = self.pin.value
        return (raw_value - self.min_input) / (self.max_input - self.min_input)


class InputManager:
    def __init__(self, i2c):
        self.i2c = i2c
        physical_button_count = 0

        self.io_expanders = [
            IOExpander(self.i2c, address) for address in io_expander_addresses
        ]

        for io_expander in self.io_expanders:
            physical_button_count += io_expander.bytes * 8

        if physical_button_count < button_count:
            raise Exception("There are more virtual buttons than bits provided by the I/O expanders")

        self.analog_inputs = [
            AnalogInput(analog_pin) for analog_pin in analog_pins
        ]

    def get_button_states(self):
        button_states = []

        # Separate I/O expanders' data into bits, but not more than the specified button_count (to avoid handling unconnected/invalid inputs)
        for io_expander in self.io_expanders:
            raw_bytes = io_expander.read_bytes()
            for bit in range(io_expander.bytes * 8):
                bytes_index = int(bit / 8)
                button_states.append(bool(raw_bytes[bytes_index] & (1 << bit)))
                if len(button_states) >= button_count:
                    break 
            if len(button_states) >= button_count:
                break                

        return button_states

    def get_axes_states(self):
        return [analog_input.get_input() for analog_input in self.analog_inputs]

# Controller driver based on https://github.com/adafruit/Adafruit_CircuitPython_HID/blob/main/examples/hid_gamepad.py
class Controller:
    def __init__(self):
        self.i2c = bitbangio.I2C(i2c_scl, i2c_sda)

        self.input_manager = InputManager(self.i2c)
        self.ledDisplay = LedDisplay(self.i2c)

        self.device = adafruit_hid.find_device(usb_hid.devices, usage_page=0x01, usage=0x05)
        self.state = [0x00] * report_byte_count

        self.report = bytearray(report_byte_count)
        # Remember the last report as well, so we can avoid sending duplicate reports.
        self.last_report = bytearray(report_byte_count)

        # Send an initial report to test if HID device is ready.
        # If not, wait a bit and try once more.
        self.update_state()
        try:
            self.send(always=True)
        except OSError:
            time.sleep(1)
            self.send(always=True)

    def update_state(self):
        self.state = [0x00] * report_byte_count

        button_states = self.input_manager.get_button_states()
        for i, button_state in enumerate(button_states):
            byte_index = int(i / 8)
            bit_index = i % 8
            self.state[byte_index] |= button_state << bit_index

        axes_states = self.input_manager.get_axes_states()
        for i, axis_state in enumerate(axes_states):
            axis_value = -128 + int(255 * axis_state) # Axis state is a byte
            self.state[button_byte_count + i] = axis_value


    def send(self, always=False):
        # Send a report with all the existing settings.
        # If ``always`` is ``False`` (the default), send only if there have been changes.
        
        struct.pack_into(
            "<" + "B" * button_byte_count + "b" * axes_byte_count,
            self.report,
            0,
            *self.state
        )

        if always or self.last_report != self.report:
            self.device.send_report(self.report)
            # Remember what we sent, without allocating new storage.
            self.last_report = self.report

def main():
    controller = Controller()

    board_led = digitalio.DigitalInOut(board.LED)
    board_led.direction = digitalio.Direction.OUTPUT

    while True:
        board_led.value = not board_led.value

        controller.update_state()
        controller.send(always=True)

        temperature = microcontroller.cpu.temperature
        controller.ledDisplay.print("{:.1f}".format(temperature) + "*C")
        
        time.sleep(0.5)

if __name__ == "__main__":
    main()
