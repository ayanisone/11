import re,sys
BASE={'hi':0x900,'bn':0x980,'as':0x980,'pa':0xA00,'gu':0xA80,'or':0xB00,'ta':0xB80,'te':0xC00,'kn':0xC80,'ml':0xD00}
DROP_FINAL={'hi','bn','as','pa','gu'}
def wsyl(w,lang):
    B=BASE[lang]; cs=[ord(c)-B for c in w if B<=ord(c)<B+0x80]; n=0
    for i,o in enumerate(cs):
        if 0x05<=o<=0x14 or o in (0x60,0x61): n+=1
        elif 0x3E<=o<=0x4C: n+=1
        elif (0x15<=o<=0x39) or (0x58<=o<=0x5F) or (lang=='pa' and o in (0x72,0x73)) or (lang!='pa' and o in (0x70,0x71)):
            j=i+1
            while j<len(cs) and (cs[j] in (0x3C,0x01,0x02,0x03) or (lang=='pa' and cs[j] in (0x70,0x71))): j+=1
            nx=cs[j] if j<len(cs) else None
            if nx==0x4D or (nx is not None and 0x3E<=nx<=0x4C): continue
            if nx is None and lang in DROP_FINAL and i>0: continue
            n+=1
    return n
def syl(l,lang): return sum(wsyl(w,lang) for w in re.findall(r'\S+',l))
if __name__=='__main__':
    lang=sys.argv[2]; tot=0;sec=None;s=0
    for line in open(sys.argv[1],encoding='utf-8'):
        line=line.strip()
        if line.startswith('['):
            if sec: print(sec,s)
            sec=line;s=0;continue
        x=syl(line,lang);s+=x;tot+=x
    print(sec,s);print('TOTAL',tot)
