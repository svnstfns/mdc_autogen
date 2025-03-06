#!/usr/bin/env python3
"""
Documentation Generator

This script generates comprehensive documentation for a repository by first
analyzing the codebase and then creating structured .mdc files for Cursor IDE.
"""

import os
import argparse
import logging
import subprocess
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


async def run_repo_analyzer(repo_path, output_dir, model="gpt-4o-mini"):
    """
    Run the repository analyzer to generate code summaries.
    
    Args:
        repo_path: Path to the repository
        output_dir: Directory to store analysis output
        model: OpenAI model to use
    
    Returns:
        Path to the generated summaries file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"summaries_{timestamp}.json")
    
    logging.info(f"Analyzing repository at {repo_path}")
    
    # Build command to run repo_analyzer.py
    cmd = [
        "python", "repo_analyzer.py",
        "--local_path", repo_path,
        "--output_file", output_file,
        "--model", model
    ]
    
    # Run the command
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        logging.info(f"Repository analysis complete: {result.stdout}")
        return output_file
    except subprocess.CalledProcessError as e:
        logging.error(f"Error analyzing repository: {e.stderr}")
        raise


async def generate_mdc_files(repo_path, summaries_file, output_dir, model):
    """
    Generate MDC files from repository analysis.
    
    Args:
        repo_path: Path to the repository
        summaries_file: Path to the summaries JSON file
        output_dir: Output directory for MDC files
        model: OpenAI model to use
    """
    logging.info(f"Generating MDC files from {summaries_file}")
    
    # Build command to run generate_mdc_files.py
    cmd = [
        "python", "generate_mdc_files.py",
        "--repo_path", repo_path,
        "--summaries_file", summaries_file,
        "--output_dir", output_dir,
        "--model", model
    ]
    
    # Run the command
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        logging.info(f"MDC file generation complete: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error generating MDC files: {e.stderr}")
        raise


async def main():
    """Main function to run the documentation generation process."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive documentation for a repository"
    )
    parser.add_argument(
        "--repo_path", 
        required=True, 
        help="Path to the repository"
    )
    parser.add_argument(
        "--output_dir", 
        default=".cursor/rules", 
        help="Output directory for documentation files"
    )
    parser.add_argument(
        "--analysis_dir", 
        default="analysis_output",
        help="Directory to store analysis output"
    )
    parser.add_argument(
        "--model", 
        default="gpt-4o-mini",
        help="OpenAI model to use for generation"
    )
    args = parser.parse_args()
    
    # Set the OpenAI API key from environment
    if not os.environ.get("OPENAI_API_KEY"):
        logging.error("Error: OPENAI_API_KEY environment variable not set.")
        return
    
    # Create output directories
    os.makedirs(args.analysis_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Step 1: Run repository analyzer
        summaries_file = await run_repo_analyzer(
            args.repo_path, args.analysis_dir, args.model
        )
        
        # Step 2: Generate MDC files
        await generate_mdc_files(
            args.repo_path, summaries_file, args.output_dir, args.model
        )
        
        msg = "Documentation generation complete!"
        msg += f" Files saved to {args.output_dir}"
        logging.info(msg)
    except Exception as e:
        logging.error(f"Error in documentation generation: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main()) 