"""Analyst recommendations are reviewable reports, never executable tools."""
from .core import ArenaError, write_json


def validate(requests):
    if not isinstance(requests,list) or len(requests)>20:
        raise ArenaError('tool_requests must be an array of at most 20 recommendations')
    for request in requests:
        if (not isinstance(request,dict) or not {'kind','problem','proposed_change'} <= set(request)
                or set(request)-{'kind','tool','problem','proposed_change','evidence','expected_benefit'}):
            raise ArenaError('Each tool request needs kind, problem and proposed_change; optional tool, evidence and expected_benefit')
        if request['kind'] not in {'new_tool','tool_change','documentation','error_feedback'}:
            raise ArenaError('Unknown tool request kind')
        for key in ('tool','problem','proposed_change','expected_benefit'):
            if key in request and (not isinstance(request[key],str) or len(request[key])>12000):
                raise ArenaError('Tool request fields must be strings of at most 12000 characters')
        evidence=request.get('evidence',[])
        if not isinstance(evidence,list) or len(evidence)>20 or any(not isinstance(v,str) or len(v)>2000 for v in evidence):
            raise ArenaError('Tool request evidence must contain at most 20 short strings')
    return requests


def write_report(directory, requests):
    validate(requests)
    write_json(directory/'tool-requests.json',requests)
    lines=['# Tool improvement recommendations', '', 'These recommendations were not executed or installed.', '']
    for index,r in enumerate(requests,1):
        lines += [f"## {index}. {r['kind']}: {r.get('tool') or 'Arena tools'}", '',
                  '**Problem**: '+r['problem'], '', '**Proposed change**: '+r['proposed_change'], '']
        if r.get('expected_benefit'): lines += ['**Expected benefit**: '+r['expected_benefit'],'']
        if r.get('evidence'): lines += ['**Training evidence**:', *['- '+v for v in r['evidence']], '']
    if not requests: lines += ['No tool changes requested.','']
    (directory/'tool-requests.md').write_text('\n'.join(lines),encoding='utf-8')
