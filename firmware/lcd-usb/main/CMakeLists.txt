idf_component_register(SRCS "fonts/cdb_text_20.c" "fonts/cdb_text_24.c" "fonts/cdb_text_32.c" "main.c" "protocol.c" "../vendor/waveshare_rgb_lcd_port.c"
 INCLUDE_DIRS "." "../vendor" REQUIRES json esp_driver_usb_serial_jtag esp_timer)
target_compile_definitions(${COMPONENT_LIB} PRIVATE LV_LVGL_H_INCLUDE_SIMPLE)
