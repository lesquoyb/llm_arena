"""Stateless Responses protocol: replay only this conversation, including reasoning items."""
import json
from urllib.parse import urlsplit
from .core import ArenaError
from .model_content import history_view, message_text, tool_text


def uses_responses(model):
    if model.get('provider') not in {'openai', 'openai-compatible'}:
        return False
    path = urlsplit(model.get('endpoint') or 'https://api.openai.com/v1/chat/completions').path.rstrip('/')
    return path.endswith('/responses') or (path.endswith('/chat/completions') and
        model.get('model', '').lower().startswith('gpt-6') and model.get('parameters', {}).get('reasoning_effort') != 'none')


def endpoint(model, url):
    if not uses_responses(model): return url
    url = url.rstrip('/')
    return url[:-len('/chat/completions')] + '/responses' if url.endswith('/chat/completions') else url


def payload(model, history, tools, output_limit):
    items = []
    for message in history_view(history):
        role = message['role']
        if role in {'user', 'system'}:
            items.append({'role':role, 'content':message_text(message)})
        elif role == 'tool':
            items.append({'type':'function_call_output', 'call_id':message['provider_call_id'], 'output':tool_text(message['result'])})
        elif role == 'assistant':
            native = message['native']
            if 'responses_output' in native:
                items.extend(native['responses_output'])
            else:
                if native.get('content'):
                    items.append({'role':'assistant', 'content':native['content']})
                for call in native.get('tool_calls') or []:
                    items.append({'type':'function_call', 'call_id':call['id'], 'name':call['function']['name'], 'arguments':call['function']['arguments']})
        else:
            raise ArenaError('Unsupported Responses history role')
    parameters = dict(model.get('parameters', {}))
    effort = parameters.pop('reasoning_effort', None)
    # Responses does not expose seed. The omission is recorded as an adapter note.
    parameters.pop('seed', None)
    result = {'model':model['model'], 'input':items, 'store':False,
              'include':['reasoning.encrypted_content'], **parameters}
    if effort is not None: result['reasoning'] = {'effort':effort}
    if output_limit is not None: result['max_output_tokens'] = output_limit
    if tools:
        result['tools'] = [{'type':'function', 'name':tool['name'], 'description':tool['description'],
                            'parameters':tool['input_schema'], 'strict':False} for tool in tools]
    return result


def unpack(raw):
    output = raw['output']
    if not isinstance(output, list): raise ArenaError('Invalid Responses output')
    calls = []
    for item in output:
        if item.get('type') == 'function_call':
            try: arguments = json.loads(item['arguments'])
            except ValueError: arguments = None
            calls.append({'id':item['call_id'], 'name':item['name'], 'arguments':arguments})
    return {'role':'assistant', 'responses_output':output}, calls
