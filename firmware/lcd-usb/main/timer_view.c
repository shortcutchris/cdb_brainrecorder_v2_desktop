#include "timer_view.h"
#include <stdio.h>
#include <string.h>
#include <inttypes.h>

int lcd_view_focus(lcd_view *view, const lcd_model *model) {
 if (!model->fresh) return -1;
 int pages=(model->count+3)/4;
 if (view->page<0 || view->page>=pages) view->page=0;
 int focus=-1;
 for (int i=0;i<model->count;i++) if (!strcmp(model->timers[i].id,view->focus_id)) focus=i;
 if (focus<0) view->focus_id[0]=0;
 // Automatic focus is not a pinned selection: a second timer restores the overview.
 return model->count==1 ? 0 : focus;
}
void lcd_view_select(lcd_view *view, const lcd_model *model, int slot) {
 int index=view->page*4+slot;
 if (model->fresh && slot>=0 && slot<4 && index>=0 && index<model->count)
  strcpy(view->focus_id,model->timers[index].id);
}
void lcd_view_next(lcd_view *view, const lcd_model *model) {
 int pages=(model->count+3)/4;
 view->page=pages ? (view->page+1)%pages : 0;
 view->focus_id[0]=0;
}
void lcd_view_back(lcd_view *view) { view->focus_id[0]=0; }
lcd_time_state lcd_time_text(const lcd_model *model, int index, int64_t now, char *out, size_t size) {
 snprintf(out,size,"--:--:--");
 if (!model->fresh || lcd_expired(model,now) || index<0 || index>=model->count) return LCD_TIME_OFFLINE;
 const lcd_timer *timer=&model->timers[index];
 int64_t ms=lcd_remaining(model,index,now);
 if (ms<0) return LCD_TIME_UNKNOWN;
 int64_t seconds=(ms+999)/1000;
 snprintf(out,size,"%02" PRId64 ":%02" PRId64 ":%02" PRId64,seconds/3600,(seconds/60)%60,seconds%60);
 if (!strcmp(timer->state,"due")) return LCD_TIME_DUE;
 if (!strcmp(timer->state,"missed")) return LCD_TIME_MISSED;
 return ms==0 ? LCD_TIME_WAITING : LCD_TIME_RUNNING;
}
bool lcd_clock_text(const lcd_model *model, int64_t now, char *out, size_t size) {
 snprintf(out,size,"--:--");
 if (!model->fresh || lcd_expired(model,now) || model->count || !model->clock_valid) return false;
 int64_t minutes=((model->local_time_ms+now-model->received_ms)/60000)%1440;
 snprintf(out,size,"%02" PRId64 ":%02" PRId64,minutes/60,minutes%60);
 return true;
}
unsigned char lcd_digit_segments(char digit) {
 // a,b,c,d,e,f,g; punctuation is drawn separately.
 static const unsigned char masks[]={0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
 return digit>='0' && digit<='9' ? masks[digit-'0'] : digit=='-' ? 0x40 : 0;
}
