"""
Command-line interface for cursor-mdc-generator.
"""

import click
import os
import asyncio
import logging
from .repo_analyzer import analyze_repository
from .llm_utils.auth import get_key_manager
from .logging_utils import setup_colored_logging


@click.command()
@click.argument("path", default=".", type=click.Path(exists=True), required=False)
@click.option(
    "--repo",
    "-r",
    help="URL of the repository to analyze (instead of local path).",
)
@click.option(
    "--out",
    "-o",
    default="mdc_output",
    help="Directory to output the analysis results.",
)
@click.option(
    "--token",
    "-t",
    help="OAuth token for private repositories.",
)
@click.option(
    "--model",
    "-m",
    default="gpt-4o-mini",
    help="OpenAI model to use for generating summaries.",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    help="Set the logging level.",
)
@click.option(
    "--imports",
    "-i",
    is_flag=True,
    help="Include @file references to imported files.",
)
@click.option(
    "--no-viz",
    is_flag=True,
    help="Skip generating dependency graph visualizations.",
)
@click.option(
    "--no-dirs",
    is_flag=True,
    help="Skip generating directory-level MDC files.",
)
@click.option(
    "--no-repo",
    is_flag=True,
    help="Skip generating repository-level MDC file.",
)
@click.option(
    "--depth",
    "-d",
    type=int,
    default=2,
    help="Max directory depth (0=repo only, 1=top-level dirs).",
)
@click.option(
    "--check-quality",
    is_flag=True,
    help="Check quality of existing MDC files before generating new ones.",
)
@click.option(
    "--update-poor-quality",
    is_flag=True,
    help="Only update MDC files with poor quality (implies --check-quality).",
)
def cli(
    path, repo, out, token, model, log_level, imports, no_viz, no_dirs, no_repo, depth, check_quality, update_poor_quality
):
    """Generate MDC files for Cursor IDE from repository analysis.
    
    PATH is the local repository path to analyze (defaults to current directory).
    
    Alternatively, use --repo to analyze a remote repository.
    """
    # Set up logging with colors
    setup_colored_logging(log_level)

    # Check if any API keys are available through the key manager
    key_manager = get_key_manager()
    if not key_manager.has_any_key():
        click.echo(
            "Error: No LLM API keys found. Required for code summarization.\n"
            "You can provide keys using:\n"
            "  1. Environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, or DEEPSEEK_API_KEY\n"
            "  2. OIDC authentication: Set OIDC_TOKEN_ENDPOINT, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, and OIDC_KEY_ENDPOINT\n"
            "  3. Service Account: Set SERVICE_ACCOUNT_FILE and SERVICE_ACCOUNT_KEY_ENDPOINT\n"
            "  4. FastAPI service: Set FASTAPI_KEY_ENDPOINT (and optionally FASTAPI_API_KEY)"
        )
        return

    local_path = path
    if repo:
        local_path = None  # If repo URL is provided, don't use local path
    
    # If update_poor_quality is set, enable check_quality automatically
    if update_poor_quality:
        check_quality = True

    # Run the analysis
    asyncio.run(
        analyze_repository(
            repo_url=repo,
            local_path=local_path,
            output_dir=out,
            oauth_token=token,
            model_name=model,
            include_import_rules=imports,
            skip_visualization=no_viz,
            skip_directory_mdcs=no_dirs,
            skip_repository_mdc=no_repo,
            max_directory_depth=depth,
            check_quality=check_quality,
            update_poor_quality=update_poor_quality,
        )
    )
    click.echo("Analysis complete. Results saved to {}".format(os.path.abspath(out)))


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
