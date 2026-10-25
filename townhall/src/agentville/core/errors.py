"""Umbrella exception hierarchy."""

from collections.abc import Sequence
from typing import Any


class AgentvilleError(Exception):
    """Base class for every Agentville error."""


class ConfigError(AgentvilleError):
    """The configuration file is missing or invalid."""


class TownhallError(AgentvilleError):
    """Base class for Townhall storage and workflow errors."""


class NotFoundError(TownhallError):
    """A board, ticket, page, task or question does not exist."""


class AlreadyExistsError(TownhallError):
    """A board, ticket, task or page that must be new already exists."""


class InvalidInputError(TownhallError):
    """The caller supplied an id, path, status or payload that is not acceptable."""


class InvalidTransitionError(TownhallError):
    """A stage move is not allowed by the Townhall state machine."""


class ClaimError(TownhallError):
    """A ticket claim cannot be taken, held or released."""


class PageBudgetError(TownhallError):
    """Content failed the page-budget linter while budgets are enforced.

    `findings` holds the linter findings (objects with `rule`, `file`, `line`,
    `message` and `severity`). It is typed loosely so `core` stays free of
    imports from the Townhall domain.
    """

    def __init__(self, message: str, findings: Sequence[Any]) -> None:
        super().__init__(message)
        self.findings = list(findings)
