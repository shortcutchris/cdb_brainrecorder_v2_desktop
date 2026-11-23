#include "main/timer_view.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static lcd_model fixture(int count) {
    lcd_model model = {.fresh = true, .bound = true, .count = count, .total = count, .received_ms = 100};
    for (int i = 0; i < count; i++) {
        snprintf(model.timers[i].id, sizeof(model.timers[i].id), "timer-%d", i);
        strcpy(model.timers[i].state, "scheduled");
        model.timers[i].time_valid = true;
        model.timers[i].remaining_ms = 65000;
    }
    return model;
}

int main(void) {
    lcd_view view = {0};
    lcd_model model = fixture(1);
    assert(lcd_view_focus(&view, &model) == 0);
    assert(view.focus_id[0] == 0);

    model = fixture(2);
    assert(lcd_view_focus(&view, &model) == -1);
    lcd_view_select(&view, &model, 1);
    assert(lcd_view_focus(&view, &model) == 1);
    lcd_timer swap = model.timers[0];
    model.timers[0] = model.timers[1];
    model.timers[1] = swap;
    assert(lcd_view_focus(&view, &model) == 0);
    lcd_view_back(&view);
    assert(lcd_view_focus(&view, &model) == -1);

    model = fixture(9);
    lcd_view_next(&view, &model);
    assert(view.page == 1);
    lcd_view_select(&view, &model, 3);
    assert(lcd_view_focus(&view, &model) == 7);
    lcd_view_next(&view, &model);
    assert(view.page == 2 && lcd_view_focus(&view, &model) == -1);
    lcd_view_next(&view, &model);
    assert(view.page == 0);
    lcd_view_select(&view, &model, 3);
    model.count = 2;
    assert(lcd_view_focus(&view, &model) == -1 && view.focus_id[0] == 0);
    model.count = 1;
    assert(lcd_view_focus(&view, &model) == 0);
    model.count = 0;
    assert(lcd_view_focus(&view, &model) == -1);

    char value[24];
    model = fixture(1);
    assert(lcd_time_text(&model, 0, 101, value, sizeof(value)) == LCD_TIME_RUNNING);
    assert(strcmp(value, "00:01:05") == 0);
    model.timers[0].remaining_ms = 1000;
    assert(lcd_time_text(&model, 0, 1100, value, sizeof(value)) == LCD_TIME_WAITING);
    assert(strcmp(value, "00:00:00") == 0);
    strcpy(model.timers[0].state, "due");
    model.timers[0].remaining_ms = 0;
    assert(lcd_time_text(&model, 0, 1100, value, sizeof(value)) == LCD_TIME_DUE);
    assert(lcd_time_text(&model, 0, 3100, value, sizeof(value)) == LCD_TIME_OFFLINE);
    assert(strcmp(value, "--:--:--") == 0);
    model.timers[0].time_valid = false;
    assert(lcd_time_text(&model, 0, 101, value, sizeof(value)) == LCD_TIME_UNKNOWN);
    model = fixture(1);
    model.timers[0].remaining_ms = 31622400000LL;
    assert(lcd_time_text(&model, 0, 100, value, sizeof(value)) == LCD_TIME_RUNNING);
    assert(strcmp(value, "8784:00:00") == 0);
    assert(lcd_digit_segments('8') == 0x7f);
    assert(lcd_digit_segments('0') == 0x3f);
    assert(lcd_digit_segments('-') == 0x40);
    assert(lcd_digit_segments('?') == 0);
    puts("Timer view: automatic single timer, overview, touch focus, paging, status and timeout passed");
}
