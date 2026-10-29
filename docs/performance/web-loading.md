# Inspecting slow pages

Open **Load diagnostics** in the workspace header or **More → Load diagnostics**
in a competition. Use **Copy diagnostics** to share server and browser timings.
The report includes requests still running, not just completed requests.

- `seconds`: request wall time, including waiting.
- `thread_cpu_seconds`: CPU time used by that request thread only.
- `store_lock_wait`: time waiting to acquire the shared Store lock.
- `revision`: detecting changed artifacts.
- `states` and `usage_receipts`: conversation metadata and API usage receipts.
- `match_index` and `workspace_artifact`: compact fight index and uncached files.
- `_workspace_summary`: workspace aggregation, including nested reads.
- `json_serialization` and `socket_write`: encoding and sending the result.
- Browser timings include fetch, body transfer and parsing; `Summary charts`
  measures chart markup generation.

Stage timings are inclusive: nested times overlap and must not be added together.
The last 80 API requests and currently running requests are held in memory.
No prompts, credentials, request bodies or artifact contents are recorded.
