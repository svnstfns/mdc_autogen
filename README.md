# Cursor MDC Generator

A tool to generate Cursor IDE documentation files (MDC) from repository analysis.

## Installation

You can install the package using pip:

```bash
pip install cursor-mdc-generator
```

Or with uv:

```bash
uv install cursor-mdc-generator
```

## Usage

To analyze a repository and generate MDC files:

```bash
# Analyze a local repository
cursor-mdc analyze --local-path /path/to/repository

# Analyze a remote repository
cursor-mdc analyze --repo-url https://github.com/user/repo

# Specify output directory
cursor-mdc analyze --repo-url https://github.com/user/repo --output-dir ./mdc-output

# Use a specific OpenAI model
cursor-mdc analyze --local-path /path/to/repo --model-name gpt-4
```

For private repositories:

```bash
cursor-mdc analyze --repo-url https://github.com/user/private-repo --oauth-token YOUR_GITHUB_TOKEN
```

## Features

- Analyzes repository structure and code dependencies
- Creates dependency graphs to visualize relationships between files
- Generates documentation files (MDC) for use with Cursor IDE
- Supports both local and remote repositories
- Compatible with various programming languages

## Requirements

- Python 3.7+
- OpenAI API Key (set as environment variable `OPENAI_API_KEY`)
