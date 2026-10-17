"""Lossless inspection of received provider output; no inference about hidden activity."""
import json


def _size(value):
    return len(value) if isinstance(value, str) else len(json.dumps(value, ensure_ascii=False))


def _readable(value):
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, list):
        return any(_readable(item) for item in value)
    if isinstance(value, dict):
        return any(_readable(value[key]) for key in ('text', 'thinking', 'reasoning_content', 'summary') if key in value)
    return False


def blocks(message):
    """Return ordered inspectable blocks. Values are fetched only when expanded."""
    result = []
    def add(kind, label, value):
        if value is None:
            return
        result.append({'kind': kind, 'label': label, 'characters': _size(value), 'readable': kind == 'reasoning' and _readable(value), 'value': value})
    if message.get('role') == 'tool':
        value = message.get('result')
        summary = 'Result'
        if isinstance(value, dict):
            if value.get('error'): summary = 'Error: ' + str(value['error'])[:120]
            elif value.get('valid') is False: summary = 'Validation failed'
            elif value.get('status'): summary = str(value['status'])
            elif value.get('valid') is True: summary = 'Valid'
            elif 'submission' in value: summary = 'Submitted'
            elif isinstance(value.get('files'), list): summary = str(len(value['files'])) + ' files'
            elif isinstance(value.get('matches'), list): summary = str(len(value['matches'])) + ' fights'
            elif isinstance(value.get('content'), str): summary = str(len(value['content'])) + ' characters'
            elif 'sha256' in value: summary = 'File saved'
        add('tool_result', f"{message.get('name', 'Tool')} · {summary}", value)
        return result
    native = message.get('native') or {}
    if not isinstance(native, dict):
        native = {}
    reasoning_keys = {'reasoning', 'reasoning_content', 'reasoning_details', 'thinking', 'analysis'}
    for key, value in native.items():
        if key in reasoning_keys:
            add('reasoning', ('Provider-exposed reasoning' if isinstance(value,str) else 'Reasoning data') + ' · ' + key, value)
    content = native.get('content')
    if isinstance(content, str):
        add('text', 'Answer text', content)
    elif isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                add('other', 'Provider content block', part)
                continue
            kind = str(part.get('type', 'unknown'))
            if kind == 'text': add('text', 'Answer text', part)
            elif kind in {'thinking', 'reasoning', 'reasoning_summary'}: add('reasoning', 'Provider-exposed reasoning', part)
            elif kind in {'redacted_thinking', 'encrypted_reasoning'}: add('opaque', 'Redacted or encrypted reasoning (not readable)', part)
            elif kind == 'tool_use': add('tool_call', 'Arena tool request · ' + str(part.get('name', 'unknown')), part)
            elif 'tool' in kind or kind in {'web_search_result', 'code_execution_result'}:
                add('provider_tool', f"Provider-reported tool activity · {part.get('name') or kind}", part)
            else: add('other', 'Provider block · ' + kind, part)
    for part in native.get('parts') or []:
        if not isinstance(part, dict):
            add('other', 'Provider part', part)
        elif part.get('thought') and 'text' in part:
            add('reasoning', 'Provider-exposed reasoning', part)
        elif 'functionCall' in part:
            add('tool_call', 'Arena tool request · ' + str(part['functionCall'].get('name', 'unknown')), part)
        elif any(key in part for key in ('functionResponse', 'executableCode', 'codeExecutionResult', 'toolCall', 'toolResponse')):
            add('provider_tool', 'Provider-reported tool activity · ' + ', '.join(part), part)
        elif 'text' in part:
            add('text', 'Answer text', part)
        elif 'thoughtSignature' in part:
            add('opaque', 'Opaque thought signature (not readable)', part)
        else:
            add('other', 'Provider part · ' + ', '.join(part), part)
    for call in native.get('tool_calls') or []:
        name = (call.get('function') or {}).get('name', call.get('type', 'unknown'))
        add('tool_call', 'Arena tool request · ' + str(name), call)
    for key, value in native.items():
        if key in {'role', 'content', 'parts', 'tool_calls'} | reasoning_keys:
            continue
        kind = 'reasoning' if key in {'reasoning', 'reasoning_content', 'reasoning_details', 'thinking', 'analysis'} else 'other'
        if key in {'thought_signature', 'thoughtSignature', 'encrypted_content'}: kind = 'opaque'
        add(kind, (('Provider-exposed reasoning' if isinstance(value, str) else 'Reasoning data') if kind == 'reasoning' else 'Additional provider output') + ' · ' + key, value)
    if not native:
        if message.get('content'): add('text', 'Answer text', message['content'])
        for call in message.get('tool_calls') or []:
            add('tool_call', 'Arena tool request · ' + str(call.get('name', 'unknown')), call)
    raw = message.get('raw')
    if raw is not None:
        if isinstance(raw, dict):
            for key in ('choices', 'candidates'):
                for i, alternative in enumerate(raw.get(key) or []):
                    if i > 0: add('alternative', f'Alternative response {i + 1}', alternative)
        if isinstance(raw, dict):
            for key, value in raw.items():
                if any(word in key.lower() for word in ('mcp', 'tool')):
                    add('provider_tool', 'Provider-reported field · ' + key, value)
        add('raw', 'Complete provider response', raw)
    return result


def preview(message):
    """Small conversation listing; exact native response and request stay immutable."""
    native = message.get('native') or {}
    if not isinstance(native, dict):
        native = {}
    content = native.get('content')
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = '\n'.join(p.get('text', '') for p in content if isinstance(p, dict) and p.get('type') == 'text' and isinstance(p.get('text'), str))
    elif native.get('parts'):
        text = '\n'.join(p.get('text', '') for p in native['parts'] if isinstance(p, dict) and not p.get('thought') and isinstance(p.get('text'), str))
    else:
        text = message.get('content') or ''
    return {'output_text': text[:1800], 'output_text_truncated': len(text) > 1800,
            'output_blocks': [{k:v for k,v in block.items() if k != 'value'} | {'index': i}
                              for i,block in enumerate(blocks(message))]}
