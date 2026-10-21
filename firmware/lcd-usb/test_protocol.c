#include "main/protocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define PREFIX "\"protocol\":\"cdb.lcd/1\",\"nonce\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"session\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\","
int main(void){
 lcd_model m;lcd_reset(&m,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
 const char *bind="{" PREFIX "\"type\":\"bind\",\"source\":\"Pi\"}";
 const char *snap="{" PREFIX "\"type\":\"snapshot\",\"seq\":1,\"total\":1,\"timers\":[{\"id\":\"one\",\"label\":\"Küche\",\"revision\":1,\"state\":\"scheduled\",\"remaining_ms\":5000,\"time_valid\":true}]}";
 assert(lcd_accept(&m,snap,0)==0);assert(lcd_accept(&m,bind,10)==1);assert(lcd_accept(&m,snap,100)==2);
 assert(!strcmp(m.timers[0].label,"Küche"));assert(lcd_remaining(&m,0,1100)==4000);
 assert(lcd_accept(&m,snap,2000)==0);assert(m.received_ms==100);assert(lcd_expired(&m,3100));assert(lcd_remaining(&m,0,3100)==-1);
 // A fresh link challenge invalidates delayed packets from the previous source/session.
 lcd_reset(&m,"cccccccccccccccccccccccccccccccc");assert(lcd_accept(&m,bind,3200)==0);assert(lcd_accept(&m,snap,3200)==0);
 lcd_reset(&m,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");assert(lcd_accept(&m,bind,0)==1);assert(lcd_accept(&m,snap,10)==2);
 const char *bad="{" PREFIX "\"type\":\"snapshot\",\"seq\":2,\"total\":1,\"timers\":[{\"id\":\"bad\"}]}";
 assert(lcd_accept(&m,bad,100)==0);assert(m.sequence==1&&!strcmp(m.timers[0].id,"one"));
 const char *clear="{" PREFIX "\"type\":\"snapshot\",\"seq\":2,\"total\":0,\"timers\":[]}";
 assert(lcd_accept(&m,clear,200)==2);assert(m.count==0);
 assert(lcd_accept(&m,"{} garbage",300)==0);assert(lcd_accept(&m,"{",300)==0);
 assert(lcd_accept(&m,"[[[[[[[[[[]]]]]]]]]]",300)==0);assert(m.sequence==2);
 puts("LCD protocol: handshake, replay, timeout, reconnect, atomic validation, removal passed");
}
