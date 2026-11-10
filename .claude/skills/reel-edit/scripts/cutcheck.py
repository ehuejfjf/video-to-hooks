#!/usr/bin/env python3
"""Verify a render: loudness at every hard cut (should be < -30 dB) and a re-transcription diff.

Usage: python3 cutcheck.py <work_dir> <final.mp4>
"""
import difflib
import json
import os
import subprocess
import sys

import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel  # noqa: E402
work, out = sys.argv[1], sys.argv[2]
w=json.load(open(f'{work}/words.json')); e=json.load(open(f'{work}/render_edl.json'))
t,total=reel.timed_words(w['words'],e)
pcm=subprocess.run(["ffmpeg","-loglevel","error","-i",out,"-vn","-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout
a=np.frombuffer(pcm,np.float32)
db=lambda x:20*np.log10(np.sqrt(np.mean(x**2))+1e-9)
off=0; bad=0
for k,sg in enumerate(e['segments']):
  if k>0 and not sg.get('join_prev'):
    i=int(off*16000); b4=db(a[max(0,i-640):i]); af=db(a[i:i+640])
    flag = "  <-- LOUD" if max(b4,af) > -30 else ""
    bad += bool(flag)
    print(f"cut @{off:6.2f}s {b4:6.1f}/{af:6.1f} dB  ...{w['words'][e['segments'][k-1]['words'][1]]['w']} | {w['words'][sg['words'][0]]['w']}...{flag}")
  off+=sg['end']-sg['start']
from faster_whisper import WhisperModel
m=WhisperModel('small',device='cpu',compute_type='int8')
segs,_=m.transcribe(a,language='en',word_timestamps=True)
gw=[reel.norm(x.word) for s in segs for x in s.words]; exp=[reel.norm(x['w']) for x in t]
print(f"\n{bad} loud cuts. Word diffs:")
for op,i1,i2,j1,j2 in difflib.SequenceMatcher(a=exp,b=gw,autojunk=False).get_opcodes():
  if op!='equal': print(f"  {op:8} @{t[min(i1,len(t)-1)]['s']:6.2f}s expected {' '.join(exp[i1:i2])!r:30} heard {' '.join(gw[j1:j2])!r}")
