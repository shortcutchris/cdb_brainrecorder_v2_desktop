#include "protocol.h"
#include "cJSON.h"
#include <string.h>
#include <math.h>
static cJSON *field(cJSON *o,const char *k){return cJSON_GetObjectItemCaseSensitive(o,k);}
static bool text(cJSON *o,const char *k,char *out,size_t size){
 cJSON *v=field(o,k);if(!cJSON_IsString(v)||!v->valuestring||strlen(v->valuestring)>=size)return false;
 for(const unsigned char *p=(const unsigned char *)v->valuestring;*p;p++)if(*p<32||*p==127)return false;
 strcpy(out,v->valuestring);return true;
}
static bool integer(cJSON *o,const char *k,double min,double max,int64_t *out){
 cJSON *v=field(o,k);if(!cJSON_IsNumber(v)||!isfinite(v->valuedouble)||v->valuedouble<min||v->valuedouble>max||floor(v->valuedouble)!=v->valuedouble)return false;
 *out=(int64_t)v->valuedouble;return true;
}
static bool hex32(const char *v){if(strlen(v)!=32)return false;for(int i=0;i<32;i++)if(!((v[i]>='0'&&v[i]<='9')||(v[i]>='a'&&v[i]<='f')))return false;return true;}
void lcd_reset(lcd_model *m,const char *nonce){memset(m,0,sizeof(*m));strncpy(m->nonce,nonce,32);}
int lcd_accept(lcd_model *m,const char *json,int64_t now){
 if(strlen(json)>=LCD_FRAME_SIZE)return 0;
 // Bound cJSON recursion before parsing untrusted serial input.
 int depth=0;bool quoted=false,escaped=false;
 for(const char *p=json;*p;p++){
  if(quoted){if(escaped)escaped=false;else if(*p=='\\')escaped=true;else if(*p=='"')quoted=false;}
  else if(*p=='"')quoted=true;
  else if(*p=='{'||*p=='['){if(++depth>8)return 0;}
  else if(*p=='}'||*p==']'){if(--depth<0)return 0;}
 }
 if(depth||quoted)return 0;
 cJSON *root=cJSON_ParseWithOpts(json,NULL,true);if(!root)return 0;
 char protocol[16],type[16],nonce[33],session[33];int result=0;
 if(!text(root,"protocol",protocol,sizeof(protocol))||strcmp(protocol,LCD_PROTOCOL)||
    !text(root,"type",type,sizeof(type))||!text(root,"nonce",nonce,sizeof(nonce))||strcmp(nonce,m->nonce)||
    !text(root,"session",session,sizeof(session))||!hex32(session))goto done;
 if(!strcmp(type,"bind")){
  // Active ownership can only change after link expiry and a new device nonce.
  if(m->bound&&strcmp(session,m->session))goto done;
  if(!text(root,"source",m->source,sizeof(m->source)))goto done;
  if(!m->bound){strcpy(m->session,session);m->bound=true;m->received_ms=now;}
  result=1;goto done;
 }
 if(strcmp(type,"snapshot")||!m->bound||strcmp(session,m->session))goto done;
 int64_t seq,total;
 if(!integer(root,"seq",1,2147483647,&seq)||seq<=m->sequence||!integer(root,"total",0,100,&total))goto done;
 cJSON *items=field(root,"timers");if(!cJSON_IsArray(items))goto done;
 int count=cJSON_GetArraySize(items);if(count>LCD_MAX_TIMERS||total<count)goto done;
 // Parse transactionally: a malformed last item must not partially replace valid state.
 lcd_timer candidate[LCD_MAX_TIMERS]={0};
 for(int i=0;i<count;i++){
  cJSON *item=cJSON_GetArrayItem(items,i);lcd_timer *t=&candidate[i];int64_t revision;
  if(!text(item,"id",t->id,sizeof(t->id))||!t->id[0]||!text(item,"label",t->label,sizeof(t->label))||
     !text(item,"state",t->state,sizeof(t->state))||
     (strcmp(t->state,"scheduled")&&strcmp(t->state,"due")&&strcmp(t->state,"missed"))||
     !integer(item,"revision",1,2147483647,&revision)||!integer(item,"remaining_ms",0,31622400000LL,&t->remaining_ms)||
     !cJSON_IsBool(field(item,"time_valid")))goto done;
  t->revision=(int)revision;t->time_valid=cJSON_IsTrue(field(item,"time_valid"));
  for(int j=0;j<i;j++)if(!strcmp(candidate[j].id,t->id))goto done;
 }
 memcpy(m->timers,candidate,sizeof(candidate));m->count=count;m->total=(int)total;m->sequence=(uint32_t)seq;m->received_ms=now;m->fresh=true;result=2;
 done:cJSON_Delete(root);return result;
}
bool lcd_expired(const lcd_model *m,int64_t now){return m->bound&&(now<m->received_ms||now-m->received_ms>=3000);}
int64_t lcd_remaining(const lcd_model *m,int index,int64_t now){
 if(!m->fresh||lcd_expired(m,now)||index<0||index>=m->count||!m->timers[index].time_valid)return -1;
 const lcd_timer *t=&m->timers[index];int64_t left=t->remaining_ms;
 if(!strcmp(t->state,"scheduled"))left-=now-m->received_ms;
 return left>0?left:0;
}
