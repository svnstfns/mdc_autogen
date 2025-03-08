# Cursor MDC Generator

A tool to generate Cursor IDE documentation files (MDC) from repository analysis.

## Installation

You can install the package using pip:

```bash
pip install mdcgen
```

Or with uv:

```bash
uv install mdcgen
```

## Installation with Visualization Support

macOS:
```bash
brew install graphviz
pip install mdcgen[visualization]
```

Ubuntu / Debian:
```bash
sudo apt-get install graphviz graphviz-dev
pip install mdcgen[visualization]
```

Windows:
  - Download and install Graphviz from https://graphviz.org/download/
  - Add the Graphviz bin directory to your PATH
  - Run: pip install mdcgen[visualization]

## Usage

To analyze a repository and generate MDC files:

```bash
# Analyze current directory
mdcgen

# Analyze a specific local directory
mdcgen /path/to/repository

# Analyze a remote repository
mdcgen --repo https://github.com/user/repo

# Specify output directory
mdcgen /path/to/repository --out ./mdc-output

# Use a specific model
mdcgen /path/to/repo --model gpt-4o

# Skip visualization (useful if you don't have Graphviz installed)
mdcgen /path/to/repo --no-viz
```

For private repositories:

```bash
mdcgen --repo https://github.com/user/private-repo --token YOUR_GITHUB_TOKEN
```

## Features

- Analyzes repository structure and code dependencies
- Creates dependency graphs to visualize relationships between files (if enabled)
- Generates documentation files (MDC) for use with Cursor IDE
- Supports both local and remote repositories
- Compatible with various programming languages (python, typescript, javascript for now)

## Requirements

- Python 3.7+
- OpenAI/Anthropic/Google Key (set as environment variable vis-a-vis LiteLLM format)

## Command Reference

| Option | Alias | Description |
|--------|-------|-------------|
| `PATH` | | Local path to repository (default: current directory) |
| `--repo` | `-r` | GitHub repository URL (instead of local path) |
| `--out` | `-o` | Output directory for analysis files |
| `--model` | `-m` | Model to use for summaries (default: gpt-4o-mini) |
| `--token` | `-t` | OAuth token for private repositories |
| `--imports` | `-i` | Include @file references to imported files |
| `--no-viz` | | Skip generating dependency graph visualizations |
| `--no-dirs` | | Skip generating directory-level MDC files |
| `--depth` | `-d` | Max directory depth (0=repo only, 1=top-level dirs) |
| `--log-level` | | Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

## Examples

```bash
# Skip all directory-level MDCs (only generate file and repository MDCs)
mdcgen /path/to/repo --no-dirs

# Limit directory depth (0=repo only, 1=top-level dirs only)
mdcgen /path/to/repo --depth 1

# Include import references in MDC files
mdcgen /path/to/repo --imports

# Using short aliases for common options
mdcgen /path/to/repo -o ./output -m gpt-4o -d 1
```
```

The key changes I made:

1. Removed all references to the `analyze` subcommand
2. Updated examples to use the positional argument for local paths
3. Added an example for analyzing the current directory
4. Updated the command reference table to show `PATH` as the positional argument
5. Reorganized the examples section for clarity
6. Updated all command examples throughout the document

This README now accurately reflects the simplified CLI interface where users can just type `mdcgen` followed by an optional path.