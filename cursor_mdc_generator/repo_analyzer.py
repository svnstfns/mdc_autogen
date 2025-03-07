import os
import json
import argparse
import asyncio
import shutil
import traceback
import networkx as nx
import matplotlib.pyplot as plt
import logging


from .repository_structure import get_repo_files, generate_directory_structure
from .symbolic_graph import analyze_imports_and_usage, convert_to_relative_paths
from .code_summarization import read_file_content, split_content, generate_mdc_files
from .visualize_dependency_graph import visualize_dependency_graph, HAS_PYGRAPHVIZ


def generate_report(
    G,
    output_dir,
    repo_url=None,
    local_path=None,
    structure=None,
    visualization_available=True,
):
    with open(os.path.join(output_dir, "repo_analysis_report.md"), "w") as f:
        # Write header
        f.write("# Repository Analysis Report\n\n")

        # Include repo info
        if repo_url:
            f.write("## Repository: %s\n\n" % repo_url)
        else:
            f.write("## Local Repository: %s\n\n" % os.path.abspath(local_path))

        # Include directory structure
        f.write("## Directory Structure\n\n")
        f.write("```\n")
        f.write(structure)
        f.write("\n```\n\n")

        # Include graph summary
        f.write("## Code Dependency Graph\n\n")
        f.write("- Total files analyzed: %d\n" % len(G.nodes()))
        f.write("- Total relationships: %d\n\n" % len(G.edges()))

        # Add reference to the visualization only if it was generated
        if visualization_available and os.path.exists(
            os.path.join(output_dir, "dependency_graph.png")
        ):
            f.write("### Dependency Graph Visualization\n\n")
            f.write("#### Force-Directed Layout\n")
            f.write("![Repository Dependency Graph](./dependency_graph.png)\n\n")
        elif not HAS_PYGRAPHVIZ:
            f.write("### Dependency Graph Visualization\n\n")
            f.write("Visualization was skipped because PyGraphviz is not installed.\n")
            f.write("Install with: `pip install mdcgen[visualization]`\n\n")
        else:
            f.write("### Dependency Graph Visualization\n\n")
            f.write("Visualization was skipped as requested.\n\n")

        # Add more detailed graph analysis for LLM understanding
        f.write("### Most Important Files\n\n")

        # Find most imported files (most depended-upon files)
        if G.nodes():
            # Calculate in-degree (number of files importing this file)
            in_degree = sorted(
                [(n, G.in_degree(n)) for n in G.nodes()],
                key=lambda x: x[1],
                reverse=True,
            )
            f.write("#### Most Imported Files\n\n")
            for node, degree in in_degree[:10]:  # Show top 10
                if degree > 0:
                    f.write("- **%s**: Imported by %d files\n" % (node, degree))
            f.write("\n")

            # Calculate out-degree (number of imports from this file)
            out_degree = sorted(
                [(n, G.out_degree(n)) for n in G.nodes()],
                key=lambda x: x[1],
                reverse=True,
            )
            f.write("#### Files With Most Dependencies\n\n")
            for node, degree in out_degree[:10]:  # Show top 10
                if degree > 0:
                    f.write("- **%s**: Imports %d files\n" % (node, degree))
            f.write("\n")

            # Identify potential core modules (high in-degree)
            core_threshold = 3  # Files imported by at least 3 other files
            core_modules = [n for n, d in in_degree if d >= core_threshold]
            if core_modules:
                f.write("#### Potential Core Modules\n\n")
                f.write(
                    "These files are imported by multiple other files and may represent core functionality:\n\n"
                )
                for module in core_modules:
                    f.write(
                        "- **%s**: Imported by %d files\n"
                        % (module, G.in_degree(module))
                    )
            f.write("\n")

            # Try to identify entry points (files with imports but not imported by others)
            entry_points = [
                n for n in G.nodes() if G.out_degree(n) > 0 and G.in_degree(n) == 0
            ]
            if entry_points:
                f.write("#### Potential Entry Points\n\n")
                f.write(
                    "These files import other modules but are not imported themselves, suggesting they may be entry points:\n\n"
                )
                for entry in entry_points:
                    f.write(
                        "- **%s**: Imports %d files\n" % (entry, G.out_degree(entry))
                    )
            f.write("\n")

            # Identify circular dependencies (potential code smell)
            try:
                cycles = list(nx.simple_cycles(G))
                if cycles:
                    f.write("#### Circular Dependencies ⚠️\n\n")
                    f.write(
                        "The following circular dependencies were detected (these may cause issues):\n\n"
                    )
                    for i, cycle in enumerate(cycles[:10]):  # Show at most 10 cycles
                        cycle_str = " → ".join(cycle)
                        f.write("%d. Cycle: %s → %s\n" % (i + 1, cycle_str, cycle[0]))

                    if len(cycles) > 10:
                        f.write(
                            "\n...and %d more circular dependencies.\n"
                            % (len(cycles) - 10)
                        )
                    f.write("\n")
            except Exception as e:
                logging.error("Error detecting cycles: %s" % e)

            # NEW SECTION: Add granular analysis of imported components
            f.write("### Most Shared Functions, Classes, and Variables\n\n")
            f.write(
                "This section shows individual components (functions, classes, variables) that are imported across multiple files.\n\n"
            )

            # Create a dictionary to track the usage frequency of each component
            component_usage = {}

            # Iterate through edges to identify imported items
            for u, v, data in G.edges(data=True):
                imported_items = data.get("imported_items", [])
                for item in imported_items:
                    name = item.get("name")
                    item_type = item.get("type", "unknown")
                    if name:
                        key = (name, item_type)
                        if key not in component_usage:
                            component_usage[key] = {
                                "count": 0,
                                "source_files": set(),
                                "importing_files": set(),
                            }
                        component_usage[key]["count"] += 1
                        component_usage[key]["source_files"].add(
                            v
                        )  # v is the source of the component
                        component_usage[key]["importing_files"].add(
                            u
                        )  # u is the importing file

            # Sort components by usage frequency
            sorted_components = sorted(
                component_usage.items(),
                key=lambda x: (x[1]["count"], len(x[1]["importing_files"])),
                reverse=True,
            )

            # Display functions
            f.write("#### Most Imported Functions\n\n")
            functions_shown = 0
            for (name, item_type), usage_data in sorted_components:
                if item_type == "function" and functions_shown < 10:
                    source_files = ", ".join(sorted(usage_data["source_files"]))
                    f.write(
                        "- **%s**: Imported %d times from %s\n"
                        % (name, usage_data["count"], source_files)
                    )
                    functions_shown += 1
            if functions_shown == 0:
                f.write("No functions are imported across files.\n")
            f.write("\n")

            # Display classes
            f.write("#### Most Imported Classes\n\n")
            classes_shown = 0
            for (name, item_type), usage_data in sorted_components:
                if item_type == "class" and classes_shown < 10:
                    source_files = ", ".join(sorted(usage_data["source_files"]))
                    f.write(
                        "- **%s**: Imported %d times from %s\n"
                        % (name, usage_data["count"], source_files)
                    )
                    classes_shown += 1
            if classes_shown == 0:
                f.write("No classes are imported across files.\n")
            f.write("\n")

            # Display variables/constants
            f.write("#### Most Imported Variables and Constants\n\n")
            vars_shown = 0
            for (name, item_type), usage_data in sorted_components:
                if item_type in ["variable", "constant"] and vars_shown < 10:
                    source_files = ", ".join(sorted(usage_data["source_files"]))
                    f.write(
                        "- **%s**: Imported %d times from %s\n"
                        % (name, usage_data["count"], source_files)
                    )
                    vars_shown += 1
            if vars_shown == 0:
                f.write("No variables or constants are imported across files.\n")
            f.write("\n")

            # Show cross-file component usage patterns
            heavily_used = [
                k for k, v in component_usage.items() if len(v["importing_files"]) >= 3
            ]
            if heavily_used:
                f.write("#### Components Used Across Multiple Files\n\n")
                f.write(
                    "These components are imported by 3 or more different files and may represent core shared functionality:\n\n"
                )

                for name, item_type in heavily_used[:15]:  # Show top 15
                    usage = component_usage[(name, item_type)]
                    file_count = len(usage["importing_files"])
                    imported_by = ", ".join(sorted(usage["importing_files"]))

                    f.write(
                        "- **%s** (%s): Used in %d files - %s\n"
                        % (name, item_type, file_count, imported_by)
                    )

                if len(heavily_used) > 15:
                    f.write(
                        "\n...and %d more heavily used components.\n"
                        % (len(heavily_used) - 15)
                    )
                f.write("\n")

        f.write(
            "See repo_graph.graphml and repo_graph.json for detailed graph data.\n\n"
        )

        # Add reference to MDC files
        f.write("## MDC Documentation Files\n\n")
        f.write(
            "Cursor-compatible MDC documentation files have been generated in the `.cursor/rules` directory. These files provide context-aware documentation for:\n\n"
        )
        f.write("- Individual files\n")
        f.write("- Directories\n")
        f.write("- The entire repository\n\n")
        f.write(
            "These files include dependency information and are designed to provide contextual help within the Cursor IDE.\n\n"
        )

        logging.info("Analysis report saved to repo_analysis_report.md")


