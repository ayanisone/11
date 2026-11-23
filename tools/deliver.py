#!/usr/bin/env python3
"""Copy QC'd takes into music/motion_<lang>/ with verdict in the name.
usage: deliver.py <lang> <src.mp3>=<style>_<gender>:<PASS|REVIEW> ...
"""
import sys, shutil, os
lang = sys.argv[1]
out = f'music/motion_{lang}'
os.makedirs(out, exist_ok=True)
for spec in sys.argv[2:]:
    src, rest = spec.split('=')
    name, verdict = rest.split(':')
    assert verdict in ('PASS', 'REVIEW'), verdict
    dst = f'{out}/motion_{lang}_{name}_{verdict}.mp3'
    for f in os.listdir(out):           # drop older verdict for same take
        if f.startswith(f'motion_{lang}_{name}_') and f != os.path.basename(dst):
            os.remove(os.path.join(out, f))
    shutil.copy(src, dst); print('->', dst)
