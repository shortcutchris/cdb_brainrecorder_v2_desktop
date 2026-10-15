#define _GNU_SOURCE
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdatomic.h>
#include <errno.h>
static void copy_ring(void *out, const unsigned char *data, uint64_t cap, uint64_t position, size_t n){
 size_t at=position%cap, first=cap-at;if(first>n)first=n;
 memcpy(out,data+at,first);if(n>first)memcpy((unsigned char*)out+first,data,n-first);
}
int main(int argc,char **argv){
 if(argc!=2)return 2;
 char *end;long target=strtol(argv[1],&end,10);if(*end||target<=0)return 2;
 struct perf_event_attr attr={0};attr.size=sizeof attr;attr.type=PERF_TYPE_SOFTWARE;attr.config=PERF_COUNT_SW_CPU_CLOCK;
 attr.sample_period=20000000;attr.sample_type=PERF_SAMPLE_IP|PERF_SAMPLE_TID|PERF_SAMPLE_CALLCHAIN;
 attr.disabled=1;attr.exclude_kernel=1;attr.exclude_hv=1;attr.exclude_callchain_kernel=1;attr.sample_max_stack=64;
 int fd=syscall(SYS_perf_event_open,&attr,(pid_t)target,-1,-1,PERF_FLAG_FD_CLOEXEC);if(fd<0){perror("perf_event_open");return 3;}
 size_t page=sysconf(_SC_PAGESIZE),length=page*65;void *area=mmap(NULL,length,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
 if(area==MAP_FAILED){perror("mmap");close(fd);return 4;}
 struct perf_event_mmap_page *meta=area;
 if(ioctl(fd,PERF_EVENT_IOC_RESET,0)||ioctl(fd,PERF_EVENT_IOC_ENABLE,0)){perror("enable");munmap(area,length);close(fd);return 5;}
 struct timespec delay={10,0};while(nanosleep(&delay,&delay)&&errno==EINTR){}
 if(ioctl(fd,PERF_EVENT_IOC_DISABLE,0)){perror("disable");munmap(area,length);close(fd);return 6;}
 uint64_t head=meta->data_head,tail=meta->data_tail;atomic_thread_fence(memory_order_acquire);
 uint64_t cap=meta->data_size,offset=meta->data_offset;int result=0;
 if(!cap||offset+cap>length||head<tail||head-tail>cap){fprintf(stderr,"Invalid or overrun sample ring\n");result=7;goto cleanup;}
 unsigned char *data=(unsigned char*)area+offset;uint64_t records[32]={0},lost=0;int comma=0;
 printf("{\"sample_period_ns\":20000000,\"ring_bytes\":%llu,\"record_bytes\":%llu,\"samples\":[",(unsigned long long)cap,(unsigned long long)(head-tail));
 while(tail<head){
  struct perf_event_header h;copy_ring(&h,data,cap,tail,sizeof h);
  if(h.size<sizeof h||h.size>head-tail){result=8;break;}
  unsigned char *record=malloc(h.size);if(!record){result=9;break;}copy_ring(record,data,cap,tail,h.size);
  if(h.type<32)records[h.type]++;
  if(h.type==PERF_RECORD_SAMPLE){
   if(h.size<32){free(record);result=10;break;}
   uint64_t ip,nr;uint32_t pid,tid;memcpy(&ip,record+8,8);memcpy(&pid,record+16,4);memcpy(&tid,record+20,4);memcpy(&nr,record+24,8);
   if(nr>(uint64_t)(h.size-32)/8||pid!=(uint32_t)target||tid!=(uint32_t)target){free(record);result=11;break;}
   printf("%s{\"ip\":%llu,\"pid\":%u,\"tid\":%u,\"chain\":[",comma?",":"",(unsigned long long)ip,pid,tid);comma=1;
   for(uint64_t i=0;i<nr;i++){uint64_t address;memcpy(&address,record+32+8*i,8);printf("%s%llu",i?",":"",(unsigned long long)address);}printf("]}");
  }else if(h.type==PERF_RECORD_LOST&&h.size>=24){uint64_t count;memcpy(&count,record+16,8);lost+=count;}
  free(record);tail+=h.size;
 }
 printf("],\"lost\":%llu,\"record_counts\":{",(unsigned long long)lost);comma=0;
 for(int i=0;i<32;i++)if(records[i]){printf("%s\"%d\":%llu",comma?",":"",i,(unsigned long long)records[i]);comma=1;}
 printf("},\"parse_error\":%d}\n",result);
cleanup:munmap(area,length);close(fd);return result;
}
