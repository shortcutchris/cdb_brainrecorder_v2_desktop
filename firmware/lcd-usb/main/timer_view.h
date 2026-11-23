#pragma once
#include "protocol.h"
#include <stddef.h>

typedef struct { int page; char focus_id[65]; } lcd_view;
typedef enum { LCD_TIME_OFFLINE, LCD_TIME_UNKNOWN, LCD_TIME_RUNNING, LCD_TIME_WAITING, LCD_TIME_DUE, LCD_TIME_MISSED } lcd_time_state;

int lcd_view_focus(lcd_view *view, const lcd_model *model);
void lcd_view_select(lcd_view *view, const lcd_model *model, int slot);
void lcd_view_next(lcd_view *view, const lcd_model *model);
void lcd_view_back(lcd_view *view);
lcd_time_state lcd_time_text(const lcd_model *model, int index, int64_t now, char *out, size_t size);
unsigned char lcd_digit_segments(char digit);
