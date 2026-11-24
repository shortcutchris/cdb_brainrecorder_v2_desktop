#include "lvgl.h"
#include "display_ui.h"
#include "timer_view.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

LV_FONT_DECLARE(cdb_text_20);
LV_FONT_DECLARE(cdb_text_24);
LV_FONT_DECLARE(cdb_text_32);
static const uint32_t CYAN=0x55E4F2, AMBER=0xFFBD69, MUTED=0x9EADB9;
static lv_obj_t *status,*cards[4],*titles[4],*times[4],*states[4],*next,*back,*help;
static lv_obj_t *focus_panel,*focus_title,*focus_state,*segments[8][7],*dots[4];
static lcd_view view;
static const lcd_model *current;
static char last_value[24];
static uint32_t last_color;

static void visible(lv_obj_t *object,bool show) {
 lv_obj_set_hidden(object,!show);
}
static lv_obj_t *text_at(lv_obj_t *parent,int x,int y,int width,const lv_font_t *font) {
 lv_obj_t *object=lv_label_create(parent);
 lv_obj_set_pos(object,x,y);lv_obj_set_size(object,width,font->line_height+2);
 lv_label_set_long_mode(object,LV_LABEL_LONG_DOT);lv_obj_set_style_text_font(object,font,0);
 return object;
}
static lv_obj_t *flat(lv_obj_t *parent,uint32_t color) {
 lv_obj_t *object=lv_obj_create(parent);lv_obj_remove_style_all(object);
 lv_obj_set_style_bg_opa(object,LV_OPA_COVER,0);lv_obj_set_style_bg_color(object,lv_color_hex(color),0);
 lv_obj_set_style_radius(object,4,0);lv_obj_set_clickable(object,false);lv_obj_set_scrollable(object,false);
 return object;
}
static void click(lv_event_t *event) {
 if (!current || !current->fresh) return;
 intptr_t action=(intptr_t)lv_event_get_user_data(event);
 if (action==10) lcd_view_next(&view,current);
 else if (action==11) lcd_view_back(&view);
 else lcd_view_select(&view,current,(int)action);
}
static lv_obj_t *button(lv_obj_t *screen,int x,const char *title,int action) {
 lv_obj_t *object=lv_btn_create(screen);lv_obj_set_pos(object,x,528);lv_obj_set_size(object,244,56);
 lv_obj_set_style_bg_color(object,lv_color_hex(0x20324D),0);
 lv_obj_set_style_text_font(object,&cdb_text_20,0);
 lv_obj_add_event_cb(object,click,LV_EVENT_CLICKED,(void *)(intptr_t)action);
 lv_obj_t *label=lv_label_create(object);lv_label_set_text(label,title);lv_obj_center(label);return object;
}
void lcd_ui_create(void) {
 lv_obj_t *screen=lv_screen_active();
 lv_obj_set_style_bg_color(screen,lv_color_hex(0x0B1421),0);
 lv_obj_set_style_text_color(screen,lv_color_hex(0xF3F6FB),0);
 lv_obj_set_scrollable(screen,false);
 lv_obj_t *heading=text_at(screen,28,20,960,&cdb_text_32);lv_label_set_text(heading,"Timer Display");
 status=text_at(screen,28,68,960,&cdb_text_20);lv_obj_set_style_text_color(status,lv_color_hex(MUTED),0);
 for (int i=0;i<4;i++) {
  cards[i]=lv_btn_create(screen);lv_obj_set_style_bg_color(cards[i],lv_color_hex(0x17273B),0);
  lv_obj_set_style_pad_all(cards[i],0,0);lv_obj_set_pos(cards[i],28+(i%2)*498,112+(i/2)*206);lv_obj_set_size(cards[i],470,186);
  lv_obj_add_event_cb(cards[i],click,LV_EVENT_CLICKED,(void *)(intptr_t)i);
  titles[i]=text_at(cards[i],20,16,420,&cdb_text_24);
  times[i]=text_at(cards[i],20,60,430,&lv_font_montserrat_48);
  states[i]=text_at(cards[i],20,125,420,&cdb_text_20);
 }
 focus_panel=flat(screen,0x101F30);lv_obj_set_pos(focus_panel,28,112);lv_obj_set_size(focus_panel,968,400);
 lv_obj_set_style_radius(focus_panel,20,0);lv_obj_set_style_border_width(focus_panel,1,0);lv_obj_set_style_border_color(focus_panel,lv_color_hex(0x284354),0);
 focus_title=text_at(focus_panel,24,22,920,&cdb_text_32);lv_obj_set_style_text_align(focus_title,LV_TEXT_ALIGN_CENTER,0);
 focus_state=text_at(focus_panel,24,336,920,&cdb_text_24);lv_obj_set_style_text_align(focus_state,LV_TEXT_ALIGN_CENTER,0);
 for (int i=0;i<8;i++) for (int j=0;j<7;j++) segments[i][j]=flat(focus_panel,0x193342);
 for (int i=0;i<4;i++) dots[i]=flat(focus_panel,CYAN);
 next=button(screen,752,"Weitere Timer",10);back=button(screen,28,"Alle Timer",11);
 help=text_at(screen,300,546,424,&cdb_text_20);lv_obj_set_style_text_align(help,LV_TEXT_ALIGN_CENTER,0);lv_obj_set_style_text_color(help,lv_color_hex(MUTED),0);
 lv_label_set_text(help,"Timer antippen für Großansicht");
 for (int i=0;i<4;i++) visible(cards[i],false);
 visible(focus_panel,false);visible(back,false);visible(next,false);visible(help,false);
}
static uint32_t state_color(lcd_time_state state) {
 return state==LCD_TIME_DUE || state==LCD_TIME_MISSED ? AMBER : state==LCD_TIME_UNKNOWN ? MUTED : CYAN;
}
static const char *state_text(lcd_time_state state) {
 switch (state) {
  case LCD_TIME_DUE:return "ABGELAUFEN";
  case LCD_TIME_MISSED:return "VERPASST";
  case LCD_TIME_UNKNOWN:return "Zeitabgleich ausstehend";
  case LCD_TIME_WAITING:return "Warte auf Timerstatus";
  case LCD_TIME_RUNNING:return "Läuft  ·  Stunden : Minuten : Sekunden";
  default:return "Verbindung unterbrochen";
 }
}
static void draw_digits(const char *value,uint32_t color) {
 if (!strcmp(last_value,value) && last_color==color) return;
 snprintf(last_value,sizeof(last_value),"%s",value);last_color=color;
 int colons=0;for (const char *c=value;*c;c++) if (*c==':') colons++;
 int count=(int)strlen(value)-colons, gap=12, colon=26, width=count==4?150:count>6?80:112, height=count==4?220:200, thick=16;
 int x=(968-(count*width+colons*colon+((int)strlen(value)-1)*gap))/2,y=count==4?94:100,digit=0,dot=0;
 for (int i=0;i<8;i++) for (int j=0;j<7;j++) visible(segments[i][j],false);
 for (int i=0;i<4;i++) visible(dots[i],false);
 for (const char *c=value;*c;c++) {
  if (*c==':') {
   for (int k=0;k<2 && dot<4;k++) {lv_obj_set_pos(dots[dot],x+(colon-thick)/2,y+height*(k+1)/3-thick/2);lv_obj_set_size(dots[dot],thick,thick);visible(dots[dot],true);lv_obj_set_style_bg_color(dots[dot++],lv_color_hex(color),0);}
   x+=colon+gap;continue;
  }
  if (digit>=8) break;
  unsigned char mask=lcd_digit_segments(*c);int half=(height-thick)/2;
  const int positions[7][4]={{thick,0,width-2*thick,thick},{width-thick,thick,thick,half-thick},{width-thick,half+thick,thick,half-thick},{thick,height-thick,width-2*thick,thick},{0,half+thick,thick,half-thick},{0,thick,thick,half-thick},{thick,half,width-2*thick,thick}};
  for (int j=0;j<7;j++) {lv_obj_t *s=segments[digit][j];lv_obj_set_pos(s,x+positions[j][0],y+positions[j][1]);lv_obj_set_size(s,positions[j][2],positions[j][3]);lv_obj_set_style_bg_color(s,lv_color_hex(mask&(1<<j)?color:0x193342),0);visible(s,true);}
  digit++;x+=width+gap;
 }
}
void lcd_ui_render(const lcd_model *model,int64_t now) {
 current=model;
 if (!model->fresh || lcd_expired(model,now)) {
  lv_label_set_text(status,"Verbindung unterbrochen - USB und Recorder prüfen");
  for (int i=0;i<4;i++) visible(cards[i],false);
  visible(focus_panel,false);visible(next,false);visible(back,false);visible(help,false);return;
 }
 int pages=(model->count+3)/4,focus=lcd_view_focus(&view,model);char info[256];
 snprintf(info,sizeof(info),"%s  |  %d Timer  |  %s%s",model->source,model->total,focus>=0?"Großansicht":"Übersicht",model->total>model->count?"  |  Weitere in der App":"");
 if (!model->count) snprintf(info,sizeof(info),"%s  |  Keine offenen Timer",model->source);
 else if (focus<0 && pages>1) snprintf(info,sizeof(info),"%s  |  %d Timer  |  Seite %d/%d%s",model->source,model->total,view.page+1,pages,model->total>model->count?"  |  Weitere in der App":"");
 lv_label_set_text(status,info);visible(focus_panel,focus>=0 || !model->count);
 for (int slot=0;slot<4;slot++) {
  int index=view.page*4+slot;bool show=focus<0 && index<model->count;visible(cards[slot],show);if (!show) continue;
  char value[24];lcd_time_state state=lcd_time_text(model,index,now,value,sizeof(value));
  lv_label_set_text(titles[slot],model->timers[index].label);lv_label_set_text(times[slot],value);
  lv_obj_set_style_text_color(times[slot],lv_color_hex(state_color(state)),0);
  lv_label_set_text(states[slot],state==LCD_TIME_RUNNING?"Läuft":state_text(state));lv_obj_set_style_text_color(states[slot],lv_color_hex(state_color(state)),0);
 }
 if (focus>=0) {
  char value[24];lcd_time_state state=lcd_time_text(model,focus,now,value,sizeof(value));
  lv_label_set_text(focus_title,model->timers[focus].label);lv_label_set_text(focus_state,state_text(state));
  lv_obj_set_style_text_color(focus_state,lv_color_hex(state_color(state)),0);draw_digits(value,state_color(state));
 }
 else if (!model->count) {
  char value[24];bool ready=lcd_clock_text(model,now,value,sizeof(value));
  lv_label_set_text(focus_title,"Uhrzeit");
  lv_label_set_text(focus_state,ready?"Ortszeit des Pi  ·  24 Stunden":"Zeitabgleich am Pi ausstehend");
  lv_obj_set_style_text_color(focus_state,lv_color_hex(MUTED),0);draw_digits(value,ready?CYAN:MUTED);
 }
 visible(next,pages>1 && focus<0);visible(back,focus>=0 && model->count>1);visible(help,model->count>1 && focus<0);
}
