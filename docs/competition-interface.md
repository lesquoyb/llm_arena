# Competition views

**Activity** contains running requests, fight workers, throughput, queued work and
conversation recovery. Other views show one short status line linking to it.
Execution totals always describe the whole competition.

The sticky filter bar selects **Model**, **Round**, **Track** and **Repetition**.
Selections are shared by Summary, Conversations, Code & versions, Matches, Errors
and Journal, and are saved in the page URL. Shared competition files remain
visible in Files; conversation folders follow the selected scope. Reset clears
these exploration filters. A fight's opponent is not hidden by a candidate filter.

Charts have a **Full screen** button. Press Escape or **Exit full screen** to
return. The conversation reader also supports full screen; its secondary tools
are in **Conversation actions**.

Read the match matrix from the **row model's perspective** against the **column
opponent**. W/D/L counts are wins, draws and losses for the row model. Green
favors the row, red favors the column. Click a score or an outcome count to inspect
the corresponding fights. The diagonal has no comparative results.

Messages are collapsed as single compact rows. Open a row to inspect its content,
reasoning, tool arguments, file diffs or raw record. **Expand messages** and
**Collapse messages** control these outer rows independently of their inner data.

Files initially lists sources and reports. Enable **Include raw fight, tool and
provider artifacts** for the full artifact tree. Match lists load compact results;
the selected replay and its full statistics are fetched separately. Cached tab
contents stay visible while a refresh runs, and navigating away does not discard
an in-progress cached read.

If Load diagnostics reports that the route is unavailable, the running server
lacks that API even though it may be serving newer static interface files. Stop
the competition, restart the updated arena server, then resume the saved run.
Browser timings remain copyable in that dialog.
