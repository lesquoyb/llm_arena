"""Refresh a frozen English language corpus from the public Leek Wars encyclopedia."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
# Titles match the English encyclopedia; API titles use spaces, not URL slugs.
PAGES = {
    'official-cheatsheet': ('LeekScript Cheat Sheet', None),
    'variables': ('Variables', '❓ Quiz'),
    'standard-functions': ('Standard functions', '❓ Quiz'),
    'conditions': ('Conditions', '❓ Quiz'),
    'booleans-null': ('Booleans and null', '❓ Quiz'),
    'operators': ('Operators', 'A smarter healing condition'),
    'strings': ('Strings', 'Greet your opponent'),
    'loops': ('Loops', 'Attacking several times in a row'),
    'lists-maps': ('Lists', 'Estimating a weapon'),
    'functions': ('Create your functions', 'Creating a `canFinish'),
    'objects-classes': ('Objects and Classes', None),
    'typing': ('Typing', None),
    'strict-mode': ('Strict mode', None),
    'version-4': ('LeekScript 4', None),
}
PATHS = {title: 'corpus/language/'+name+'.md' for name,(title,_) in PAGES.items()}
PATHS.update({'LeekScript':'corpus/language/index.md','Tutorial':'corpus/language/index.md'})


def clean(content, cutoff):
    text = content.replace('\r\n','\n').replace('\r','\n')
    if cutoff:
        match = re.search(r'^## '+re.escape(cutoff)+r'.*$',text,re.M)
        if not match: raise ValueError('Expected tutorial boundary is missing: '+cutoff)
        text = text[:match.start()]
    # Remove website navigation/widgets, keeping syntax and short teaching examples.
    parts = re.split(r'(```[\s\S]*?```)',text)
    for index in range(0,len(parts),2):
        part = re.sub(r'\{\{[^}]*\}\}', '', parts[index])
        part = re.sub(r'<img\b[^>]*>', '', part, flags=re.I)
        part = re.sub(r'</?(?:br|center|a|span|div)\b[^>]*>', '', part, flags=re.I)
        def link(match):
            target, _, label = match[1].partition('|')
            path = PATHS.get(target)
            return (label or target)+((' ('+path+')') if path else '')
        parts[index] = re.sub(r'\[\[([^\]]+)\]\]', link, part)
    return re.sub(r'\n{3,}','\n\n','\n'.join(line.rstrip() for line in ''.join(parts).splitlines())).strip()+'\n'


def import_pages(pages, destination, manifest):
    by_title={page['title']:page for page in pages}
    rendered={}; records=[]
    for name,(title,cutoff) in PAGES.items():
        page=by_title.get(title)
        if not page or page.get('language')!='en' or not isinstance(page.get('content'),str) or not page['content'].strip():
            raise ValueError('Missing English encyclopedia article: '+title)
        text=clean(page['content'],cutoff)
        note=''
        if name=='official-cheatsheet':
            note+='The original sheet uses placeholders (...). In Arena, include only files inside your submission. Registers do not persist across matches; editor pause/mark helpers are not required. Prefer cheatsheet.md for adapted, complete syntax examples.\n\n'
        if name=='strict-mode':
            note+='The online editor settings described below do not configure Arena; its pinned compiler settings apply.\n\n'
        text=note+text
        rendered[name+'.md']=text
        records.append({'path':'corpus/language/'+name+'.md', 'title':title,'page_id':page['id'],
            'source_url':'https://leekwars.com/encyclopedia/en/'+quote(title.replace(' ','_'),safe=''),
            'last_edition_time':page.get('last_edition_time'),'creator':page.get('creator_name'),
            'contributors':page.get('contributors',[]),'cut_before_heading':cutoff,
            'source_sha256':hashlib.sha256(page['content'].encode()).hexdigest(),
            'rendered_sha256':hashlib.sha256(text.encode()).hexdigest()})
    # Validate every article before replacing any file.
    destination.mkdir(parents=True,exist_ok=True)
    for name,text in rendered.items(): (destination/name).write_text(text,encoding='utf-8',newline='\n')
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps({'fetched_at':datetime.now(timezone.utc).isoformat(),
        'index_url':'https://leekwars.com/encyclopedia/fr/LeekScript',
        'transform':'English source; remove web widgets, quizzes and complete-AI/game-strategy sections at recorded headings; remap topic links; add Arena compatibility notes.',
        'pages':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return len(records)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,help='Offline JSON array of original encyclopedia API pages')
    parser.add_argument('--save-snapshot',type=Path,help='Save original API pages for auditing/reproduction')
    parser.add_argument('--out',type=Path,default=ROOT/'docs/corpus/language')
    parser.add_argument('--manifest',type=Path,default=ROOT/'docs/language-sources.json')
    args=parser.parse_args()
    try:
        if args.snapshot: pages=json.loads(args.snapshot.read_text(encoding='utf-8'))
        else:
            pages=[]
            for title,_ in PAGES.values():
                url='https://leekwars.com/api/encyclopedia/get/en/'+quote(title,safe='')
                with urlopen(Request(url,headers={'User-Agent':'LLMArena/1','Accept':'application/json'}),timeout=30) as response:
                    pages.append(json.load(response))
        count=import_pages(pages,args.out,args.manifest)
        if args.save_snapshot:
            args.save_snapshot.parent.mkdir(parents=True,exist_ok=True)
            args.save_snapshot.write_text(json.dumps(pages,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
        print(f'Imported {count} language reference chapters into {args.out}')
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(1,str(error)+'\n')
