"""Small derived metadata for dashboards; full checkpoints remain authoritative."""
FIELDS = (
    'model','participant_revision','replicate','generation','condition','parent','parent_checkpoint_sha256',
    'attempt','attempt_started_at','discarded_attempt_cost_usd','conversation_paused','automatic_retries_paused','automatic_retry_at','automatic_retry_attempts','status','validity','calls','completed_calls','failure','context_recoveries','manual_frozen','steps',
    'test_matches','replay_reads','wall_seconds','cost_spent','money_reserved','token_usage_known','input_tokens','output_tokens',
    'submission','in_flight','retry_count','continuation_identity','provider_parameter_overrides','reserved','current_tool',
)


def project(state):
    return {**{key:state[key] for key in FIELDS if key in state and state[key] is not None},
            'messages':len(state.get('history',[])),
            'replay_reads':sum(message.get('role')=='tool' and message.get('name') in {'read_replay','read_past_fight'} for message in state.get('history',[]))}
