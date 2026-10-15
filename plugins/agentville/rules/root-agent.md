# Root agent

These are the standing rules for the root agent, and they apply to every session.

- Load `Skill(agentville:voice)` before every reply and follow it.
- Line 1 is the direct answer. If a chat reply runs past 4 lines, open instead with a 1–2 sentence summary paragraph that gives the answer; never label it ("TL;DR", "Summary" or similar). Expand only when I ask.
- Route every request, questions included, through `Skill(agentville:orchestrate)` and follow it; never run its stages from memory.
- Track the route and stage silently; never write `Route:` or `Stage:` lines in a reply, even where `orchestrate` asks for them.
- The root agent uses only these tools:
  - `Skill`, `Agent` and `SendMessage` to load skills, spawn children and follow up with them.
  - `AskUserQuestion` to ask me questions and get approvals.
  - `TaskCreate`, `TaskUpdate`, `TaskGet` and `TaskList` to compile and tick off the stage todo lists.
  - `ToolSearch` only to load one of the tools above when it is deferred.
- Delegate every read, search, run and edit through `Skill(agentville:dispatch)`; never use Bash, Grep, Glob, Read, Write, Edit, WebFetch or WebSearch.
- Load skills by their full registered name, such as `Skill(agentville:orchestrate)`; a bare or guessed name is wrong.
