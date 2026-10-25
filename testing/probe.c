// Test-only observer of real compositor window states (protocol version 1).
#include <wayland-client.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "toplevel-info.h"

// These interfaces are referenced by newer protocol versions, not bound here.
const struct wl_interface ext_foreign_toplevel_handle_v1_interface={"ext_foreign_toplevel_handle_v1",1,0,NULL,0,NULL};
const struct wl_interface ext_workspace_handle_v1_interface={"ext_workspace_handle_v1",1,0,NULL,0,NULL};
const struct wl_interface zcosmic_workspace_handle_v1_interface={"zcosmic_workspace_handle_v1",1,0,NULL,0,NULL};
struct entry {char title[4096], app[512];int active,minimized,closed;struct wl_output *outputs[16];int output_count;};
struct output_entry {struct wl_output *object;char name[256];};
static struct output_entry outputs[16];static int output_count;
static struct entry entries[512];static int count=0;
static void closed(void *d,struct zcosmic_toplevel_handle_v1 *h){((struct entry*)d)->closed=1;}
static void done(void *d,struct zcosmic_toplevel_handle_v1 *h){}
static void title(void *d,struct zcosmic_toplevel_handle_v1 *h,const char *s){snprintf(((struct entry*)d)->title,4096,"%s",s);}
static void appid(void *d,struct zcosmic_toplevel_handle_v1 *h,const char *s){snprintf(((struct entry*)d)->app,512,"%s",s);}
static void output(void *d,struct zcosmic_toplevel_handle_v1 *h,struct wl_output *o){
    struct entry *e=d;if(e->output_count<16)e->outputs[e->output_count++]=o;
}
static void output_leave(void *d,struct zcosmic_toplevel_handle_v1 *h,struct wl_output *o){
    struct entry *e=d;for(int i=0;i<e->output_count;i++)if(e->outputs[i]==o){e->outputs[i]=e->outputs[--e->output_count];break;}
}
static void workspace(void *d,struct zcosmic_toplevel_handle_v1 *h,struct zcosmic_workspace_handle_v1 *w){}
static void state(void *d,struct zcosmic_toplevel_handle_v1 *h,struct wl_array *a){
    struct entry *e=d;e->active=e->minimized=0;uint32_t *s;
    wl_array_for_each(s,a){if(*s==2)e->active=1;if(*s==1)e->minimized=1;}
}
static const struct zcosmic_toplevel_handle_v1_listener handler={
    .closed=closed,.done=done,.title=title,.app_id=appid,.output_enter=output,.output_leave=output_leave,
    .workspace_enter=workspace,.workspace_leave=workspace,.state=state
};
static void toplevel(void *d,struct zcosmic_toplevel_info_v1 *m,struct zcosmic_toplevel_handle_v1 *h){
    if(count>=512)abort();zcosmic_toplevel_handle_v1_add_listener(h,&handler,&entries[count++]);
}
static void finished(void*d,struct zcosmic_toplevel_info_v1*m){}
static void all_done(void*d,struct zcosmic_toplevel_info_v1*m){}
static const struct zcosmic_toplevel_info_v1_listener manager={.toplevel=toplevel,.finished=finished,.done=all_done};
static int bound=0;static uint32_t info_global;
static void output_geometry(void*d,struct wl_output*o,int32_t x,int32_t y,int32_t w,int32_t h,int32_t s,const char*m,const char*n,int32_t t){}
static void output_mode(void*d,struct wl_output*o,uint32_t f,int32_t w,int32_t h,int32_t r){}
static void output_done(void*d,struct wl_output*o){}
static void output_scale(void*d,struct wl_output*o,int32_t s){}
static void output_name(void*d,struct wl_output*o,const char*s){snprintf(((struct output_entry*)d)->name,256,"%s",s);}
static void output_description(void*d,struct wl_output*o,const char*s){}
static const struct wl_output_listener output_listener={.geometry=output_geometry,.mode=output_mode,.done=output_done,.scale=output_scale,.name=output_name,.description=output_description};
static void global(void *d,struct wl_registry *r,uint32_t n,const char *i,uint32_t v){
    if(!strcmp(i,"wl_output")&&output_count<16){
        struct output_entry *out=&outputs[output_count++];out->object=wl_registry_bind(r,n,&wl_output_interface,v<4?v:4);
        wl_output_add_listener(out->object,&output_listener,out);
    }
    if(!strcmp(i,"zcosmic_toplevel_info_v1")){
        info_global=n;bound=1;
    }
}
static void removed(void*d,struct wl_registry*r,uint32_t n){}
static const struct wl_registry_listener registry={.global=global,.global_remove=removed};
int main(int argc,char**argv){
    struct wl_display *d=wl_display_connect(NULL);if(!d){perror("Wayland connect");return 1;}
    struct wl_registry *r=wl_display_get_registry(d);wl_registry_add_listener(r,&registry,NULL);
    if(wl_display_roundtrip(d)<0||wl_display_roundtrip(d)<0)return 2;
    if(!bound){fprintf(stderr,"No COSMIC toplevel-info protocol\n");return 3;}
    struct zcosmic_toplevel_info_v1 *m=wl_registry_bind(r,info_global,&zcosmic_toplevel_info_v1_interface,1);
    zcosmic_toplevel_info_v1_add_listener(m,&manager,NULL);
    if(wl_display_roundtrip(d)<0||wl_display_roundtrip(d)<0)return 2;
    for(int i=0;i<count;i++)if(!entries[i].closed){
        printf("%d\t%d\t%s\t%s",entries[i].active,entries[i].minimized,entries[i].app,entries[i].title);
        if(argc>1){
            printf("\t");
            for(int j=0;j<entries[i].output_count;j++)for(int k=0;k<output_count;k++)
                if(entries[i].outputs[j]==outputs[k].object)printf("%s%s",j?",":"",outputs[k].name);
        }
        printf("\n");
    }
    wl_display_disconnect(d);
}
