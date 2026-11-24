#include "lvgl.h"
#include "display_ui.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *output_dir;
static unsigned char frame[1024*600*4], buffer[1024*600*4];
static void flush(lv_display_t *display,const lv_area_t *area,uint8_t *pixels) {
 int width=area->x2-area->x1+1;
 for(int y=area->y1;y<=area->y2;y++) memcpy(frame+(y*1024+area->x1)*4,pixels+(y-area->y1)*width*4,width*4);
 lv_display_flush_ready(display);
}
static void save(lv_display_t *display,const char *path) {
 lv_refr_now(display);
 char target[1024];snprintf(target,sizeof(target),"%s/%s",output_dir,path);
 FILE *out=fopen(target,"wb");if(!out){perror(target);exit(1);}fprintf(out,"P6\n1024 600\n255\n");
 for(int i=0;i<1024*600;i++){unsigned char rgb[3]={frame[i*4+2],frame[i*4+1],frame[i*4]};fwrite(rgb,1,3,out);}fclose(out);
}
int main(int argc,char **argv) {
 output_dir=argc>1?argv[1]:".";
 lv_init();lv_display_t *display=lv_display_create(1024,600);
 lv_display_set_color_format(display,LV_COLOR_FORMAT_XRGB8888);
 lv_display_set_buffers(display,buffer,NULL,sizeof(buffer),LV_DISPLAY_RENDER_MODE_FULL);
 lv_display_set_flush_cb(display,flush);lcd_ui_create();
 lcd_model clock={.fresh=true,.bound=true,.clock_valid=true,.received_ms=100,.local_time_ms=14*3600000+35*60000};strcpy(clock.source,"Pi Recorder");
 lcd_ui_render(&clock,100);save(display,"clock.ppm");
 lcd_model model={.fresh=true,.bound=true,.count=1,.total=1,.received_ms=100};strcpy(model.source,"Pi Recorder");
 for(int i=0;i<4;i++) {snprintf(model.timers[i].id,65,"timer-%d",i);snprintf(model.timers[i].label,321,"Timer %d",i+1);strcpy(model.timers[i].state,"scheduled");model.timers[i].time_valid=true;model.timers[i].remaining_ms=(15+i*10)*60000;}
 lcd_ui_render(&model,100);save(display,"single.ppm");
 model.count=model.total=4;lcd_ui_render(&model,100);save(display,"multiple.ppm");
 model.count=model.total=1;strcpy(model.timers[0].state,"due");model.timers[0].remaining_ms=0;lcd_ui_render(&model,100);save(display,"due.ppm");
 lcd_ui_render(&clock,100);save(display,"clock-after-timer.ppm");
 clock.clock_valid=false;lcd_ui_render(&clock,100);save(display,"clock-unknown.ppm");
 lcd_ui_render(&model,3100);save(display,"offline.ppm");
 return 0;
}
