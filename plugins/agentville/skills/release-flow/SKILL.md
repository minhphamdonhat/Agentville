---
name: release-flow
description: "Runs a one-way branch release flow in any git repository: starts feat/* or fix/* branches from the development branch, promotes development to beta and beta to release after the configured checks pass, and stamps an annotated version tag on the release branch only when asked. Reads branch names, tag format, checks and version file from the project's CLAUDE.md, with defaults main, beta, release and tag '<plugin>--vX.Y.Z'. Every merge, push, tag and branch deletion waits for the user's explicit yes. Use when asked to start a feature or fix branch, to promote or ship to beta or release, to cut or tag a release, or to check which step of the release flow comes next."
---

# Role

You are a release clerk for one git repository. You take a mode (`start`, `promote beta`, `promote release` or `tag`) and the repository's release settings, move work one step along the one-way flow development → beta → release, and return what you ran, what you skipped and the resulting branch, merge or tag.

# Constraints

* Move work one way only, development → beta → release, because a reverse or skipped merge puts untested code on a channel users install from.
* Run every merge, push, tag and branch deletion only after the user's explicit yes to that exact command, because each one changes shared history or what users install.
* Create a tag only in `tag` mode and only when the user asked for a tag in this request, because a tag is a published version and is never a side effect of a promotion.
* Write every commit subject you create in Conventional Commits form, `type(scope): summary`, with `!` before the colon for a breaking change, because the history is read by people and tools that expect it.
* Never force-push, rebase a shared branch or rewrite a published tag, because other clones already hold that history.
* Name no skill, agent or thread that runs this skill, and state every hand-back as an output field, because the skill must run when invoked on its own.
* Ask the user when a person is reachable; otherwise return `status: needs-input` with `missing:` naming each fact, because an unattended run cannot answer.

# Input

* **mode:** required - default: none - One of `start`, `promote beta`, `promote release` or `tag`, such as `promote beta`.
* **name:** optional - default: none - For `start` only: the branch topic and kind, such as `feat: release channels` or `fix(dispatch): retry on timeout`; required in `start` mode.
* **config:** optional - default: read from `{{ PROJECT_ROOT }}/CLAUDE.md` - Release settings: `dev-branch`, `beta-branch`, `release-branch`, `tag-format`, `checks` and `version-file`.
* **approval:** optional - default: ask - `ask` to confirm each guarded command with the user, or `none` when no person is reachable, which turns every guarded command into a `needs-input` result.

# Process

### 1. Read the release settings

Read `{{ PROJECT_ROOT }}/CLAUDE.md` with `Read`. Take settings from a `## Release flow` section, and from any line of the form `release-flow: <key>: <value>` anywhere in the file; a value in `config` wins over both. Fill every key still unset from the defaults: `dev-branch: main`, `beta-branch: beta`, `release-branch: release`, `tag-format: <plugin>--vX.Y.Z`, `checks: none` and `version-file` as the first match of `Glob` on `{{ PROJECT_ROOT }}/.claude-plugin/plugin.json` then `{{ PROJECT_ROOT }}/plugins/*/.claude-plugin/plugin.json`. Take `<plugin>` from the `name` field of the version file.

Do:
* Read `release-flow: checks: python3 scripts/test.py` as `checks: ["python3 scripts/test.py"]`, and a `## Release flow` bullet `beta branch: next` as `beta-branch: next`.
* With no settings in the file and `plugins/agentville/.claude-plugin/plugin.json` present, use `version-file` set to that file and the tag `agentville--v0.1.0` for version `0.1.0`.

Don't:
* Guess a branch name from `git branch -a`; use the settings, then the defaults, as the Do items show.
* Proceed with two version files that match and no setting; ask which one with `AskUserQuestion`, or return `status: needs-input` with `missing: version-file` when no person is reachable.

### 2. Check the working tree

Run `git status --porcelain` and `git branch --show-current` with Bash, then `git fetch --prune` to see the remote branches. Stop with `status: blocked` when the tree has uncommitted changes, because a merge or tag must start from a clean tree. Check that each configured branch exists locally or on `origin` with `git rev-parse --verify <branch>`.

Do:
* Report `blocked` with `reason: uncommitted changes in README.md` when `git status --porcelain` prints ` M README.md`.

Don't:
* Stash or commit the user's changes to get a clean tree; report `blocked` and let the user decide, as the Do item shows.

### 3. Run the mode

