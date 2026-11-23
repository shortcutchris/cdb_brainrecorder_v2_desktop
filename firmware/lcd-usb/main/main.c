#include <assert.h>

#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "tinyusb_default_config.h"
#include "tinyusb_cdc_acm.h"
#include "tusb.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_lv_adapter.h"
#include "waveshare_rgb_lcd_port.h"
#include "protocol.h"
#if LVGL_VERSION_MAJOR != 9 || LVGL_VERSION_MINOR != 6 || LVGL_VERSION_PATCH != 0
#error "Review this firmware before changing its LVGL version"
#endif
#include "display_ui.h"

static lcd_model model;
static int64_t now_ms(void){return esp_timer_get_time()/1000;}
static void new_link(void){char nonce[33];for(int i=0;i<4;i++)snprintf(nonce+i*8,9,"%08" PRIx32,esp_random());lcd_reset(&model,nonce);}
static void send_status(const char *type){
 char out[256];int n=snprintf(out,sizeof(out),"{\"protocol\":\"%s\",\"type\":\"%s\",\"nonce\":\"%s\",\"session\":\"%s\",\"seq\":%" PRIu32 "}\n",LCD_PROTOCOL,type,model.nonce,model.session,model.sequence);
 tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0,(const uint8_t *)out,n);
 (void)tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0,0);
}
// One CDC interface pair, bus-powered, 500 mA (board nominal draw: 450 mA).
// Product/manufacturer and per-chip serial come from the pinned TinyUSB defaults.
static const uint8_t usb_configuration[] = {
 TUD_CONFIG_DESCRIPTOR(1,2,0,TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN,0,500),
 TUD_CDC_DESCRIPTOR(0,4,0x81,8,0x02,0x82,64)
};
void app_main(void){
 tinyusb_config_t usb=TINYUSB_DEFAULT_CONFIG();
 usb.descriptor.full_speed_config=usb_configuration;
 ESP_ERROR_CHECK(tinyusb_driver_install(&usb));
 tinyusb_config_cdcacm_t cdc={.cdc_port=TINYUSB_CDC_ACM_0};
 ESP_ERROR_CHECK(tinyusb_cdcacm_init(&cdc));
 esp_lcd_panel_handle_t panel=NULL;esp_lcd_touch_handle_t touch=NULL;
 esp_lv_adapter_rotation_t rotation=ESP_LV_ADAPTER_ROTATE_0;
 ESP_ERROR_CHECK(waveshare_esp32_s3_rgb_lcd_init(ESP_LV_ADAPTER_TEAR_AVOID_MODE_DEFAULT_RGB,rotation,&panel,&touch));
 ESP_ERROR_CHECK(waveshare_rgb_lcd_backlight_on());
 esp_lv_adapter_config_t config=ESP_LV_ADAPTER_DEFAULT_CONFIG();config.task_stack_size=12*1024;config.stack_in_psram=true;ESP_ERROR_CHECK(esp_lv_adapter_init(&config));
 esp_lv_adapter_display_config_t display=ESP_LV_ADAPTER_DISPLAY_RGB_DEFAULT_CONFIG(panel,NULL,EXAMPLE_LCD_H_RES,EXAMPLE_LCD_V_RES,rotation);display.profile.use_psram=true;
 lv_display_t *disp=esp_lv_adapter_register_display(&display);assert(disp);
 if(touch){esp_lv_adapter_touch_config_t cfg=ESP_LV_ADAPTER_TOUCH_DEFAULT_CONFIG(disp,touch);assert(esp_lv_adapter_register_touch(&cfg));}
 ESP_ERROR_CHECK(esp_lv_adapter_start());ESP_ERROR_CHECK(esp_lv_adapter_lock(-1));lcd_ui_create();esp_lv_adapter_unlock();
 new_link();static char line[LCD_FRAME_SIZE];size_t length=0;bool dropping=false;int64_t hello=0,draw=0,last_byte=0;
 while(true){
  unsigned char chunk[256];size_t count=0;
  ESP_ERROR_CHECK(tinyusb_cdcacm_read(TINYUSB_CDC_ACM_0,chunk,sizeof(chunk),&count));
  vTaskDelay(pdMS_TO_TICKS(20));int64_t now=now_ms();
  ESP_ERROR_CHECK(esp_lv_adapter_lock(-1));
  if(lcd_expired(&model,now)){new_link();length=0;dropping=false;}
  if(length&&now-last_byte>1000){length=0;dropping=false;}
  for(size_t i=0;i<count;i++){
   last_byte=now;
   if(chunk[i]=='\n'){
    if(!dropping){line[length]=0;int accepted=lcd_accept(&model,line,now);if(accepted)send_status(accepted==1?"bound":"ack");}
    length=0;dropping=false;
   }else if(!dropping){if(chunk[i]==0||length+1>=sizeof(line)){length=0;dropping=true;}else line[length++]=(char)chunk[i];}
  }
  if(!model.bound&&now>=hello){send_status("hello");hello=now+1000;}
  if(now>=draw){lcd_ui_render(&model,now);draw=now+100;}
  esp_lv_adapter_unlock();
 }
}
