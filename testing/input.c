// Test-only virtual mouse, removed automatically when this process exits.
#include <linux/uinput.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static void event(int fd, int type, int code, int value) {
    struct input_event e = {.type=type, .code=code, .value=value};
    if (write(fd, &e, sizeof e) != sizeof e) { perror("input write"); exit(1); }
}
int main(void) {
    int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (fd < 0) { perror("/dev/uinput"); return 1; }
    ioctl(fd, UI_SET_EVBIT, EV_KEY);
    ioctl(fd, UI_SET_KEYBIT, BTN_LEFT);
    ioctl(fd, UI_SET_KEYBIT, BTN_MIDDLE);
    ioctl(fd, UI_SET_KEYBIT, BTN_RIGHT);
    int keys[]={KEY_LEFTMETA,KEY_LEFTSHIFT,KEY_LEFTALT,KEY_LEFTCTRL,KEY_LEFT,KEY_RIGHT,KEY_ESC};
    for(unsigned i=0;i<sizeof(keys)/sizeof(keys[0]);i++)ioctl(fd,UI_SET_KEYBIT,keys[i]);
    ioctl(fd, UI_SET_EVBIT, EV_REL);
    ioctl(fd, UI_SET_RELBIT, REL_X); ioctl(fd, UI_SET_RELBIT, REL_Y);
    ioctl(fd, UI_SET_RELBIT, REL_WHEEL);
    struct uinput_setup setup = {.id={BUS_USB,0x1234,0x5678,1}};
    snprintf(setup.name, UINPUT_MAX_NAME_SIZE, "COSMIC Window List Test Mouse");
    if (ioctl(fd, UI_DEV_SETUP, &setup)<0 || ioctl(fd, UI_DEV_CREATE)<0) { perror("create"); return 1; }
    usleep(600000);
    puts("ready"); fflush(stdout);
    char line[128];
    while (fgets(line,sizeof line,stdin)) {
        int a,b,c;
        if (sscanf(line,"rel %d %d",&a,&b)==2) {
            event(fd,EV_REL,REL_X,a);event(fd,EV_REL,REL_Y,b);event(fd,EV_SYN,SYN_REPORT,0);
        } else if (sscanf(line,"wheel %d",&a)==1) {
            event(fd,EV_REL,REL_WHEEL,a);event(fd,EV_SYN,SYN_REPORT,0);
        } else if (sscanf(line,"click %d",&c)==1) {
            int key = c==2 ? BTN_MIDDLE : c==3 ? BTN_RIGHT : BTN_LEFT;
            event(fd,EV_KEY,key,1);event(fd,EV_SYN,SYN_REPORT,0);usleep(50000);
            event(fd,EV_KEY,key,0);event(fd,EV_SYN,SYN_REPORT,0);
        } else if(sscanf(line,"key %d %d",&a,&b)==2){
            event(fd,EV_KEY,a,b);event(fd,EV_SYN,SYN_REPORT,0);
        }
        puts("ok");fflush(stdout);
    }
    ioctl(fd,UI_DEV_DESTROY);close(fd);
}
