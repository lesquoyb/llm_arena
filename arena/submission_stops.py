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
