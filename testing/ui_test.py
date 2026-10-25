#!/usr/bin/env python3
"""Real mouse tests against the installed panel, checked via compositor state."""
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
results=[]
mouse=subprocess.Popen([str(ROOT/'input')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
assert mouse.stdout.readline().strip()=='ready'
time.sleep(1)

def send(command):
    mouse.stdin.write(command+'\n');mouse.stdin.flush()
    assert mouse.stdout.readline().strip()=='ok'

def move(x,y):
    (ROOT/'pointer-hide').unlink(missing_ok=True)
    (ROOT/'pointer.json').unlink(missing_ok=True)
    overlay=subprocess.Popen(['/usr/bin/python3',str(ROOT/'pointer_probe.py')])
    try:
        time.sleep(.5)
        for _ in range(15):
            send('rel 2 2');time.sleep(.1)
            if (ROOT/'pointer.json').exists():break
        assert (ROOT/'pointer.json').exists(),'No pointer feedback'
        for _ in range(160):
            pos=json.loads((ROOT/'pointer.json').read_text())
            dx=x-pos['x'];dy=y-pos['y']
            if abs(dx)<2 and abs(dy)<2:break
            sx=round(max(-50,min(50,dx)));sy=round(max(-50,min(50,dy)))
            send(f'rel {sx} {sy}');time.sleep(.055)
        else:raise AssertionError(f'Could not reach {x},{y}: {pos}')
    finally:
        (ROOT/'pointer-hide').touch();overlay.wait(timeout=5)
    time.sleep(.8)
    send('rel 1 0')
    time.sleep(.1)

def states():
    data=subprocess.check_output([str(ROOT/'probe')],text=True)
    found={}
    for line in data.splitlines():
        active,minimized,appid,title=line.split('\t',3)
        if title.startswith('Window List Test'):
            found[title]={'active':active=='1','minimized':minimized=='1','app':appid}
    return found

def click(x,y,button=1):
    move(x,y);send(f'click {button}');time.sleep(.45)

def record(name,condition):
    assert condition,name
    results.append({'test':name,'passed':True,'windows':states()})
    print('PASS',name,flush=True)

def main():
    try:
        initial=states()
        record('three windows from same application',len(initial)==3 and len({v['app'] for v in initial.values()})==1)
        click(2420,1050)
        record('Alpha button focuses Alpha',states()['Window List Test — Alpha']['active'])
        click(2420,1050)
        record('active Alpha button minimizes Alpha',states()['Window List Test — Alpha']['minimized'])
        click(2420,1050)
        record('Alpha button restores Alpha',states()['Window List Test — Alpha']['active'] and not states()['Window List Test — Alpha']['minimized'])
        click(2570,1050)
        record('Bravo button focuses Bravo',states()['Window List Test — Bravo']['active'])
        click(2720,1050)
        record('Charlie button focuses Charlie',states()['Window List Test — Charlie']['active'])
        subprocess.run(['cosmic-screenshot','--interactive=false','--notify=false','--save-dir',str(PROJECT/'screenshots')],check=True)
        click(2720,1050,2)
        record('middle-click closes only Charlie',set(states())=={'Window List Test — Alpha','Window List Test — Bravo'})
    finally:
        mouse.stdin.close();mouse.wait(timeout=5)
        (PROJECT/'test-results.json').write_text(json.dumps(results,indent=2))

if __name__ == "__main__":
    main()
