"""Small, provider-independent progress notices for explicitly configured limits."""
from .usage import amount

COUNTERS = {'max_calls':'calls', 'max_agent_steps':'steps', 'max_test_matches':'test_matches',
            'max_wall_seconds':'wall_seconds', 'max_input_tokens':'input_tokens', 'max_output_tokens':'output_tokens'}
NOTICE = ('Limits apply to this preparation session. A test uses two matches. '
          'Input tokens count every request including repeated context and cached input; output includes reasoning when reported. '
          'On exhaustion Arena freezes the latest saved files automatically, even without submit and even if invalid. '
          'Save a complete strategy early and compile it before spending the remaining budget. '
          'A limit may prevent pending tools from running; submit can share the same response as other tool calls.')


def progress(state, budget):
    result = {}
    for limit, counter in COUNTERS.items():
        if limit not in budget: continue
        used = state.get(counter,0)
        if counter in {'input_tokens','output_tokens'} and state.get('calls') and not state.get('token_usage_known'):
            used = None
        result[counter] = {'limit':budget[limit], 'used':used, 'remaining':None if used is None else max(0,budget[limit]-used)}
    if 'max_cost_usd' in budget:
        used = amount(state.get('cost_spent','0'))
        result['cost_usd'] = {'limit':str(budget['max_cost_usd']), 'used':str(used),
                              'remaining':str(max(amount('0'),amount(budget['max_cost_usd'])-used))}
    return {'limits':result, 'on_exhaustion':'Latest saved files are frozen automatically; invalid code still fails evaluation.'} if result else None
