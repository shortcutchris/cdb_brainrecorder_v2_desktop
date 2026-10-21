idf_component_register(SRCS "main.c" "protocol.c" "../vendor/waveshare_rgb_lcd_port.c"
 INCLUDE_DIRS "." "../vendor" REQUIRES json esp_driver_usb_serial_jtag esp_timer)
