"""Readable views of immutable request/receipt pairs, including older hash-only receipts."""
import difflib


def request_for(history, index):
    receipt = history[index]
    if receipt.get('role') != 'tool': return None
    for previous in range(index-1, -1, -1):
        message = history[previous]
        if message.get('role') != 'assistant': continue
        calls = message.get('tool_calls') or []
        match = next((c for c in calls if c.get('id') and c.get('id') == receipt.get('provider_call_id')), None)
        if match is None:
            # Legacy fixtures have no provider IDs; pair repeated names in receipt order.
            same = [c for c in calls if c.get('name') == receipt.get('name')]
            used = sum(m.get('role') == 'tool' and m.get('name') == receipt.get('name') for m in history[previous+1:index])
            if used < len(same): match = same[used]
        return {'message':previous, 'call':match} if match is not None else None
    return None


def summary(history, index):
    request = request_for(history, index)
    if request is None: return None
    call, receipt = request['call'], history[index]
    args, result = call.get('arguments') or {}, receipt.get('result') or {}
    if not isinstance(args, dict) or not isinstance(result, dict): return None
    name = call.get('name')
    if name not in {'read_docs','read_file','write_file'}: return None
    view = {'name':name, 'path':args.get('path',result.get('path')), 'request_message':request['message'], 'error':result.get('error')}
    if name == 'write_file':
        view.update(characters=len(args['content']) if isinstance(args.get('content'),str) else None,
                    created=result.get('created'), saved=not bool(result.get('error')) and bool(result.get('sha256')))
    else:
        content = result.get('content')
        start = args.get('offset',0)
        view.update(offset=start, end_offset=start+len(content) if type(start) is int and isinstance(content,str) else None,
                    total_characters=result.get('total_characters'), returned_characters=len(content) if isinstance(content,str) else None,
                    truncated=result.get('truncated'), next_offset=result.get('next_offset'))
    return view


def inspect(history, index, writes):
    view = summary(history,index)
    if view is None: return None
    request = request_for(history,index)
    args, result = request['call'].get('arguments') or {}, history[index].get('result') or {}
    view.update(arguments=args, receipt=result)
    if view['name'] == 'write_file':
        before = next((w['content'] for w in reversed(writes) if w['message']<index and w['path']==view['path']),None)
        after = args.get('content')
        view.update(before=before, after=after, before_known=before is not None or view.get('created') is True)
        if isinstance(after,str):
            diff = difflib.unified_diff((before or '').splitlines(keepends=True),after.splitlines(keepends=True),
                                       fromfile='previous recorded/'+str(view['path']),tofile='written/'+str(view['path']))
            view['diff'] = ''.join(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n' for line in diff)
    else: view['content'] = result.get('content')
    return view
