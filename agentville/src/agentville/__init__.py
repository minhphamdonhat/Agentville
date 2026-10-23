"""Agentville: umbrella CLI and MCP platform."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentville")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0+unknown"
