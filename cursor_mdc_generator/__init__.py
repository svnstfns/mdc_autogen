"""
MDC Generator for Cursor IDE

A tool for automatically generating .mdc documentation files for codebases.
"""

from .repo_analyzer import analyze_repository

__all__ = ["analyze_repository"]

__version__ = "0.1.0"
