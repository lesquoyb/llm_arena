"""Submission reminders require an explicit, completed model turn."""


def completed_turn(response):
    reason=str(response.get('stop_reason') or response.get('finish_reason') or '').lower()
    return reason in {'stop','end_turn','completed','stop_sequence','end'}


def restore_interrupted_streak(state):
    """Repair an outstanding reset marker written by the previous implementation."""
    previous=state.pop('interrupted_stop_streak',None)
    if type(previous) is int and previous>0 and state.get('consecutive_submission_reminders',0)==0:
        state['consecutive_submission_reminders']=previous
        return {'previous':0,'restored':previous,'reason':'incorrect_reset_during_provider_interruption'}
    return None


def interrupted_response(state, response):
    """Keep the received output and usage without treating truncation as a stop."""
    import time
    reason=response.get('stop_reason') or response.get('finish_reason')
    state.update(status='provider_unavailable',pending=None,cursor=0,in_flight=False)
    state['failure']={'message':
        'The provider response did not confirm a completed model turn '
        f'(finish reason: {reason if reason is not None else "missing"}). '
        'The response and its reported usage are saved. Retry continues the same preparation session; '
        'this interruption does not count toward submission reminders.',
        'phase':'provider response','retryable':True,'uncertain':False,'at':time.time(),
        'incomplete_response':True,'stop_reason':reason}
    return {'error':state['failure']['message'],'retryable':True,'uncertain':False,'stop_reason':reason}


def output_limited(response):
    reason=str(response.get('stop_reason') or response.get('finish_reason') or '').lower()
    return reason in {'length','max_tokens','max_output_tokens'}


def continue_output(state, response):
    """Continue a received, charged output in the same history, without a failure."""
    reason=response.get('stop_reason') or response.get('finish_reason')
    state.update(status='running',pending=None,cursor=0)
    state['history'].append({'role':'user','output_continuation':True,'completion_reason':reason,
        'content':'Your previous response reached its output token limit. Continue from where it was cut off, using the preceding response and the current workspace. '
                  'Continue preparation and use the available tools when ready. Reissue any tool call rejected for incomplete arguments with complete arguments. '
                  'Saved files, recorded usage and remaining preparation budgets are preserved.'})
    return {'stop_reason':reason,'history_preserved':True,'usage_counters_preserved':True,
            'submission_streak_preserved':True}
