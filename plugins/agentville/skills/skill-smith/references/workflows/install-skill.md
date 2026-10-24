Used by SKILL.md step 9.

# Input

* **staging:** required - default: none - The validated staging folder `<STAGING>`.
* **path:** required - default: none - The target folder `<PATH>` from SKILL.md step 4.
* **scope:** required - default: none - `project` or `user`, from SKILL.md step 4.
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

Run `python3 {{ SKILL_ROOT }}/scripts/stage.py install <STAGING> <PATH> --scope <scope>` with Bash. Read its `written:`, `removed:` and `files:` lines. When it exits 2, write nothing, and return the failure template with `<status>blocked</status>` and the script's message in `<outcome>`; it refuses any `<PATH>` outside the chosen scope's skills folder and any plugin.

Do:
* Run `python3 {{ SKILL_ROOT }}/scripts/stage.py install <STAGING> {{ USER_ROOT }}/.claude/skills/acme-pr-review --scope user`.
* Keep the `files:` line for the report, such as `files: none` for a skill with only SKILL.md.

Don't:
* Copy files by hand with `cp`, or run `stage.py sync` onto the target; the install also removes stale files, reports every change and refuses a plugin.
* Run the install twice; one run mirrors every file.

### 3. Check what was removed

Compare each `removed:` line with the request. When a removed file is one the user did not ask to remove, name it in `<open>` so the user can restore it.

Do:
* Report `removed {{ USER_ROOT }}/.claude/skills/acme-pr-review/evals/evals.json` in `<open>` when the request did not mention evals.
* Report `removed: none` when the install printed no `removed:` line.

Don't:
* Hide a removal; list every `removed:` line in the output.
* Restore a removed file yourself; report it and let the user decide.

# Output

Reply with the six report tags below, or with the failure template when install did not run.

```text
<status>completed</status>
<outcome>The skill is installed at <PATH>.</outcome>
<claims>
- removed: <removed paths, or none>. verified: the removed: line stage.py install printed
</claims>
<artefacts>
skill-md: <PATH>/SKILL.md
supporting-files: <the files line, or none>
</artefacts>
<open><warnings, or none></open>
<deviations>none</deviations>
```

Do:
* `skill-md: {{ USER_ROOT }}/.claude/skills/acme-pr-review/SKILL.md`
* `supporting-files: {{ PROJECT_ROOT }}/.claude/skills/catalogue/references/prices.md`

Don't:
* Report success before the install ran; the Do items show paths the install printed.
* Edit a different skill ("also update the naming skill to match"); say a separate request is needed.

Reply with this template when install did not run:

```text
<status>blocked | needs-input | failed</status>
<outcome><one sentence></outcome>
<claims>none</claims>
<artefacts>none</artefacts>
<open>missing: none</open>
<deviations>none</deviations>
```
