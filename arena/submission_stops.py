"""Submission reminders require an explicit, completed model turn."""


def completed_turn(response):
    reason=str(response.get('stop_reason') or response.get('finish_reason') or '').lower()
    return reason in {'stop','end_turn','completed','stop_sequence','end'}


def reset_streak(state, *, interrupted=False):
    previous=state.get('consecutive_submission_reminders',0)
    state['consecutive_submission_reminders']=0
    if interrupted and previous:state['interrupted_stop_streak']=previous
    return previous


def interrupted_response(state, response):
    """Keep the received output and usage without treating truncation as a stop."""
    reset_streak(state,interrupted=True)
    reason=response.get('stop_reason') or response.get('finish_reason')
    state.update(status='provider_unavailable',pending=None,cursor=0,in_flight=False)
    state['failure']={'message':
        'The provider response did not confirm a completed model turn '
        f'(finish reason: {reason if reason is not None else "missing"}). '
        'The response and its reported usage are saved. Retry continues the same preparation session; '
        'this interruption does not count toward submission reminders.',
        'phase':'provider response','retryable':True,'uncertain':False,
        'incomplete_response':True,'stop_reason':reason}
    return {'error':state['failure']['message'],'retryable':True,'uncertain':False,'stop_reason':reason}
