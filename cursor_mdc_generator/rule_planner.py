"""
rule_planner.py

Thematic planner that detects project properties (frameworks, tooling, configs)
and plans targeted rule-sets instead of generating one rule per file.
"""

import os
import re
import glob
import json
from typing import Dict, List, Set, Optional, Any
from pathlib import Path


class ProjectDetector:
    """Detects technologies and frameworks used in a project."""

    # Default detection patterns
    DETECTION_PATTERNS = {
        "vue": [r"\bvue\b", r"@vue/", r"\.vue$"],
        "react": [r"\breact\b", r"react-dom"],
        "vite": [r"\bvite\b"],
        "pinia": [r"\bpinia\b"],
        "typescript": [r"\btypescript\b", r"\.ts$", r"\.tsx$"],
        "javascript": [r"\.js$", r"\.jsx$"],
        "tailwind": [r"\btailwindcss\b", r"tailwind.config"],
        "fastapi": [r"\bfastapi\b", r"from fastapi"],
        "flask": [r"\bflask\b", r"from flask"],
        "django": [r"\bdjango\b"],
        "pydantic": [r"\bpydantic\b"],
        "sqlalchemy": [r"\bsqlalchemy\b"],
        "alembic": [r"\balembic\b"],
        "sqlite": [r"sqlite://", r"\.db$"],
        "postgresql": [r"postgresql://", r"\bpsycopg"],
        "pytest": [r"\bpytest\b"],
        "jest": [r"\bjest\b"],
        "vitest": [r"\bvitest\b"],
        "pre-commit": [r"\bpre-commit\b", r"\.pre-commit-config\.yaml"],
        "ruff": [r"\bruff\b"],
        "black": [r"\bblack\b"],
        "mypy": [r"\bmypy\b"],
        "eslint": [r"\beslint\b"],
        "prettier": [r"\bprettier\b"],
        "openapi": [r"\bopenapi\b", r"\bswagger\b"],
        "docker": [r"^Dockerfile", r"docker-compose"],
        "kubernetes": [r"\.yaml$.*kind:", r"kubectl"],
        "python": [r"\.py$"],
    }

    # Important files to scan for detection
    CONFIG_FILES = [
        "package.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "package-lock.json",
        "pyproject.toml",
        "poetry.lock",
        "Pipfile",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.py",
        "setup.cfg",
        ".pre-commit-config.yaml",
        "tsconfig.json",
        "vite.config.*",
        "vue.config.*",
        "jest.config.*",
        "vitest.config.*",
        ".eslintrc.*",
        ".prettierrc.*",
        "tailwind.config.*",
        "openapi.yaml",
        "openapi.yml",
        "openapi.json",
        "swagger.yaml",
        "swagger.yml",
        "Dockerfile",
        "docker-compose*.yml",
        "docker-compose*.yaml",
        "alembic.ini",
    ]

    def __init__(self, repo_root: str):
        """
        Initialize detector.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = Path(repo_root).resolve()

    def detect(self) -> Dict[str, bool]:
        """
        Detect technologies used in the project.

        Returns:
            Dict mapping technology names to detection status
        """
        detections: Dict[str, bool] = {tech: False for tech in self.DETECTION_PATTERNS.keys()}

        # Scan configuration files
        corpus = self._gather_config_content()

        # Pattern matching in config files
        for tech, patterns in self.DETECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, corpus, re.IGNORECASE | re.MULTILINE):
                    detections[tech] = True
                    break

        # Filesystem-based detection
        self._detect_from_filesystem(detections)

        return detections

    def _gather_config_content(self) -> str:
        """Gather content from configuration files."""
        corpus = ""
        for filename in self.CONFIG_FILES:
            # Handle wildcards
            if "*" in filename:
                pattern = str(self.repo_root / filename)
                for path in glob.glob(pattern):
                    corpus += "\n" + self._read_file(path)
            else:
                path = self.repo_root / filename
                if path.exists():
                    corpus += "\n" + self._read_file(str(path))
        return corpus

    def _detect_from_filesystem(self, detections: Dict[str, bool]) -> None:
        """Detect technologies based on file extensions and structure."""
        # Quick file type detection
        extensions = {
            ".vue": "vue",
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".db": "sqlite",
        }

        # Sample some files (not exhaustive scan for performance)
        for ext, tech in extensions.items():
            if not detections[tech]:
                pattern = str(self.repo_root / "**" / f"*{ext}")
                files = list(glob.iglob(pattern, recursive=True))
                if files:
                    detections[tech] = True

        # Test directory presence
        test_dirs = list(self.repo_root.glob("**/tests")) + list(self.repo_root.glob("**/test"))
        if test_dirs and detections["python"]:
            detections["pytest"] = True

    def _read_file(self, path: str, max_size: int = 100000) -> str:
        """Read file content safely."""
        try:
            file_path = Path(path)
            if file_path.stat().st_size > max_size:
                return ""  # Skip large files
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def get_project_summary(self) -> Dict[str, Any]:
        """
        Get a structured summary of detected project properties.

        Returns:
            Dict with frameworks, languages, tooling, and testing info
        """
        detections = self.detect()

        summary = {
            "frameworks": {
                "frontend": [],
                "backend": [],
            },
            "languages": [],
            "databases": [],
            "testing": [],
            "tooling": {
                "build": [],
                "lint": [],
                "format": [],
                "pre_commit": detections.get("pre-commit", False),
            },
            "infrastructure": [],
        }

        # Categorize detections
        if detections.get("vue"):
            summary["frameworks"]["frontend"].append("Vue")
        if detections.get("react"):
            summary["frameworks"]["frontend"].append("React")
        if detections.get("vite"):
            summary["tooling"]["build"].append("Vite")

        if detections.get("fastapi"):
            summary["frameworks"]["backend"].append("FastAPI")
        if detections.get("flask"):
            summary["frameworks"]["backend"].append("Flask")
        if detections.get("django"):
            summary["frameworks"]["backend"].append("Django")

        if detections.get("python"):
            summary["languages"].append("Python")
        if detections.get("typescript"):
            summary["languages"].append("TypeScript")
        if detections.get("javascript"):
            summary["languages"].append("JavaScript")

        if detections.get("sqlite"):
            summary["databases"].append("SQLite")
        if detections.get("postgresql"):
            summary["databases"].append("PostgreSQL")
        if detections.get("sqlalchemy"):
            summary["databases"].append("SQLAlchemy")

        if detections.get("pytest"):
            summary["testing"].append("pytest")
        if detections.get("jest"):
            summary["testing"].append("Jest")
        if detections.get("vitest"):
            summary["testing"].append("Vitest")

        if detections.get("ruff"):
            summary["tooling"]["lint"].append("Ruff")
        if detections.get("eslint"):
            summary["tooling"]["lint"].append("ESLint")
        if detections.get("mypy"):
            summary["tooling"]["lint"].append("mypy")

        if detections.get("black"):
            summary["tooling"]["format"].append("Black")
        if detections.get("prettier"):
            summary["tooling"]["format"].append("Prettier")

        if detections.get("docker"):
            summary["infrastructure"].append("Docker")
        if detections.get("kubernetes"):
            summary["infrastructure"].append("Kubernetes")

        return summary


class ThematicRulePlanner:
    """Plans thematic rule-sets based on detected project properties."""

    def __init__(self, repo_root: str, mapping: Optional[Dict] = None):
        """
        Initialize planner.

        Args:
            repo_root: Path to repository root
            mapping: Optional mapping configuration (detection -> rules)
        """
        self.repo_root = repo_root
        self.detector = ProjectDetector(repo_root)
        self.mapping = mapping or {}

    def plan_rules(self) -> List[Dict[str, Any]]:
        """
        Plan thematic rules based on project detection.

        Returns:
            List of rule specifications to generate
        """
        detections = self.detector.detect()
        rules = []

        # Get mapping from config
        detection_map = self.mapping.get("detections", {})

        # Add rules based on detections
        for tech, detected in detections.items():
            if not detected:
                continue

            if tech in detection_map:
                for rule_spec in detection_map[tech]:
                    # Create a copy to avoid modifying original
                    rule = rule_spec.copy()
                    rule["detected_via"] = tech
                    rules.append(rule)

        # Always add foundation rules
        foundation_rules = [
            {
                "category": "00-foundation",
                "slug": "base-standards",
                "description": "Project-wide base standards (directory structure, naming, security basics)",
                "tags": ["foundation", "standards"],
                "globs": [],
                "activation": "always",
            },
        ]

        # Deduplicate by category/slug
        seen = set()
        unique_rules = []
        
        for rule in foundation_rules + rules:
            key = f"{rule['category']}/{rule['slug']}"
            if key not in seen:
                seen.add(key)
                unique_rules.append(rule)

        return unique_rules

    def get_project_context(self) -> str:
        """
        Generate a text summary of project context for LLM prompts.

        Returns:
            Formatted string describing the project
        """
        summary = self.detector.get_project_summary()

        context_parts = []

        if summary["frameworks"]["frontend"]:
            context_parts.append(f"Frontend: {', '.join(summary['frameworks']['frontend'])}")
        if summary["frameworks"]["backend"]:
            context_parts.append(f"Backend: {', '.join(summary['frameworks']['backend'])}")
        if summary["languages"]:
            context_parts.append(f"Languages: {', '.join(summary['languages'])}")
        if summary["databases"]:
            context_parts.append(f"Databases: {', '.join(summary['databases'])}")
        if summary["testing"]:
            context_parts.append(f"Testing: {', '.join(summary['testing'])}")

        tooling = []
        if summary["tooling"]["build"]:
            tooling.append(f"Build: {', '.join(summary['tooling']['build'])}")
        if summary["tooling"]["lint"]:
            tooling.append(f"Lint: {', '.join(summary['tooling']['lint'])}")
        if summary["tooling"]["format"]:
            tooling.append(f"Format: {', '.join(summary['tooling']['format'])}")
        if tooling:
            context_parts.append(f"Tooling: {'; '.join(tooling)}")

        if summary["infrastructure"]:
            context_parts.append(f"Infrastructure: {', '.join(summary['infrastructure'])}")

        return "\n".join(context_parts)


def load_mapping_config(mapping_path: Optional[str] = None) -> Dict:
    """
    Load mapping configuration from YAML or JSON.

    Args:
        mapping_path: Optional path to mapping file. If None, uses default.

    Returns:
        Mapping configuration dict
    """
    if mapping_path and os.path.exists(mapping_path):
        try:
            # Try YAML first
            import yaml
            with open(mapping_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            # Fallback to JSON if PyYAML not available
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load mapping file {mapping_path}: {e}")
                return {}
        except Exception as e:
            print(f"Warning: Could not load mapping file {mapping_path}: {e}")
            return {}

    # Return empty dict if no mapping file
    return {}
