Improve your submitted strategy using the existing code and conversation.
The scenario, tools and preparation rules are unchanged. Opponents may improve too.
No tournament results are provided for this branch. list_past_fights and read_past_fight are not authorized here; the server will refuse these calls. You can still use analyze, test and read_replay for your own preparation tests.
Submit the updated strategy explicitly. Optional preparation limits apply to this branch.

Before submit, call analyze on the final saved version of your entrypoint and
configured team. Read diagnostic_messages: each error includes its file, line and
message. Fix every error and analyze again until status is valid. Recheck after
any further code edit or team entrypoint change. Compilation success does not
prove correct behavior: use test and read_replay to check execution when needed.
submit only freezes files and ends preparation; it does not validate or repair
your script. Invalid code is a failed strategy submission, even if the fight
process completes. You cannot fix that frozen version during evaluation fights.
