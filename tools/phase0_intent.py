"""Bounded local intent scorer for public Phase 0 commands; never executes actions."""
import re

def intent(text):
    value=' '.join(re.findall(r'[a-z0-9]+',text.lower())).replace('note pad','notepad').replace('you tube','youtube')
    if re.search(r'\b(not|never|delete|ignore|except)\b',value): return None
    for words,number in [('one hundred','100'),('forty','40'),('fifteen','15'),('fifty','50')]: value=value.replace(words,number)
    if 'volume' in value:
        numbers=re.findall(r'\b\d+\b',value)
        if len(numbers)==1 and 0<=int(numbers[0])<=100:return 'audio.set_volume',int(numbers[0])
        return None
    if 'unmute' in value or 'un mute' in value:return 'audio.set_mute',False
    if re.search(r'\bmute\b',value):return 'audio.set_mute',True
    if re.search(r'\b(open|launch|start|bring|show|take|visit)\b',value):
        for target in ('notepad','calculator'):
            if target in value:return 'app.open',target
        for target in ('documents','downloads'):
            if target in value:return 'folder.open',target
        for target in ('wikipedia','youtube'):
            if target in value:return 'website.open',target
    if 'study' in value and ('routine' in value or 'start' in value):return 'routine.run','study'
    if re.search(r'\b(screenshot|screenshots|capture)\b|screen shot',value):
        return 'screen.capture','all' if re.search(r'\ball\b',value) else 'primary'
    if re.search(r'\b(music|song|track|pause|resume)\b',value):
        if re.search(r'\b(previous|back)\b',value):return 'media.control','previous'
        if re.search(r'\b(next|skip)\b',value):return 'media.control','next'
        if re.search(r'\b(pause|resume)\b',value):return 'media.control','play_pause'
    return None

EXPECTED=[('app.open','notepad'),('app.open','calculator'),('folder.open','documents'),
('folder.open','downloads'),('website.open','wikipedia'),('website.open','youtube'),
('audio.set_volume',40),('audio.set_volume',15),('audio.set_volume',100),
('audio.set_mute',True),('audio.set_mute',False),('media.control','play_pause'),
('media.control','next'),('media.control','previous'),('screen.capture','primary'),
('screen.capture','all'),('routine.run','study'),('app.open','notepad'),
('folder.open','downloads'),('audio.set_volume',50)]
