Used by SKILL.md step 9.

# Input

* **staging:** required - default: none - The validated staging folder `<STAGING>`.
* **path:** required - default: none - The target folder `<PATH>` from SKILL.md step 4.
* **last-validation:** required - default: none - `pass`, or the failures from the last measure.py run and validate-rules pass.

# Process

### 1. Confirm the last validation passed

Check `last-validation`. Continue only when the last measure.py run printed `failures: none` and the validate-rules pass found nothing. Otherwise write nothing under `<PATH>` and return to SKILL.md step 6 with the failures.

Do:
* Continue when `last-validation` is `pass`.
* Return to SKILL.md step 6 with `rule 5: step 3 has no Don't list` when that was the last result.

Don't:
* Install a draft whose last validation failed; fix and validate again first.
* Treat a warning such as `warnings: 14` as a failure; only the `failures:` line blocks install.

### 2. Mirror the staging folder

Run `python3 {{ SKILL_ROOT }}/scripts/stage.py sync <STAGING> <PATH>` with Bash. Read its `written:`, `removed:` and `files:` lines.

Do:
* Run `python3 {{ SKILL_ROOT }}/scripts/stage.py sync <STAGING> {{ USER_ROOT }}/.claude/skills/pr-review`.
* Keep the `files:` line for the report, such as `files: none` for a skill with only SKILL.md.

Don't:
* Copy files by hand with `cp`; the script also removes stale files and reports every change.
* Run the sync twice; one run mirrors every file.

### 3. Check what was removed

Compare each `removed:` line with the request. When a removed file is one the user did not ask to remove, name it in `warnings` so the user can restore it.

Do:
* Report `warnings: removed {{ USER_ROOT }}/.claude/skills/pr-review/evals/evals.json` when the request did not mention evals.
* Report `removed: none` when the sync printed no `removed:` line.

Don't:
* Hide a removal; list every `removed:` line in the output.
* Restore a removed file yourself; report it and let the user decide.

# Output

Reply with this block, or with the failure block when install did not run.

```text
skill-md: <PATH>/SKILL.md
supporting-files: <the files line, or none>
removed: <removed paths, or none>
warnings: <list, or none>
```

Do:
* `skill-md: {{ USER_ROOT }}/.claude/skills/pr-review/SKILL.md`
* `supporting-files: {{ PROJECT_ROOT }}/.claude/skills/catalogue/references/prices.md`

Don't:
* Report success before the sync ran; the Do items show paths the sync printed.
* Edit a different skill ("also update the naming skill to match"); say a separate request is needed.

```text
status: blocked | failed
reason: <one sentence>
missing: none
```
