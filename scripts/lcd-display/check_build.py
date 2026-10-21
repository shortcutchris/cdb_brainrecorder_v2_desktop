#!/usr/bin/env python3
"""Reject successful compilations with an unsafe or wrong device configuration."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'firmware/lcd-usb'
config=json.loads((root/'build/config/sdkconfig.json').read_text())
expected={'IDF_TARGET':'esp32s3','ESPTOOLPY_FLASHSIZE':'16MB',
          'ESP_CONSOLE_UART_DEFAULT':True,'ESP_CONSOLE_SECONDARY_NONE':True,
          'ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG':False,'ESP_CONSOLE_USB_SERIAL_JTAG':False,
          'ESP_CONSOLE_USB_CDC':False,'SPIRAM_MODE_OCT':True,'SPIRAM_SPEED':80,
          'LV_COLOR_DEPTH':16,'ESP_MAIN_TASK_STACK_SIZE':20000}
for key,value in expected.items():
    if config.get(key)!=value:raise SystemExit(f'Wrong firmware configuration: {key}={config.get(key)!r}, expected {value!r}')
print('Firmware target, memory, stack, color depth and UART-only diagnostics verified.')
