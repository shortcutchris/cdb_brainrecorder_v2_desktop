#!/usr/bin/env python3
"""Fetch exact vendor BSP outside Git; never fetch models or touch hardware."""
import argparse,hashlib,io,pathlib,urllib.request,zipfile
URL='https://files.waveshare.com/wiki/ESP32-S3-Touch-LCD-5/ESP32-S3-Touch-LCD-5-Demo.zip'
SHA='ba208ac802387189a079930dbc4b40bfacd1d8608045aba3b9b2838be5a8fbcd'
p=argparse.ArgumentParser();p.add_argument('--archive',type=pathlib.Path);a=p.parse_args()
data=a.archive.read_bytes() if a.archive else urllib.request.urlopen(URL,timeout=120).read()
if hashlib.sha256(data).hexdigest()!=SHA:raise SystemExit('Vendor archive changed; review before updating pin')
z=zipfile.ZipFile(io.BytesIO(data));out=pathlib.Path(__file__).resolve().parents[2]/'firmware/lcd-usb/vendor';out.mkdir(exist_ok=True)
for name in ('waveshare_rgb_lcd_port.c','waveshare_rgb_lcd_port.h'):
 raw=z.read('ESP32-S3-Touch-LCD-5-Demo/ESP-IDF/08_lvgl_v8_demo/components/'+name)
 if name.endswith('.h'):
  assert b'#define EXAMPLE_USE_1024_600_LCD    0' in raw
  raw=raw.replace(b'#define EXAMPLE_USE_1024_600_LCD    0',b'#define EXAMPLE_USE_1024_600_LCD    1')
 (out/name).write_bytes(raw)
print('Pinned Waveshare 5B BSP prepared; 1024x600 selected.')
