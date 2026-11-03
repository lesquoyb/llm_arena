You previously submitted a strategy. The previous competition round has finished.
You now have a new preparation period to improve that strategy before the next round.
Your previous submitted files are already in your workspace, including team.json
when you choose your team. The previous_submission field identifies the exact entrypoint and files. Start with
its read_workspace call; read_frozen retrieves the unchanged submitted version.
Submission or a successful test against passive does not prove a strong strategy.
Use the previous-round result summary below to investigate weaknesses before editing.

list_past_fights and read_past_fight expose your own earlier tournament
fights in this track. Omit round in list_past_fights for the previous round, or
pass round to inspect an older one; available_rounds lists the accessible rounds.
Each response identifies its round and your frozen submitted source. Opponent scripts and private logs are
inaccessible. If declared, list_submissions and read_submitted_file let you read
your own earlier source versions by round. Other tracks and opponents are forbidden.
Compile and test the revised code, then explicitly call submit. Opponents may improve too.
