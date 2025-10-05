"""
cli_thematic.py

Separate CLI for thematic rule generation.
Does not interfere with the existing file-based CLI.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import click

from .rule_planner import ThematicRulePlanner, load_mapping_config, ProjectDetector
from .rule_id_allocator import RuleIDAllocator
from .llm_utils.llm_client import generate_mdc_response
from .llm_utils.prompts import format_thematic_rule_prompt, format_project_summary_prompt, SYSTEM_PROMPT


logger = logging.getLogger(__name__)


def load_authoring_spec() -> str:
    """Load the rule authoring specification."""
    spec_path = Path(__file__).parent / "rule_authoring_spec.md"
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Could not load authoring spec: {e}")
        return "# Rule Authoring Specification\n(Specification file not found)"


def load_default_mapping() -> Dict:
    """Load default mapping configuration."""
    mapping_path = Path(__file__).parent / "data" / "mapping.yaml"
    if mapping_path.exists():
        return load_mapping_config(str(mapping_path))
    return {}


async def generate_rule_content(
    rule_spec: Dict[str, Any],
    project_context: str,
    authoring_spec: str,
    model: str,
) -> Optional[str]:
    """
    Generate MDC rule content using LLM.

    Args:
        rule_spec: Rule specification
        project_context: Project context summary
        authoring_spec: Authoring specification content
        model: LLM model to use

    Returns:
        Generated MDC content or None on error
    """
    try:
        user_prompt = format_thematic_rule_prompt(
            rule_spec=rule_spec,
            project_context=project_context,
            authoring_spec=authoring_spec,
        )

        response = await generate_mdc_response(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model_name=model,
            temperature=0.3,
        )

        # The response is an MDCResponse object with various fields
        # Build the MDC file from it
        mdc_content = build_mdc_from_response(response, rule_spec)
        return mdc_content

    except Exception as e:
        logger.error(f"Error generating rule {rule_spec.get('slug')}: {e}")
        return None


def build_mdc_from_response(response: Any, rule_spec: Dict[str, Any]) -> str:
    """
    Build complete MDC file from LLM response.

    Args:
        response: MDCResponse from LLM
        rule_spec: Original rule specification

    Returns:
        Complete MDC file content with frontmatter
    """
    # Build frontmatter
    frontmatter = ["---"]
    
    # Use description from response or fallback to spec
    description = response.description if hasattr(response, 'description') else rule_spec.get('description', '')
    frontmatter.append(f'description: "{description}"')
    
    # Globs
    globs = rule_spec.get('globs', [])
    if globs:
        globs_json = json.dumps(globs)
        frontmatter.append(f'globs: {globs_json}')
    else:
        frontmatter.append('globs: []')
    
    # alwaysApply based on activation type
    activation = rule_spec.get('activation', 'auto')
    always_apply = activation == 'always'
    frontmatter.append(f'alwaysApply: {"true" if always_apply else "false"}')
    
    # Category
    category = rule_spec.get('category', '99-other')
    frontmatter.append(f'category: "{category}"')
    
    # rule_id (to be filled later)
    frontmatter.append('rule_id: 0  # Will be assigned')
    
    # Tags
    tags = rule_spec.get('tags', [])
    tags_json = json.dumps(tags)
    frontmatter.append(f'tags: {tags_json}')
    
    frontmatter.append("---")
    
    # Build body from response
    body_parts = []
    
    # Add overview if available
    if hasattr(response, 'overview') and response.overview:
        body_parts.append(f"# {rule_spec.get('slug', 'Rule').replace('-', ' ').title()}\n")
        body_parts.append(response.overview)
    
    # Add key points
    if hasattr(response, 'key_points') and response.key_points:
        body_parts.append("\n## Key Points\n")
        for point in response.key_points:
            body_parts.append(f"- {point}")
    
    # Add examples
    if hasattr(response, 'examples') and response.examples:
        body_parts.append("\n## Examples\n")
        body_parts.append(response.examples)
    
    # Add best practices
    if hasattr(response, 'best_practices') and response.best_practices:
        body_parts.append("\n## Best Practices\n")
        for practice in response.best_practices:
            body_parts.append(f"- {practice}")
    
    # If response doesn't have structured fields, use raw content
    if not body_parts and hasattr(response, 'content'):
        body_parts.append(response.content)
    
    # Combine everything
    full_content = "\n".join(frontmatter) + "\n\n" + "\n".join(body_parts) + "\n"
    return full_content


def write_rule_file(
    rules_dir: Path,
    category: str,
    slug: str,
    rule_id: int,
    content: str,
) -> Path:
    """
    Write rule file to appropriate location.

    Args:
        rules_dir: Base .cursor/rules directory
        category: Category slug
        slug: Rule slug
        rule_id: Assigned rule ID
        content: MDC content

    Returns:
        Path to written file
    """
    # Create category directory
    category_dir = rules_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)
    
    # Update rule_id in content
    content = content.replace("rule_id: 0  # Will be assigned", f"rule_id: {rule_id}")
    
    # Write file
    filename = f"{rule_id}-{slug}.mdc"
    file_path = category_dir / filename
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"Created rule: {file_path}")
    return file_path


async def generate_thematic_rules(
    repo_root: str,
    output_dir: str,
    mapping_path: Optional[str],
    spec_path: Optional[str],
    model: str,
    assign_ids: bool,
) -> None:
    """
    Main function to generate thematic rules.

    Args:
        repo_root: Repository root path
        output_dir: Output directory for rules
        mapping_path: Optional custom mapping file
        spec_path: Optional custom authoring spec
        model: LLM model to use
        assign_ids: Whether to assign rule IDs
    """
    # Load configuration
    if mapping_path:
        mapping = load_mapping_config(mapping_path)
    else:
        mapping = load_default_mapping()
    
    if spec_path and os.path.exists(spec_path):
        with open(spec_path, "r", encoding="utf-8") as f:
            authoring_spec = f.read()
    else:
        authoring_spec = load_authoring_spec()
    
    # Initialize planner and detector
    planner = ThematicRulePlanner(repo_root, mapping)
    detector = ProjectDetector(repo_root)
    
    # Get project context
    project_context = planner.get_project_context()
    logger.info(f"Detected project context:\n{project_context}")
    
    # Plan rules
    planned_rules = planner.plan_rules()
    logger.info(f"Planned {len(planned_rules)} thematic rules")
    
    if not planned_rules:
        click.echo("No rules to generate based on project detection.")
        return
    
    # Setup output directory
    if output_dir == ".":
        rules_dir = Path(repo_root) / ".cursor" / "rules"
    else:
        rules_dir = Path(output_dir) / ".cursor" / "rules"
    
    rules_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize ID allocator
    allocator = RuleIDAllocator(
        str(rules_dir),
        custom_ranges=mapping.get("id_ranges")
    ) if assign_ids else None
    
    # Generate rules
    generated_files = []
    
    for rule_spec in planned_rules:
        category = rule_spec.get('category', '99-other')
        slug = rule_spec.get('slug', 'unknown')
        
        click.echo(f"Generating rule: {category}/{slug}...")
        
        # Generate content
        content = await generate_rule_content(
            rule_spec=rule_spec,
            project_context=project_context,
            authoring_spec=authoring_spec,
            model=model,
        )
        
        if not content:
            click.echo(f"  ⚠️  Failed to generate {slug}", err=True)
            continue
        
        # Assign ID if requested
        if assign_ids and allocator:
            try:
                rule_id = allocator.allocate_id(category)
            except ValueError as e:
                click.echo(f"  ⚠️  Could not allocate ID for {slug}: {e}", err=True)
                continue
        else:
            # Use placeholder ID
            rule_id = 0
        
        # Write file
        file_path = write_rule_file(
            rules_dir=rules_dir,
            category=category,
            slug=slug,
            rule_id=rule_id,
            content=content,
        )
        
        generated_files.append(str(file_path.relative_to(rules_dir.parent.parent)))
        click.echo(f"  ✓ Generated: {file_path.relative_to(rules_dir.parent.parent)}")
    
    # Generate INDEX.md
    update_index(rules_dir)
    
    # Summary
    click.echo(f"\n✓ Generated {len(generated_files)} rules in {rules_dir}")
    
    if not assign_ids:
        click.echo("\n⚠️  Note: Rule IDs not assigned (use without --no-assign-ids to assign)")


def update_index(rules_dir: Path) -> None:
    """Update INDEX.md with all rules."""
    from .rule_id_allocator import RuleIDAllocator
    import glob as glob_module
    import re
    
    index_path = rules_dir / "INDEX.md"
    
    # Scan all rules
    rows = []
    pattern = str(rules_dir / "**" / "*.mdc")
    
    rules_info = []
    for path in glob_module.glob(pattern, recursive=True):
        file_path = Path(path)
        filename = file_path.name
        
        # Extract from filename
        match = re.match(r"^(\d+)-([a-z0-9\-]+)\.mdc$", filename)
        if not match:
            continue
        
        rule_id = int(match.group(1))
        slug = match.group(2)
        
        # Read frontmatter
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            category = ""
            description = ""
            
            fm_match = re.search(r"^---\s*(.*?)\s*---", content, re.DOTALL | re.MULTILINE)
            if fm_match:
                block = fm_match.group(1)
                cat_match = re.search(r'category:\s*"(.*?)"', block)
                if cat_match:
                    category = cat_match.group(1)
                desc_match = re.search(r'description:\s*"(.*?)"', block)
                if desc_match:
                    description = desc_match.group(1)
            
            rel_path = file_path.relative_to(rules_dir.parent)
            rules_info.append({
                "rule_id": rule_id,
                "category": category,
                "slug": slug,
                "path": str(rel_path),
                "description": description,
            })
        except Exception as e:
            logger.warning(f"Could not read rule {path}: {e}")
            continue
    
    # Sort by category, then rule_id
    rules_info.sort(key=lambda x: (x["category"], x["rule_id"]))
    
    # Build table
    for info in rules_info:
        row = f"| {info['rule_id']} | {info['category']} | {info['slug']} | `{info['path']}` | {info['description']} |"
        rows.append(row)
    
    index_content = "# Cursor Rules Index\n\n"
    index_content += "| ID | Category | Slug | Path | Description |\n"
    index_content += "|---:|---|---|---|---|\n"
    index_content += "\n".join(rows) + "\n"
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    
    logger.info(f"Updated {index_path}")


@click.command()
@click.option(
    "--repo",
    default=".",
    help="Repository root path to analyze",
)
@click.option(
    "--output-dir",
    default=".",
    help="Output directory for generated rules (default: repo/.cursor/rules)",
)
@click.option(
    "--mapping",
    help="Path to custom mapping.yaml file",
)
@click.option(
    "--spec",
    help="Path to custom rule authoring specification",
)
@click.option(
    "--model",
    default="gpt-4o",
    help="LLM model to use (litellm model ID)",
)
@click.option(
    "--no-assign-ids",
    is_flag=True,
    help="Skip automatic rule ID assignment",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    help="Set the logging level",
)
def cli(repo, output_dir, mapping, spec, model, no_assign_ids, log_level):
    """
    Generate thematic Cursor MDC rules based on project detection.

    This is a thematic rule generator that detects project properties
    (frameworks, tooling, configs) and generates targeted rule-sets
    instead of one rule per file.

    Example usage:

        python -m cursor_mdc_generator.cli_thematic --repo . --output-dir .

        python -m cursor_mdc_generator.cli_thematic \\
            --repo /path/to/project \\
            --mapping custom_mapping.yaml \\
            --model gpt-4o \\
            --output-dir /path/to/output
    """
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Check for LLM API keys
    if (
        not os.environ.get("OPENAI_API_KEY")
        and not os.environ.get("ANTHROPIC_API_KEY")
        and not os.environ.get("GEMINI_API_KEY")
    ):
        click.echo(
            "Error: No LLM API key found in environment variables.\n"
            "Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY.",
            err=True,
        )
        sys.exit(1)

    # Run generation
    try:
        asyncio.run(
            generate_thematic_rules(
                repo_root=os.path.abspath(repo),
                output_dir=os.path.abspath(output_dir),
                mapping_path=mapping,
                spec_path=spec,
                model=model,
                assign_ids=not no_assign_ids,
            )
        )
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n\nError: {e}", err=True)
        logger.exception("Fatal error during generation")
        sys.exit(1)


def main():
    """Entry point for the thematic CLI."""
    cli()


if __name__ == "__main__":
    main()