async def analyze_repository(
    repo_url=None,
    local_path=None,
    output_dir="output",
    oauth_token=None,
    include_import_rules=False,
    skip_visualization=False,
    model_name="gpt-4o-mini",
    skip_directory_mdcs=False,
    skip_repository_mdc=False,
    max_directory_depth=2,
):
    """
    Analyze a repository and generate structure, graph, and summaries.

    Supports Python, JavaScript, and TypeScript files. Python files will have
    detailed AST-based analysis of functions, classes, and dependencies, while
    JavaScript and TypeScript files are included with basic information.

    Args:
        repo_url: GitHub repository URL (optional if local_path is provided)
        local_path: Local path to repository (optional if repo_url is provided)
        output_dir: Directory to save output files
        oauth_token: OAuth token for private repositories
        include_import_rules: Whether to include @file references to imported files
        skip_visualization: Whether to skip generating visualizations (useful if pygraphviz is not installed)
        model_name: Model to use for generating summaries
        skip_directory_mdcs: Whether to skip generating directory-level MDC files
        skip_repository_mdc: Whether to skip generating repository-level MDC file
        max_directory_depth: Maximum directory depth for generating MDC files (0=repo only, 1=top-level dirs, etc.)
    """
    # Set default local path if not provided
    if not local_path:
        local_path = "./temp_repo"
        should_cleanup = True
    else:
        # If using an existing local repo, don't clean it up
        should_cleanup = False

    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Get repository files and ignore patterns
        logging.info("Collecting repository files...")
        relevant_files = get_repo_files(repo_url, local_path, oauth_token)
        logging.info("Found %d relevant files" % len(relevant_files))

        # Step 2: Generate directory structure
        logging.info("Generating directory structure visualization...")
        structure = generate_directory_structure(local_path)
        with open(os.path.join(output_dir, "directory_structure.txt"), "w") as f:
            f.write(structure)
        logging.info(
            "Directory structure visualization saved to directory_structure.txt"
        )

        # Step 3: Create symbolic graph
        logging.info("Analyzing code structure and dependencies...")
        G = nx.DiGraph()
        for file_path in relevant_files:
            full_path = os.path.join(local_path, file_path)
            analyze_imports_and_usage(full_path, local_path, G)

        # Convert absolute paths to relative paths for the final graph
        logging.info("Converting absolute paths to relative paths...")
        G_rel = convert_to_relative_paths(G, local_path)

        # Save dependency graph
        logging.info("Saving dependency graph...")
        nx.write_gexf(G_rel, os.path.join(output_dir, "dependency_graph.gexf"))

        # Step 4: Save the graph data
        logging.info("Saving dependency graph data...")
        graph_data = {"nodes": [], "edges": []}

        # Add node data
        for node in G_rel.nodes():
            node_data = {"id": node, "type": G_rel.nodes[node].get("type", "unknown")}
            graph_data["nodes"].append(node_data)

        # Add edge data
        for u, v, data in G_rel.edges(data=True):
            edge_data = {
                "source": u,
                "target": v,
                "type": data.get("type", "unknown"),
                "imported_items": data.get("imported_items", []),
            }
            graph_data["edges"].append(edge_data)

        # Save graph data as JSON
        with open(os.path.join(output_dir, "repo_graph.json"), "w") as f:
            json.dump(graph_data, f, indent=2)

        # Step 5: Generate visualization (if not skipped)
        if not skip_visualization:
            try:
                logging.info("Generating dependency graph visualization...")
                visualize_dependency_graph(
                    G_rel, os.path.join(output_dir, "dependency_graph.png")
                )
            except Exception as e:
                logging.warning(
                    "Visualization failed: %s. Try installing with 'pip install mdcgen[visualization]'"
                    % e
                )
        else:
            logging.info("Skipping visualization as requested")

        # Step 6: Split files and prepare for MDC generation
        logging.info("Splitting files into functions and classes...")
        file_data = {}
        for file_path in relevant_files:
            full_path = os.path.join(local_path, file_path)
            try:
                content = read_file_content(full_path)
                if content:
                    file_data[file_path] = split_content(content, file_path)
                else:
                    logging.error("Error reading file: %s" % file_path)
            except Exception as e:
                logging.error("Error processing file: %s. Error: %s" % (file_path, e))

        # Step 7: Generate MDC files with dependency information
        logging.info("Generating MDC documentation files...")
        mdc_output_dir = os.path.join(local_path, ".cursor/rules")
        os.makedirs(mdc_output_dir, exist_ok=True)
        mdc_files = await generate_mdc_files(
            file_data,
            G_rel,
            mdc_output_dir,
            model_name=model_name,
            include_import_rules=include_import_rules,
            skip_directory_mdcs=skip_directory_mdcs,
            skip_repository_mdc=skip_repository_mdc,
            max_directory_depth=max_directory_depth,
        )

        # Log information about generated MDC files
        file_mdcs = sum(
            1
            for f in mdc_files
            if not f.endswith("_directory.mdc") and not f.endswith("_repository.mdc")
        )
        dir_mdcs = sum(1 for f in mdc_files if f.endswith("_directory.mdc"))
        repo_mdcs = sum(1 for f in mdc_files if f.endswith("_repository.mdc"))

        logging.info(
            f"Generated {len(mdc_files)} MDC documentation files in {mdc_output_dir}:"
        )
        logging.info(f"  - {file_mdcs} file-level MDCs")
        logging.info(f"  - {dir_mdcs} directory-level MDCs")
        logging.info(f"  - {repo_mdcs} repository-level MDCs")

        # Step 8: Generate a report
        visualization_available = not skip_visualization and (
            HAS_PYGRAPHVIZ or True
        )  # True for fallback layouts
        logging.info("Creating combined analysis report...")
        generate_report(
            G_rel, output_dir, repo_url, local_path, structure, visualization_available
        )
        return os.path.abspath(output_dir)

    except Exception as e:
        logging.error("Error analyzing repository: %s" % e)
        traceback.print_exc()
        return None
    finally:
        # Clean up: remove the temporary repository only if we created it
        if should_cleanup:
            logging.info("Cleaning up temporary files...")
            shutil.rmtree(local_path, ignore_errors=True)


