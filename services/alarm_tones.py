"""Small synthesized alarm palette; fixed IDs, no paths/URLs from a tool."""
import array
import math
import sys
import wave

TONES={'bell':'Glocke','chime':'Klangspiel','pulse':'Sanfter Puls','silent':'Lautlos'}

def write_alarm(path, tone, seconds=3):
    if tone not in TONES or tone=='silent': raise ValueError('Kein abspielbarer Alarmton.')
    if seconds not in (3, 60): raise ValueError('Ungültige Alarmdauer.')
    rate=24000
    notes={'bell':[(0,660),(0.8,880),(1.6,660)],'chime':[(0,523.25),(.5,659.25),(1,783.99),(1.5,1046.5)],'pulse':[(0,440),(.8,440),(1.6,440)]}[tone]
    frames=array.array('h')
    for i in range(rate*3):
        t=i/rate; sample=0
        for start,freq in notes:
            elapsed=t-start
            if 0<=elapsed<.75:
                envelope=min(1,elapsed/.02)*math.exp(-5*elapsed)*min(1,(.75-elapsed)/.04)
                sample+=5000*envelope*math.sin(2*math.pi*freq*elapsed)
        value=round(sample);frames.extend((value,value))
    if sys.byteorder!='little':frames.byteswap()
    with wave.open(str(path),'wb') as output:
        output.setparams((2,2,rate,0,'NONE','not compressed'))
        cycle=frames.tobytes()
        output.writeframes(cycle if seconds==3 else (cycle+bytes(rate*4))*15)
