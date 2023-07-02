from busio import I2C
from adafruit_bus_device import i2c_device

try:
    from typing import Union
except ImportError:
    pass

_OSCILATOR_ON = 0x21
_DISPLAY_ENABLE = 0b10000001
_DISPLAY_BLINK_2HZ = 0b10000011
_DISPLAY_BLINK_1HZ = 0b10000101
_DISPLAY_BLINK_05HZ = 0b100000111

'''
     7>--
    2>|  |<6
     1>--
    3>|  |<5
     4>--.<0
'''
_CHARS = {
    " ": 0b00000000,
    ".": 0b10000000,
    "*": 0b01100011,
    "=": 0b01001000,
    "-": 0b01000000,
    "_": 0b00001000,
    ":": 0b00001001,
    "(": 0b00111001,
    "[": 0b00111001,
    ")": 0b00001111,
    "]": 0b00001111,
    "0": 0b00111111,
    "1": 0b00000110,
    "2": 0b01011011,
    "3": 0b01001111,
    "4": 0b01100110,
    "5": 0b01101101,
    "6": 0b01111101,
    "7": 0b00000111,
    "8": 0b01111111,
    "9": 0b01101111,
    "A": 0b01110111,
    "b": 0b01111100,
    "C": 0b00111001,
    "c": 0b01011000,
    "d": 0b01011110,
    "E": 0b01111001,
    "F": 0b01110001,
    "G": 0b01111101,
    "H": 0b01110110,
    "h": 0b01110100,
    "I": 0b00000110,
    "i": 0b00000100,
    "J": 0b00011111,
    "L": 0b00111000,
    "Ł": 0b01111000,
    "O": 0b00111111,
    "P": 0b01110011,
    "U": 0b00111110,
    "N": 0b00110111,
    "Z": 0b01011011,
}

class Display:
    def __init__(
        self,
        i2c: I2C,
        address: int = 0x70,
        auto_write: bool = True,
    ) -> None:
        # Initializing variables.
        self._auto_write: bool = auto_write
        self._temp: bytearray = bytearray(1)
        self._i2c_device = i2c_device.I2CDevice(i2c, address)
        self._buffer_size: int = 1 + 16
        self._buffer: bytearray = bytearray(self._buffer_size)

        # Setting up display.
        self.clear(True)
        self._write_cmd(_OSCILATOR_ON)
        self._write_cmd(_DISPLAY_ENABLE)

    def _write_cmd(self, byte: bytearray) -> None:
        """Writes bytearray to the display."""
        self._temp[0] = byte
        with self._i2c_device:
            self._i2c_device.write(self._temp)
    
    def _round_down(self, value: float, decimals: int):
        """Rounds down number to given number of decimal places."""\
        # Szczerze to nie wiem czy to działa XDDD
        factor = 1 / (10 ** decimals)
        return ((int) (value // factor)) * factor

    def blink(self, value: int):
        """Sets blinking speed of display.
        0 - OFF 
        1 - 0.5 Hz 
        2 - 1 Hz 
        3 - 2 Hz"""
        if value not in [0, 1, 2, 3]:
            raise ValueError("Accepted values are 0, 1, 2 or 3. Got {}".format(value))
        if value == 0:
            self._write_cmd(_DISPLAY_ENABLE)
        if value == 1:
            self._write_cmd(_DISPLAY_BLINK_05HZ)
        if value == 2:
            self._write_cmd(_DISPLAY_BLINK_1HZ)
        if value == 3:
            self._write_cmd(_DISPLAY_BLINK_2HZ)

    def _clear_buff(self) -> None:
        self._buffer = bytearray(self._buffer_size)

    def clear(self, force_show: bool = False):
        self._clear_buff()

        if self._auto_write or force_show:
            self.show()
            
    
    def show(self) -> None:
        """Update display."""
        with self._i2c_device:
            self._i2c_device.write(self._buffer)

    def print(self, value: str) -> None:
        """Print the value to the display.
        
        value: The value to print. (str)
        """
        if not isinstance(value, str):
            raise ValueError("Type not supported: {}".format(type(value)))
        
        final_index = 0
        skip_next = False

        for index, char in enumerate(value):
            if final_index >= 8:
                break
            if skip_next:
                skip_next = False
                continue
            if char == '.':
                # print just dot
                self._put(char, final_index)
                final_index += 1
            else:
                if index + 1 < len(value) and value[index + 1] == '.':
                    # print current with dot
                    self._put(char, final_index, True)
                    final_index += 1
                    skip_next = True
                else:
                    self._put(char, final_index)
                    final_index += 1

        if self._auto_write:
            self.show()

    def _put_raw(self, byte: Union[bytes, bytearray], index: int = 0) -> None:
        if index < 0 or index > 7:
            raise ValueError("Index out of range. ({})".format(index))
        
        if len(byte) != 1:
            raise ValueError("Expected one byte got: {}".format(len(byte)))
        
        buffer_index = 1+2*index

        self._buffer[buffer_index] = byte[0]

    def _put(self, char: str, index: int, dot: bool = False) -> None:
        """Place character on specified index into buffer."""
        if len(char) != 1:
            raise ValueError("Expected one character, got {}".format(len(char)))

        byte = bytearray([0x00])

        if char in _CHARS:
            byte[0] = _CHARS[char]

        if dot:
            byte[0] |= 0b10000000
        
        self._put_raw(byte, index)
