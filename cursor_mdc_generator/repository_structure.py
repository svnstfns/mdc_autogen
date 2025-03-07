from git import Repo
import os
import re
import fnmatch
import logging


def glob_to_regex(pattern):
    """Convert a glob pattern to a regular expression."""
    return re.compile(fnmatch.translate(pattern))


def get_ignore_patterns(local_path):
    """Get compiled ignore patterns from .gitignore and common patterns."""
    # Read .gitignore file
    gitignore_path = os.path.join(local_path, ".gitignore")
    ignore_patterns = []

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            ignore_patterns = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
        logging.info(f"Found .gitignore file with {len(ignore_patterns)} patterns")

    # Common patterns to ignore - these are directly compiled as regex patterns
    common_ignores = [
        r".*\.git$",  # Match the .git directory itself
        r".*\.git/.*",  # Match contents inside .git
        r".*\.github$",  # Match the .github directory itself
        r".*\.github/.*",
        r".*\.gitignore$",  # Match the .gitignore file itself
        r".*\.gitignore/.*",
        r".*\.ruff.toml$",  # Match the .ruff.toml file itself
        r".*\.ruff.toml/.*",
        r".*ruff.toml$",  # Match the ruff.toml file itself without the dot
        r".*ruff.toml/.*",
        r".*\.pyproject.toml$",  # Match the .pyproject.toml file itself
        r".*\.pyproject.toml/.*",
        r".*pyproject.toml$",  # Match the pyproject.toml file itself without the dot
        r".*pyproject.toml/.*",
        r".*__init__.py",
        r".*package-lock.json",
        r".*package.json",
        r".*\.DS_Store",
        r".*\.vscode$",  # Match the .vscode directory itself
        r".*\.vscode/.*",
        r".*tests$",  # Match the tests directory itself
        r".*tests/.*",
        r".*\.pyc",
        r".*__pycache__$",  # Match the __pycache__ directory itself
        r".*__pycache__/.*",
        r".*\.idea$",  # Match the .idea directory itself
        r".*\.idea/.*",
        r".*node_modules$",  # Match the node_modules directory itself
        r".*node_modules/.*",
        r".*dist$",  # Match the dist directory itself
        r".*dist/.*",
        r".*build$",  # Match the build directory itself
        r".*build/.*",
        r".*vendor$",  # Match the vendor directory itself
        r".*vendor/.*",
        r".*\.next$",  # Match the .next directory itself
        r".*\.next/.*",
        r".*coverage$",  # Match the coverage directory itself
        r".*coverage/.*",
        r".*\.pytest_cache$",  # Match the .pytest_cache directory itself
        r".*\.pytest_cache/.*",
        r".*\.cache$",  # Match the .cache directory itself
        r".*\.cache/.*",
        r".*\.cursor$",  # Match the .cursor directory itself
        r".*\.cursor/.*",
        r".*\.ruff_cache$",  # Match the .ruff_cache directory itself
        r".*\.ruff_cache/.*",
        r".*\.DS_Store",
        r".*\.DS_Store/.*",
        r".*\.venv$",  # Match the .venv directory itself
        r".*\.venv/.*",
        r".*\.env",
        r".*\.env$",  # Match the .env file itself
        r".*\.env/.*",
        r".*\.env.local$",  # Match the .env.local file itself
        r".*\.env.local/.*",
        # Ignore License and Readme files
        r".*LICENSE$",
        r".*LICENSE/.*",
        r".*README$",
        r".*README/.*",
    ]

    # Compile gitignore patterns using fnmatch.translate and common patterns directly
    compiled_ignore_patterns = []

    # Process gitignore patterns (use glob_to_regex)
    for pattern in ignore_patterns:
        compiled_ignore_patterns.append(glob_to_regex(pattern))

    # Process common patterns (direct regex compilation)
    for pattern in common_ignores:
        compiled_ignore_patterns.append(re.compile(pattern))

    return compiled_ignore_patterns


def should_ignore(file_path, compiled_ignore_patterns):
    """Check if a file path should be ignored based on patterns."""
    try:
        # Convert file_path to an absolute path for consistent matching
        abs_file_path = os.path.abspath(file_path)
        for pattern in compiled_ignore_patterns:
            if pattern.match(abs_file_path):
                return True
    except Exception as e:
        logging.error(f"Error checking ignore pattern: {e}. File path: {file_path}")
    return False


def get_repo_files(repo_url=None, local_path=None, oauth_token=None):
    """
    Get a list of relevant files from a repository.

    Args:
        repo_url: GitHub repository URL (optional if local_path is a valid repo)
        local_path: Local path to repository
        oauth_token: OAuth token for private repositories

    Returns:
        List of relevant files
    """
    # Check if we need to clone the repository
    if repo_url and not os.path.exists(local_path):
        logging.info(f"Cloning repository: {repo_url}")

        # Handle OAuth token for private repositories
        if oauth_token:
            # Format the URL with the token for authentication
            if repo_url.startswith("https://"):
                auth_url = repo_url.replace(
                    "https://", f"https://{oauth_token}:x-oauth-basic@"
                )
                Repo.clone_from(auth_url, local_path)
            else:
                logging.error("OAuth token provided but repository URL is not HTTPS")
                return []
        else:
            # Clone public repository
            Repo.clone_from(repo_url, local_path)
    elif os.path.exists(local_path):
        logging.info(f"Using existing repository at {local_path}")
    else:
        logging.error("Neither a valid repository URL nor a local path was provided")
        return []

    # Get ignore patterns
    compiled_ignore_patterns = get_ignore_patterns(local_path)

    # Collect all relevant files
    relevant_files = []
    for root, dirs, files in os.walk(local_path):
        # Filter out directories that match ignore patterns
        dirs[:] = [
            d
            for d in dirs
            if not should_ignore(os.path.join(root, d), compiled_ignore_patterns)
        ]

        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, local_path)
            if not should_ignore(file_path, compiled_ignore_patterns):
                relevant_files.append(rel_path)

    return relevant_files


def generate_directory_structure(repo_path):
    """Generate a visual representation of the repository directory structure."""
    result = []

    # Get ignore patterns
    compiled_ignore_patterns = get_ignore_patterns(repo_path)

    def _list_directory(path, prefix="", is_last=False):
        # Skip paths that should be ignored
        if should_ignore(path, compiled_ignore_patterns):
            return

        # Use appropriate branch symbols
        branch = "└── " if is_last else "├── "
        result.append(f"{prefix}{branch}{os.path.basename(path)}")

        # Prepare the prefix for children
        extension = "    " if is_last else "│   "

        # List directories first, then files
        items = os.listdir(path)
        dirs = sorted(
            [
                item
                for item in items
                if os.path.isdir(os.path.join(path, item))
                and not should_ignore(
                    os.path.join(path, item), compiled_ignore_patterns
                )
            ]
        )
        files = sorted(
            [
                item
                for item in items
                if os.path.isfile(os.path.join(path, item))
                and not should_ignore(
                    os.path.join(path, item), compiled_ignore_patterns
                )
            ]
        )

        # Process directories
        for i, d in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and not files
            _list_directory(os.path.join(path, d), prefix + extension, is_last_dir)

        # Process files
        for i, f in enumerate(files):
            is_last_file = i == len(files) - 1
            branch = "└── " if is_last_file else "├── "
            result.append(f"{prefix}{extension}{branch}{f}")

    # Start from the root directory
    result.append(os.path.basename(repo_path) + "/")
    _list_directory(repo_path)

    return "\n".join(result)
