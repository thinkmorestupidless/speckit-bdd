"""Checks a spec-kit project's Gherkin features against its glossary and its specs."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("speckit-bdd")
except PackageNotFoundError:  # run from a source tree that was never installed
    __version__ = "0.0.0"
