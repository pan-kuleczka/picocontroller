import usb_hid
from main import button_count, analog_pins, report_byte_count

# Code based on https://learn.adafruit.com/customizing-usb-devices-in-circuitpython/hid-devices

report = []
axes_usages = [
    [0x09, 0x30],  #   Usage (X)
    [0x09, 0x31],  #   Usage (Y)
    [0x09, 0x32],  #   Usage (Z)
    [0x09, 0x35],  #   Usage (Rz) 
]

if len(analog_pins) > len(axes_usages):
    raise IndexError(
        "Too many analog axes (there aren't enough HID usages to accomodate all of the analog pins)"
    )

report += [
    0x05,
    0x01,  # Usage Page (Generic Desktop Ctrls)
    0x09,
    0x05,  # Usage (Game Pad)
    0xA1,
    0x01,  # Collection (Application)
    0x85,
    0x04,  #   Report ID (4)
    0x05,
    0x09,  #   Usage Page (Button)
    0x19,
    0x01,  #   Usage Minimum (Button 1)
    0x29,
    button_count,  # Usage maximum
    0x15,
    0x00,  #   Logical Minimum (0)
    0x25,
    0x01,  #   Logical Maximum (1)
    0x75,
    0x01,  #   Report Size (1)
    0x95,
    button_count,  # Report count
    0x81,
    0x02,  #   Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x05,
    0x01,  #   Usage Page (Generic Desktop Ctrls)
    0x15,
    0x81,  #   Logical Minimum (-127)
    0x25,
    0x7F  #   Logical Maximum (127)
]

for i in range(len(analog_pins)):
    report += axes_usages[i]

report += [
    0x75,
    0x08,  # Report Size (8)
    0x95,
    len(analog_pins),  # Report count
    0x81,
    0x02,  # Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0xC0  # End Collection
]

gamepad = usb_hid.Device(
    report_descriptor=bytes(report),
    usage_page=0x01,  # Generic Desktop Control
    usage=0x05,  # Gamepad
    report_ids=(4,),  # Descriptor uses report ID 4.
    in_report_lengths=(report_byte_count,),  # This gamepad sends report_bytes bytes in its report.
    out_report_lengths=(0,),  # It does not receive any reports.
)

usb_hid.enable((usb_hid.Device.KEYBOARD, usb_hid.Device.MOUSE,
                usb_hid.Device.CONSUMER_CONTROL, gamepad))
