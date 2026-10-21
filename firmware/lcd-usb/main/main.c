#include <assert.h>

#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/usb_serial_jtag.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_lv_adapter.h"
#include "waveshare_rgb_lcd_port.h"
#include "protocol.h"
#if LVGL_VERSION_MAJOR != 9 || LVGL_VERSION_MINOR != 6 || LVGL_VERSION_PATCH != 0
#error "Review this firmware before changing its LVGL version"
#endif
LV_FONT_DECLARE(cdb_text_20);
LV_FONT_DECLARE(cdb_text_24);
LV_FONT_DECLARE(cdb_text_32);

static lcd_model model;
static lv_obj_t *heading,*status,*cards[4],*titles[4],*times[4],*states[4],*next,*back;
static int page=0;
static char focus_id[65];
static int64_t now_ms(void){return esp_timer_get_time()/1000;}
static void new_link(void){char nonce[33];for(int i=0;i<4;i++)snprintf(nonce+i*8,9,"%08" PRIx32,esp_random());lcd_reset(&model,nonce);}
static void send_status(const char *type){
 char out[256];int n=snprintf(out,sizeof(out),"{\"protocol\":\"%s\",\"type\":\"%s\",\"nonce\":\"%s\",\"session\":\"%s\",\"seq\":%" PRIu32 "}\n",LCD_PROTOCOL,type,model.nonce,model.session,model.sequence);
 usb_serial_jtag_write_bytes(out,n,pdMS_TO_TICKS(20));
}
static void click(lv_event_t *event){
 intptr_t action=(intptr_t)lv_event_get_user_data(event);
 if(action==10){page=(page+1)%4;focus_id[0]=0;}else if(action==11){focus_id[0]=0;}else{int index=page*4+(int)action;if(index<model.count)strcpy(focus_id,model.timers[index].id);}
}
static lv_obj_t *text_at(lv_obj_t *parent,int x,int y,int width,const lv_font_t *font){
 lv_obj_t *o=lv_label_create(parent);lv_obj_set_pos(o,x,y);lv_obj_set_width(o,width);lv_label_set_long_mode(o,LV_LABEL_LONG_DOT);lv_obj_set_style_text_font(o,font,0);return o;
}
static void create_ui(void){
 lv_obj_t *screen=lv_scr_act();lv_obj_set_style_bg_color(screen,lv_color_hex(0x101B2D),0);lv_obj_set_style_text_color(screen,lv_color_hex(0xF3F6FB),0);
 heading=text_at(screen,28,20,960,&cdb_text_32);lv_label_set_text(heading,"Timerdisplay");
 status=text_at(screen,28,68,960,&cdb_text_20);
 for(int i=0;i<4;i++){
  cards[i]=lv_btn_create(screen);lv_obj_set_style_bg_color(cards[i],lv_color_hex(0x20324D),0);lv_obj_set_style_pad_all(cards[i],0,0);
  lv_obj_add_event_cb(cards[i],click,LV_EVENT_CLICKED,(void *)(intptr_t)i);
  titles[i]=text_at(cards[i],20,16,420,&cdb_text_24);
  times[i]=text_at(cards[i],20,60,420,&lv_font_montserrat_48);
  states[i]=text_at(cards[i],20,125,420,&cdb_text_20);
 }
 next=lv_btn_create(screen);lv_obj_set_pos(next,752,538);lv_obj_set_size(next,244,46);lv_obj_add_event_cb(next,click,LV_EVENT_CLICKED,(void *)10);
 lv_obj_t *label=lv_label_create(next);lv_label_set_text(label,"Weitere Timer");lv_obj_center(label);
 back=lv_btn_create(screen);lv_obj_set_pos(back,28,538);lv_obj_set_size(back,244,46);lv_obj_add_event_cb(back,click,LV_EVENT_CLICKED,(void *)11);
 label=lv_label_create(back);lv_label_set_text(label,"Alle Timer");lv_obj_center(label);
}
static void visible(lv_obj_t *o,bool show){if(show)lv_obj_clear_flag(o,LV_OBJ_FLAG_HIDDEN);else lv_obj_add_flag(o,LV_OBJ_FLAG_HIDDEN);}
static void render(int64_t now){
 if(!model.fresh){lv_label_set_text(status,"Verbindung unterbrochen - USB und Recorder prüfen");for(int i=0;i<4;i++)visible(cards[i],false);visible(next,false);visible(back,false);return;}
 int pages=(model.count+3)/4;if(page>=pages)page=0;
 int focus=-1;for(int i=0;i<model.count;i++)if(!strcmp(model.timers[i].id,focus_id))focus=i;
 if(focus<0)focus_id[0]=0;
 char info[256];snprintf(info,sizeof(info),"%s  |  %d Timer  |  Seite %d/%d%s",model.source,model.total,page+1,pages?pages:1,model.total>model.count?"  |  Weitere in der App":"");
 if(!model.count)snprintf(info,sizeof(info),"%s  |  Keine offenen Timer",model.source);
 lv_label_set_text(status,info);
 for(int slot=0;slot<4;slot++){
  int index=focus>=0?focus:page*4+slot;bool show=index<model.count&&(focus<0||slot==0);visible(cards[slot],show);if(!show)continue;
  lcd_timer *t=&model.timers[index];lv_obj_set_pos(cards[slot],28+(slot%2)*498,112+(slot/2)*206);lv_obj_set_size(cards[slot],470,186);
  if(focus>=0){lv_obj_set_pos(cards[slot],28,112);lv_obj_set_size(cards[slot],968,400);}
  lv_obj_set_width(titles[slot],focus>=0?920:420);lv_label_set_text(titles[slot],t->label);
  int64_t ms=lcd_remaining(&model,index,now);char value[48];
  if(ms<0)strcpy(value,"--:--");else{int64_t secs=(ms+999)/1000;snprintf(value,sizeof(value),"%02" PRId64 ":%02" PRId64 ":%02" PRId64,secs/3600,(secs/60)%60,secs%60);}
  lv_label_set_text(times[slot],value);
  bool due=!strcmp(t->state,"due"),missed=!strcmp(t->state,"missed");
  lv_label_set_text(states[slot],!t->time_valid?"Zeitabgleich ausstehend":due?"ABGELAUFEN":missed?"VERPASST":ms==0?"Warte auf Timerstatus":"Läuft");
  lv_obj_set_style_text_color(states[slot],lv_color_hex(due||missed?0xFFBD69:0xA6E3CA),0);
 }
 visible(next,pages>1&&focus<0);visible(back,focus>=0);
}
void app_main(void){
 usb_serial_jtag_driver_config_t usb={.tx_buffer_size=1024,.rx_buffer_size=LCD_FRAME_SIZE};ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
 esp_lcd_panel_handle_t panel=NULL;esp_lcd_touch_handle_t touch=NULL;
 esp_lv_adapter_rotation_t rotation=ESP_LV_ADAPTER_ROTATE_0;
 ESP_ERROR_CHECK(waveshare_esp32_s3_rgb_lcd_init(ESP_LV_ADAPTER_TEAR_AVOID_MODE_DEFAULT_RGB,rotation,&panel,&touch));
 ESP_ERROR_CHECK(waveshare_rgb_lcd_backlight_on());
 esp_lv_adapter_config_t config=ESP_LV_ADAPTER_DEFAULT_CONFIG();config.task_stack_size=12*1024;config.stack_in_psram=true;ESP_ERROR_CHECK(esp_lv_adapter_init(&config));
 esp_lv_adapter_display_config_t display=ESP_LV_ADAPTER_DISPLAY_RGB_DEFAULT_CONFIG(panel,NULL,EXAMPLE_LCD_H_RES,EXAMPLE_LCD_V_RES,rotation);display.profile.use_psram=true;
 lv_display_t *disp=esp_lv_adapter_register_display(&display);assert(disp);
 if(touch){esp_lv_adapter_touch_config_t cfg=ESP_LV_ADAPTER_TOUCH_DEFAULT_CONFIG(disp,touch);assert(esp_lv_adapter_register_touch(&cfg));}
 ESP_ERROR_CHECK(esp_lv_adapter_start());ESP_ERROR_CHECK(esp_lv_adapter_lock(-1));create_ui();esp_lv_adapter_unlock();
 new_link();static char line[LCD_FRAME_SIZE];size_t length=0;bool dropping=false;int64_t hello=0,draw=0,last_byte=0;
 while(true){
  unsigned char chunk[256];int count=usb_serial_jtag_read_bytes(chunk,sizeof(chunk),pdMS_TO_TICKS(20));int64_t now=now_ms();
  ESP_ERROR_CHECK(esp_lv_adapter_lock(-1));
  if(lcd_expired(&model,now)){new_link();length=0;dropping=false;}
  if(length&&now-last_byte>1000){length=0;dropping=false;}
  for(int i=0;i<count;i++){
   last_byte=now;
   if(chunk[i]=='\n'){
    if(!dropping){line[length]=0;int accepted=lcd_accept(&model,line,now);if(accepted)send_status(accepted==1?"bound":"ack");}
    length=0;dropping=false;
   }else if(!dropping){if(chunk[i]==0||length+1>=sizeof(line)){length=0;dropping=true;}else line[length++]=(char)chunk[i];}
  }
  if(!model.bound&&now>=hello){send_status("hello");hello=now+1000;}
  if(now>=draw){render(now);draw=now+100;}
  esp_lv_adapter_unlock();
 }
}
