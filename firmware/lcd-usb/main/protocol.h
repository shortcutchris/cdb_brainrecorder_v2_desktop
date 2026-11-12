#pragma once
#include <stdbool.h>
#include <stdint.h>
#define LCD_MAX_TIMERS 16
#define LCD_FRAME_SIZE 8192
#define LCD_PROTOCOL "cdb.lcd/1"
typedef struct { char id[65], label[321], state[10]; int revision; int64_t remaining_ms; bool time_valid; } lcd_timer;
typedef struct { char nonce[33], session[33], source[161]; bool bound, fresh; uint32_t sequence; int count, total; int64_t received_ms; lcd_timer timers[LCD_MAX_TIMERS]; } lcd_model;
void lcd_reset(lcd_model *m, const char *nonce);
// Returns 1 on bind, 2 on snapshot, 0 on rejection. Invalid input never renews freshness.
int lcd_accept(lcd_model *m, const char *json, int64_t now_ms);
bool lcd_expired(const lcd_model *m, int64_t now_ms);
int64_t lcd_remaining(const lcd_model *m, int index, int64_t now_ms);
