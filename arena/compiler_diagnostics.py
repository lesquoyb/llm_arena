"""Decode pinned compiler diagnostics for display without changing archived results."""
import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).with_name('compiler_errors.json')).read_text(encoding='utf-8'))
MESSAGES = {33: 'Unknown variable or function', 35: 'Expected a value or expression',
            36: 'An instruction follows break in the same block', 40: 'Incorrect number of function arguments',
            93: 'Triple equals is deprecated', 124: 'Incompatible types'}


def compilation_rows(assessment, engine=None):
    rows = []
    engine_commit = (engine or {}).get('lock', {}).get('leekscript_commit')
    compatible = not engine_commit or engine_commit == CATALOG['leekscript_commit']
    def visit(result, entrypoint=None):
        if not isinstance(result, dict): return
        diagnostics = result.get('diagnostics') or []
        if not isinstance(diagnostics, list): return
        for value in diagnostics:
            if isinstance(value, list) and len(value) >= 7:
                severity, file, line, column, end_line, end_column, code = value[:7]
                if type(code) is not int: continue
                name = CATALOG['codes'].get(str(code)) if compatible else None
                parameters = value[7] if len(value)>7 and isinstance(value[7],list) else []
                label = MESSAGES.get(code) if compatible else None
                message = label or (name.replace('_', ' ').capitalize() if name else f'Compiler diagnostic {code}')
                if name in {'REMOVED_FUNCTION', 'REMOVED_FUNCTION_REPLACEMENT'} and len(parameters) >= 2:
                    message = f'Function is only available through LeekScript {parameters[0]}; this script uses LeekScript {parameters[1]}.'
                    if len(parameters) >= 3: message += f' Use {parameters[2]} instead.'
                elif parameters: message += ': '+', '.join(str(p) for p in parameters)
                rows.append({'severity':'error' if severity==0 else 'warning' if severity==1 else 'info',
                    'file':file,'line':line,'column':column,'end_line':end_line,'end_column':end_column,
                    'code':code,'name':name,'message':message,'parameters':parameters,'entrypoint':entrypoint})
            elif isinstance(value, dict):
                rows.append({'severity':value.get('severity','error'), 'file':value.get('file',entrypoint),
                             'line':value.get('line'), 'column':value.get('column'),
                             'code':value.get('code'), 'message':str(value.get('message',value))})
        for member, child in (result.get('member_analyses') or {}).items(): visit(child, member)
    visit(assessment)
    return rows


def readable_analysis(result, engine=None, source_root=None):
    rows = compilation_rows(result, engine)
    for row in rows:
        source = None
        if source_root is not None and isinstance(row.get('file'), str) and type(row.get('line')) is int:
            from .preparation import local_path
            from .core import ArenaError
            try:
                lines = local_path(source_root, row['file']).read_text(encoding='utf-8').splitlines()
                if 1 <= row['line'] <= len(lines):
                    source = lines[row['line']-1]
                    row['source_line'] = source
            except (OSError, ArenaError):
                pass
        if row.get('name') in {'REMOVED_FUNCTION', 'REMOVED_FUNCTION_REPLACEMENT'}:
            if source and 'getLeek(' in source.replace(' ', ''):
                row['hint'] = 'Replace getLeek() with getEntity() for the active runtime entity ID. getLeekID() is a persistent website ID and is not a substitute.'
    return {**result, 'diagnostic_messages': rows,
            'guide': 'Each diagnostic gives severity, file, line, column, message and the original compiler code. Errors prevent compilation; warnings do not necessarily prevent it. Fix errors and analyze the final saved sources again before submit. submit freezes files and ends preparation; it is not a compilation check.'}
