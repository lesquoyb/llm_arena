"""Model-facing text views; provenance and original files remain in the archive."""
import copy
import json
import re

MESSAGE_METADATA={'arena_finalization','output_continuation','submission_reminder','trigger_model_call','completion_reason','provider_recovery'}

METADATA = {'sha256', 'commit', 'source_commit', 'generator_commit', 'engine_commit',
            'source_url', 'source_urls', 'sources', 'url', 'fetched_at', 'master_version',
            'provenance', 'artifact_dir', 'engine_identity'}


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def visible(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in METADATA or key.endswith('_sha256'): continue
            if key == 'files' and isinstance(item, dict) and all(isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) for v in item.values()):
                result[key] = sorted(name for name in item if name!='.arena-submission-error.json')
            else: result[key] = visible(item)
        return result
    if isinstance(value, list): return [visible(item) for item in value]
    return value


def documentation(path, text):
    if path.endswith('.json'):
        return compact(visible(json.loads(text)))
    if path.endswith('.leek'): return text
    pieces = re.split(r'(```[\s\S]*?```)', text)
    for index in range(0,len(pieces),2):
        part = pieces[index]
        part = re.sub(r'Resolve ambiguities against generator commit[\s\S]*?experimental session\.', '', part)
        part = re.sub(r'(?m)^Sources?:[^\n]*(?:\n(?!\n)[^\n]*)*', '', part)
        part = re.sub(r'\[([^\]]+)\]\(https?://[^)]+\)', r'\1', part)
        part = re.sub(r'https?://[^\s)]+', '', part)
        part = re.sub(r'(?<![A-Za-z0-9_])`?(?:[a-f0-9]{40}|[a-f0-9]{64})`?(?![A-Za-z0-9_])', '', part)
        pieces[index] = re.sub(r'\n{3,}', '\n\n', part)
    return ''.join(pieces)


def history_view(history):
    result = []
    for message in history:
        if message['role'] == 'tool':
            result.append({**message, 'result': visible(message['result'])})
        elif message['role'] == 'user':
            result.append(visible({key:value for key,value in message.items() if key not in MESSAGE_METADATA}))
        else: result.append(message)
    return result


def message_text(message):
    """Keep source/Markdown line breaks as text, rather than escaped JSON in JSON."""
    value = visible(message)
    for key in MESSAGE_METADATA:value.pop(key,None)
    if value.get('context_format')=='briefing-v1' and isinstance(value.get('scenario'),dict):
        from .user_briefing import render
        return render(value)
    content = value.pop('content', None)
    value.pop('role', None)
    return (content + ('\n' if value else '') if isinstance(content,str) else '') + (compact(value) if value else '')


def tool_text(result):
    value = visible(result)
    if isinstance(value,dict) and isinstance(value.get('content'),str):
        value = copy.copy(value)
        content = value.pop('content')
        return compact(value)+'\n'+content
    # configure_team already returns the parsed team; do not repeat its JSON file.
    if isinstance(value,dict) and 'team' in value: value.pop('content', None)
    return compact(value)


def character_page(arguments, default=16000):
    from .core import ArenaError
    offset, limit = arguments.get('offset', 0), arguments.get('limit', default)
    if type(offset) is not int or offset < 0:
        raise ArenaError('Invalid offset: use a non-negative integer character offset, preferably next_offset from the previous response')
    if type(limit) is not int or limit < 1:
        raise ArenaError('Invalid limit: use a positive integer character count; requests above 16000 are capped at 16000')
    return offset, min(limit, 16000)


def page(text, arguments, tool, identity, default=16000):
    offset, limit = character_page(arguments, default)
    end = min(len(text), offset+limit)
    following = end if end<len(text) else None
    return {**identity, 'offset':offset,'end_offset':max(offset,end),'total_characters':len(text),
            'content':text[offset:end], 'truncated':following is not None, 'next_offset':following,
            'reading_status':'partial: repeat continuation to read the remaining content' if following is not None else 'end_of_file',
            'continuation':{'tool':tool,'arguments':{**identity,'offset':following,'limit':limit}} if following is not None else None}
