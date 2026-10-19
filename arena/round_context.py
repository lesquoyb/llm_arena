"""Small phase context; earlier source contents and replays stay pull-based."""

def phase(round_number, maximum):
    return (f'You are preparing Round {round_number} of {maximum}.' if maximum is not None
            else f'You are preparing Round {round_number}; rounds continue until manually stopped.')


def source_context(version, tools=None):
    info = version['submission']
    number = version['round']
    result = {'round':number, 'entrypoint':info['entrypoint'], 'files':sorted(info['files']),
            'workspace':'These exact submitted files were copied into your workspace. Read them before editing; do not replace them with a stub.',
            'read_workspace':{'tool':'read_file','arguments':{'path':info['entrypoint']}},
            'read_frozen':{'tool':'read_submitted_file','arguments':{'round':number,'path':info['entrypoint']}}}
    if tools is not None:
        if 'read_file' not in tools: result.pop('read_workspace')
        if 'read_submitted_file' not in tools: result.pop('read_frozen')
    return result


def progress_line(number, counts):
    scored = counts['wins'] + counts['draws'] + counts['losses']
    score = f", score {(counts['wins'] + .5*counts['draws'])/scored:.1%}" if scored else ', no scored fights'
    return (f"Round {number}: {counts['wins']} wins, {counts['draws']} draws, {counts['losses']} losses"
            f", {counts.get('failures',0)} unscored failures{score}.")
