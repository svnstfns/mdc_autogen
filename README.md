# Cursor MDC Generator

Autogenerate better Cursor documentation files (MDC) to build faster.

## Features

- Analyzes repository structure and code dependencies
- Generates documentation files (MDC) for Cursor
- Visualize dependency graph between files (if enabled)
- Supports both local and remote repositories
- Compatible with python, typescript, and javascript (for now)

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

You may need to install pygraphviz separately

macOS:
```bash
brew install graphviz
pip install --global-option=build_ext --global-option="-I/opt/homebrew/include/" --global-option="-L/opt/homebrew/lib/" pygraphviz
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