def main():
    """Main function to parse arguments and run the analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze a repository with support for Python, JavaScript, and TypeScript"
    )
    parser.add_argument(
        "--repo",
        "-r",
        dest="repo_url",
        help="GitHub repository URL (optional if --local is provided)",
    )
    parser.add_argument(
        "--local",
        "-l",
        dest="local_path",
        help="Local path to repository (optional if --repo is provided)",
    )
    parser.add_argument(
        "--out",
        "-o",
        dest="output_dir",
        default="mdc_output",
        help="Output directory for analysis files",
    )
    parser.add_argument(
        "--model", "-m", default="gpt-4o-mini", help="OpenAI model to use for summaries"
    )
    parser.add_argument(
        "--token", "-t", dest="oauth_token", help="OAuth token for private repositories"
    )
    parser.add_argument(
        "--imports",
        "-i",
        dest="include_import_rules",
        action="store_true",
        help="Include @file references to imported files",
    )
    parser.add_argument(
        "--no-viz",
        dest="skip_visualization",
        action="store_true",
        help="Skip generating dependency graph visualizations",
    )
    parser.add_argument(
        "--no-dirs",
        dest="skip_directory_mdcs",
        action="store_true",
        help="Skip generating directory-level MDC files",
    )
    parser.add_argument(
        "--no-repo",
        dest="skip_repository_mdc",
        action="store_true",
        help="Skip generating repository-level MDC file",
    )
    parser.add_argument(
        "--depth",
        "-d",
        dest="max_directory_depth",
        type=int,
        default=2,
        help="Max directory depth (0=repo only, 1=top-level dirs)",
    )
    args = parser.parse_args()

    # Validate arguments
    if not args.repo_url and not args.local_path:
        logging.error("Error: Either --repo or --local must be provided")
        return

    # Set the OpenAI API key from environment
    if not os.environ.get("OPENAI_API_KEY"):
        logging.error(
            "Error: OPENAI_API_KEY environment variable not set. Required for code summarization."
        )
        return

    # Run the analysis
    output_path = asyncio.run(
        analyze_repository(
            repo_url=args.repo_url,
            local_path=args.local_path,
            output_dir=args.output_dir,
            oauth_token=args.oauth_token,
            include_import_rules=args.include_import_rules,
            skip_visualization=args.skip_visualization,
            model_name=args.model,
            skip_directory_mdcs=args.skip_directory_mdcs,
            skip_repository_mdc=args.skip_repository_mdc,
            max_directory_depth=args.max_directory_depth,
        )
    )

    if output_path:
        logging.info("Repository analysis complete! Results saved to %s" % output_path)
    else:
        logging.error("Repository analysis failed.")


if __name__ == "__main__":
    main()
