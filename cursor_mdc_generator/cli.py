"""
Command-line interface for cursor-mdc-generator.
"""

import click
import os
import asyncio
import logging
from .repo_analyzer import analyze_repository


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
def cli(
    path, repo, out, token, model, log_level, imports, no_viz, no_dirs, no_repo, depth
):
    """Generate MDC files for Cursor IDE from repository analysis.
    
    PATH is the local repository path to analyze (defaults to current directory).
    
    Alternatively, use --repo to analyze a remote repository.
    """
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if (
        not os.environ.get("OPENAI_API_KEY")
        and not os.environ.get("ANTHROPIC_API_KEY")
        and not os.environ.get("GEMINI_API_KEY")
    ):
        click.echo(
            "Error: LLM key environment variable not set. Required for code summarization. Ideally use OpenAI, Anthropic or Gemini (via LiteLLM)"
        )
        return

    local_path = path
    if repo:
        local_path = None  # If repo URL is provided, don't use local path

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
        )
    )
    click.echo("Analysis complete. Results saved to {}".format(os.path.abspath(out)))


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
