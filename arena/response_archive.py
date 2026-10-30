"""Keep exact transport records once, outside frequently rewritten checkpoints."""
from .core import ArenaError, digest, write_json, file_hash, read_json


def compact(out, message):
    if not isinstance(message, dict) or message.get('role') != 'assistant':
        return message
    if 'raw' not in message and 'sent_parameters' not in message:
        return message
    artifact=out/'artifacts'/(digest(message)+'.json')
    if artifact.exists():
        if read_json(artifact)!=message:
            raise ArenaError('Archived model response changed')
    else:
        write_json(artifact,message)
    parameters=message.get('sent_parameters') or {}
    return {**{key:value for key,value in message.items() if key not in {'raw','sent_parameters'}},
            'request_summary':{key:parameters[key] for key in ('seed','reasoning_effort','reasoning','thinking','output_config','generationConfig') if key in parameters},
            'response_artifact':{'artifact':artifact.relative_to(out).as_posix(),'sha256':file_hash(artifact)}}
