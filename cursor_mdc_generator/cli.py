"""
Command-line interface for cursor-mdc-generator.
"""

import click
import os
import asyncio
import logging
from .repo_analyzer import analyze_repository


@click.group()
def cli():
    """Generate MDC files for Cursor IDE from repository analysis."""
    pass


@cli.command()
@click.option(
    "--repo-url",
    "-r",
    help="URL of the repository to analyze.",
)
@click.option(
    "--local-path",
    "-l",
    help="Local path to the repository.",
)
@click.option(
    "--output-dir",
    "-o",
    default="output",
    help="Directory to output the analysis results.",
)
@click.option(
    "--oauth-token",
    help="OAuth token for private repositories.",
)
@click.option(
    "--model-name",
    default="gpt-4o-mini",
    help="OpenAI model to use for generating summaries.",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Set the logging level.",
)
def analyze(repo_url, local_path, output_dir, oauth_token, model_name, log_level):
    """Analyze a repository and generate MDC files.
    
    You must specify either --repo-url or --local-path.
    """
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    if not os.environ.get("OPENAI_API_KEY"):
        click.echo("Error: OPENAI_API_KEY environment variable not set. Required for code summarization.")
        return
    
    if not repo_url and not local_path:
        click.echo("Error: Either --repo-url or --local-path must be specified.")
        return
    
    # Run the analysis
    asyncio.run(
        analyze_repository(
            repo_url=repo_url,
            local_path=local_path,
            output_dir=output_dir,
            oauth_token=oauth_token,
            model_name=model_name,
        )
    )
    click.echo("Analysis complete. Results saved to {}".format(os.path.abspath(output_dir)))


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main() 