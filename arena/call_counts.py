"""Keep request sequence IDs separate from completed model responses."""


def completed_calls(state, db=None, sid=None):
    if 'completed_calls' in state:
        return state['completed_calls']
    if db is not None and sid is not None:
        return db.execute("SELECT count(*) FROM events WHERE session=? AND kind='model_response'",(sid,)).fetchone()[0]
    # Legacy detached summaries have no receipt journal; retain their historical value.
    return state.get('calls',0)


def hydrate_calls(state, db, sid):
    state['completed_calls']=completed_calls(state,db,sid)
    return state
