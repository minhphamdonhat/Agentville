# Packaging and release rules

Rules for `{{ SKILL_ROOT }}/assets/pyproject.toml`, `{{ SKILL_ROOT }}/assets/workflows/test.yml` and `{{ SKILL_ROOT }}/assets/workflows/publish.yml`.

## pyproject.toml

| Rule | Why |
| --- | --- |
| `[project.scripts]` holds a command named exactly like `[project].name`, such as `acme-tool = "acme_tool.cli:main"`. | `uvx acme-tool` runs the command named after the package; a different name needs `uvx --from acme-tool acme`. |
| `[build-system]` is `hatchling` with `build-backend = "hatchling.build"`. | One small, standard backend; `uv build` uses it with no extra setup. |
| `requires-python = ">=3.X"`, with `3.X` the newest stable CPython that `uv python list` shows. | uv downloads that Python on demand, so users need no system Python; a new floor drops old-version workarounds. |
| `dependencies = []` unless a need has no standard-library answer, and then each one is named with its reason in a comment. | Every dependency is resolved on each cold `uvx` run and is one more supply-chain risk. |
| `version` lives in `pyproject.toml` only; the code reads it with `importlib.metadata.version`. | One source of truth; the publish workflow checks the release tag against it. |
| `license` is an SPDX expression taken from the project's `LICENSE` file; drop the line when there is none. | Metadata must not claim a licence the project has not chosen. |

## Pinning actions

Pin every `uses:` line to a full 40-character commit SHA and name the tag in a comment: `uses: actions/checkout@<sha> # v5.0.0`. Read the SHA, never recall it:

```bash
git ls-remote --tags https://github.com/actions/checkout 'refs/tags/v5*'
```

An annotated tag prints two lines: `refs/tags/v5.0.0` (the tag object) and `refs/tags/v5.0.0^{}` (the commit). Take the `^{}` line. A lightweight tag prints one line, which is the commit. Take the highest `vX.Y.Z` tag with no pre-release suffix. The actions in the templates are `actions/checkout`, `astral-sh/setup-uv`, `actions/upload-artifact`, `actions/download-artifact` and `pypa/gh-action-pypi-publish`.

## Test workflow

`test.yml` runs on push to `main` and on pull requests, with `permissions: contents: read`, `persist-credentials: false` on checkout, and a matrix of `ubuntu-latest`, `macos-latest` and `windows-latest` with `fail-fast: false`. Each runner runs the unit tests, builds the wheel, runs it through `uvx --from <wheel>` with `--version` and `install --dry-run`, and checks the installer syntax for its own shell. Drop the `install --dry-run` line when the CLI has no `install` subcommand, and the installer steps when the project ships no installers.

## Publish workflow and trusted publishing

`publish.yml` runs when a GitHub release is published, in two jobs:

1. **build** (`contents: read`): checks out, checks that the release tag without its `v` equals `uv version --short`, runs `uv build`, and uploads `dist/` as an artifact.
2. **publish** (`needs: build`, `environment: pypi`, `permissions: id-token: write` and nothing else): downloads `dist/` and runs `pypa/gh-action-pypi-publish`, which swaps the GitHub OIDC token for a short-lived PyPI token.

Only the publish job can mint a PyPI credential, and it runs no project code. No API token is stored in GitHub secrets. Manual steps the user does once, outside the checkout:

* On PyPI, add a trusted publisher (a pending publisher for a new project) with the GitHub owner, the repository, workflow `publish.yml` and environment `pypi`.
* On GitHub, create the environment `pypi` and add required reviewers, so a release waits for approval before upload.
* Publish a GitHub release whose tag matches the version, such as `v0.1.0` for `version = "0.1.0"`.
