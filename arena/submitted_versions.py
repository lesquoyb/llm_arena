"""Read-only access to this trajectory's own frozen earlier source versions."""
import json
import sqlite3
from contextlib import closing
from .core import ArenaError, file_hash
from .preparation import local_path
from .model_content import page

NAMES = {'list_submissions', 'read_submitted_file'}


class OwnSubmissions:
    def __init__(self, out, state):
        self.out, self.state = out, state

    def versions(self):
        database = self.out/'journal.sqlite'
        if not database.exists(): return []
        seeds = list(self.state.get('calibration',{}).get('previous_sessions',[]))
        if self.state.get('parent'): seeds.append(self.state['parent'])
        result, seen = [], set()
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as db:
            while seeds:
                sid = seeds.pop()
                if sid in seen: continue
                seen.add(sid)
                row = db.execute("SELECT json_extract(state,'$.model'),json_extract(state,'$.replicate'),json_extract(state,'$.generation'),json_extract(state,'$.parent'),json_extract(state,'$.submission') FROM sessions WHERE id=?",(sid,)).fetchone()
                if not row: continue
                model, replicate, generation, parent, info = row
                if model != self.state['model'] or replicate != self.state['replicate'] or generation >= self.state['generation']:
                    raise ArenaError('Source version is outside this trajectory')
                if parent: seeds.append(parent)
                if info: result.append({'round':generation+1,'session':sid,'submission':json.loads(info)})
        return sorted(result,key=lambda r:r['round'])

    def call(self, name, arguments):
        if name == 'list_submissions':
            if set(arguments)-{'offset','limit'}: raise ArenaError('Unknown version-list arguments')
            offset, limit = arguments.get('offset',0), arguments.get('limit',20)
            if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:
                raise ArenaError('Invalid version page')
            rows=self.versions(); selected=rows[offset:offset+limit]
            return {'scope':'Your own submitted code from earlier rounds of this track; no fight results.',
                    'submissions':[{'round':r['round'],'entrypoint':r['submission']['entrypoint'],'files':sorted(r['submission']['files'])} for r in selected],
                    'next_offset':offset+limit if offset+limit<len(rows) else None}
        if set(arguments)-{'round','path','offset','limit'}: raise ArenaError('Unknown source-version arguments')
        number=arguments.get('round')
        if type(number) is not int or number<1: raise ArenaError('round must be a positive strategy-round number')
        row=next((r for r in self.versions() if r['round']==number),None)
        if not row: raise ArenaError('That round is not an earlier submission of this track')
        path=arguments.get('path'); expected=row['submission']['files'].get(path)
        if not expected: raise ArenaError('File not present in that submission')
        source=local_path(self.out/'sessions'/row['session']/'submission',path)
        if file_hash(source)!=expected: raise ArenaError('Archived source version changed')
        return page(source.read_text(encoding='utf-8'),arguments,name,{'round':number,'path':path})