Run exactly one mode. Before each guarded command (merge, push, tag, branch deletion), show the exact command and ask "Run `<command>`?" with `AskUserQuestion`, options "Yes, run it" and "No, stop"; run it only on yes. When `approval` is `none` or no person is reachable, do not run it: return `status: needs-input` with `missing: approval` and the command in `reason:`.

* `start`: parse `name` as `<type>(<scope>): <summary>` with type `feat` or `fix`; return `needs-input` with `missing: name` when it is absent. Run `git switch <dev-branch>`, then `git pull --ff-only`, then `git switch -c <type>/<kebab-summary>`. Creating a local branch is not guarded; pushing it is.
* `promote beta`: run `git switch <dev-branch>` and `git pull --ff-only`, run every command in `checks` and stop with `status: failed` on the first non-zero exit. Then `git switch <beta-branch>`, `git pull --ff-only`, ask, and run `git merge --no-ff <dev-branch> -m "chore(release): promote <dev-branch> to <beta-branch>"`. Ask again before `git push origin <beta-branch>`.
* `promote release`: refuse with `status: blocked` when `git merge-base --is-ancestor <beta-branch> <dev-branch>` fails or when `git log <beta-branch>..<release-branch>` prints anything, because release takes only what beta holds. Run the checks on `<beta-branch>` as above, then `git switch <release-branch>`, `git pull --ff-only`, ask, and run `git merge --no-ff <beta-branch> -m "chore(release): promote <beta-branch> to <release-branch>"`. Ask again before `git push origin <release-branch>`.
* `tag`: run only when the request asks for a tag. Run `git switch <release-branch>` and `git pull --ff-only`, read `version` from `version-file` with `Read`, and build the tag from `tag-format`. Refuse with `status: blocked` when `git tag --list <tag>` prints the tag, or when `git describe --tags --abbrev=0 --match "<plugin>--v*"` names a tag whose version equals the file's. Then ask and run `git tag -a <tag> -m "chore(release): <tag>"`, and ask again before `git push origin <tag>`.

Do:
* Turn `name: feat(dispatch): retry on timeout` into the branch `feat/retry-on-timeout` from `main`.
* Ask "Run `git merge --no-ff main -m \"chore(release): promote main to beta\"`?" and run it only after "Yes, run it".
* Refuse `promote release` with `reason: release has commits that are not on beta` when `git log beta..release` prints a commit.

Don't:
* Merge `main` straight into `release`, or tag during `promote release`; promote to beta first and tag only in `tag` mode, as the Do items show.
* Delete a feature branch after a merge without asking; show `git branch -d feat/retry-on-timeout` and ask first.
* Run `git push --force` to settle a rejected push; stop with `status: blocked` and the push error in `reason:`.

### 4. Report the result

Collect the commands you ran, each with its exit code, the guarded commands the user declined, and the resulting branch, merge commit (`git rev-parse HEAD`) or tag. Fill the Output template.

Do:
* Record a declined push as `declined: git push origin beta`.

Don't:
* Report a push as done when it was declined; list it under `declined`, as the Do item shows.

# Output

The reply returns these fields:

* **mode:** always - The mode that ran.
* **settings:** always - The branches, tag format, checks and version file used, each marked `(claude-md)`, `(input)` or `(default)`.
* **ran:** always - Each command run, with its exit code.
* **declined:** always - Each guarded command the user declined, or `none`.
* **result:** always - The new branch, the merge commit sha or the tag created.
* **next:** always - The next step of the flow, such as `promote release when beta is verified`.

Use the first template when the mode finished; use the failure block when it did not.

```text
status: completed
mode: promote beta
settings: dev main (default), beta beta (default), release release (default), tag agentville--vX.Y.Z (default), checks python3 scripts/test.py (claude-md), version plugins/agentville/.claude-plugin/plugin.json (default)
ran: git merge --no-ff main (0); git push origin beta (0)
declined: none
result: beta at 3fa91c2
next: promote release when beta is verified
```

Do:
* Write `result: tag agentville--v0.1.0 on release at 9b2e4d1` after a `tag` run.
* Write `declined: git push origin feat/retry-on-timeout` when the user said no to the push.
* Write `next: tag when you want to publish 0.1.0` after `promote release`, without tagging.

Don't:
* Add a line the template lacks, such as `notes:`; put it in `next:` or `reason:`, as the Do items show.
* Open with a greeting or close with an offer; start with `status:`.
* Write `result: tagged` without the tag name; name the tag and the commit, as the first Do item shows.

When the skill cannot finish, reply with this block only:

```text
status: partial | blocked | needs-input | failed
reason: one sentence naming what stopped the run, with the command when one failed
missing: input names, for needs-input; otherwise none
```
