import os
import json
import argparse
import asyncio
import shutil
import traceback
import networkx as nx
import matplotlib.pyplot as plt
import logging
from networkx.drawing.nx_agraph import graphviz_layout

from repository_structure import get_repo_files, generate_directory_structure
from symbolic_graph import analyze_imports_and_usage
from code_summarization import read_file_content, split_content, generate_mdc_files


def visualize_dependency_graph(G, output_path):
    """Create a visual representation of the dependency graph."""
    try:
        # Create two visualizations: one with spring layout and one hierarchical (if possible)
        # 1. Spring layout (force-directed) - good for general visualization
        plt.figure(figsize=(12, 8))
        
        # Use spring layout for graph visualization
        pos = nx.spring_layout(G, k=0.3, iterations=50)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_size=300, node_color='skyblue', alpha=0.8)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, width=0.7, alpha=0.6, arrows=True, arrowsize=10)
        
        # Draw labels with smaller font size and without full paths for readability
        labels = {node: os.path.basename(node) for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=7)
        
        plt.title("Repository Dependency Graph (Force-Directed Layout)")
        plt.axis('off')
        plt.tight_layout()
        
        # Save the spring layout figure
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Try to create a hierarchical layout if the graph is a DAG
        try:
            # Check if the graph is a DAG (no cycles)
            if nx.is_directed_acyclic_graph(G) and len(G.nodes()) > 1:
                plt.figure(figsize=(12, 10))
                
                # Use hierarchical layout
                pos = graphviz_layout(G, prog='dot')

                # Draw nodes
                nx.draw_networkx_nodes(G, pos, node_size=300, node_color='lightgreen', alpha=0.8)
                
                # Draw edges
                nx.draw_networkx_edges(G, pos, width=0.7, alpha=0.6, arrows=True, arrowsize=10)
                
                # Draw labels
                nx.draw_networkx_labels(G, pos, labels=labels, font_size=7)
                
                plt.title("Repository Dependency Graph (Hierarchical Layout)")
                plt.axis('off')
                plt.tight_layout()
                
                # Save the hierarchical layout figure
                hierarchical_path = os.path.splitext(output_path)[0] + "_hierarchical.png"
                plt.savefig(hierarchical_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                logging.info("Hierarchical dependency graph saved to %s" % hierarchical_path)
        except Exception as e:
            logging.warning("Could not create hierarchical layout: %s" % e)
        
        logging.info("Dependency graph visualization saved to %s" % output_path)
    except Exception as e:
        logging.error("Error creating graph visualization: %s" % e)
        traceback.print_exc()


async def analyze_repository(repo_url=None, local_path=None, output_dir="output", oauth_token=None):
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
    """
    # Set default local path if not provided
    if not local_path:
        local_path = './temp_repo'
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
        with open(os.path.join(output_dir, "directory_structure.txt"), 'w') as f:
            f.write(structure)
        logging.info("Directory structure visualization saved to directory_structure.txt")
        
        # Step 3: Create symbolic graph
        logging.info("Analyzing code structure and dependencies...")
        G = nx.DiGraph()
        for file_path in relevant_files:
            full_path = os.path.join(local_path, file_path)
            analyze_imports_and_usage(full_path, local_path, G)

        # Step 4: Split files and prepare for MDC generation
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

        # Save the graph data
        logging.info("Saving dependency graph data...")
        try:
            # Save in GraphML format (readable by tools like Gephi)
            nx.write_graphml(G, os.path.join(output_dir, "repo_graph.graphml"))
            
            # For JSON format, convert to a serializable format
            graph_data = {
                "nodes": [{"id": n, "type": G.nodes[n].get("type", "unknown")} for n in G.nodes()],
                "edges": [{"source": u, "target": v, "type": G.edges[u, v].get("type", "unknown")} 
                          for u, v in G.edges()]
            }
            with open(os.path.join(output_dir, "repo_graph.json"), 'w') as f:
                json.dump(graph_data, f, indent=2)
                
            # Generate visual representation of the graph
            visualize_dependency_graph(G, os.path.join(output_dir, "repo_graph.png"))
                
            logging.info("Dependency graph saved with %d nodes and %d edges" % (len(G.nodes()), len(G.edges())))
        except Exception as e:
            logging.error("Error saving dependency graph: %s" % e)
        
        # Step 5: Generate MDC files with dependency information
        logging.info("Generating MDC documentation files...")
        mdc_output_dir = os.path.join(output_dir, ".cursor/rules")
        mdc_files = await generate_mdc_files(file_data, G, mdc_output_dir)
        logging.info("Generated %d MDC documentation files" % len(mdc_files))
        
        # Create a combined report
        logging.info("Creating combined analysis report...")
        with open(os.path.join(output_dir, "repo_analysis_report.md"), 'w') as f:
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
            
            # Add reference to the visualization
            f.write("### Dependency Graph Visualization\n\n")
            f.write("#### Force-Directed Layout\n")
            f.write("![Repository Dependency Graph](./repo_graph.png)\n\n")
            
            # Add reference to hierarchical layout if it exists
            hierarchical_path = os.path.join(output_dir, "repo_graph_hierarchical.png")
            if os.path.exists(hierarchical_path):
                f.write("#### Hierarchical Layout\n")
                f.write("This layout shows the dependency direction more clearly, with upstream dependencies at the top and downstream dependencies at the bottom.\n\n")
                f.write("![Repository Hierarchical Dependency Graph](./repo_graph_hierarchical.png)\n\n")
            
            # Add more detailed graph analysis for LLM understanding
            f.write("### Most Important Files\n\n")
            
            # Find most imported files (most depended-upon files)
            if G.nodes():
                # Calculate in-degree (number of files importing this file)
                in_degree = sorted([(n, G.in_degree(n)) for n in G.nodes()], key=lambda x: x[1], reverse=True)
                f.write("#### Most Imported Files\n\n")
                for node, degree in in_degree[:10]:  # Show top 10
                    if degree > 0:
                        f.write("- **%s**: Imported by %d files\n" % (node, degree))
                f.write("\n")
                
                # Calculate out-degree (number of imports from this file)
                out_degree = sorted([(n, G.out_degree(n)) for n in G.nodes()], key=lambda x: x[1], reverse=True)
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
                    f.write("These files are imported by multiple other files and may represent core functionality:\n\n")
                    for module in core_modules:
                        f.write("- **%s**: Imported by %d files\n" % (module, G.in_degree(module)))
                f.write("\n")
                
                # Try to identify entry points (files with imports but not imported by others)
                entry_points = [n for n in G.nodes() if G.out_degree(n) > 0 and G.in_degree(n) == 0]
                if entry_points:
                    f.write("#### Potential Entry Points\n\n")
                    f.write("These files import other modules but are not imported themselves, suggesting they may be entry points:\n\n")
                    for entry in entry_points:
                        f.write("- **%s**: Imports %d files\n" % (entry, G.out_degree(entry)))
                f.write("\n")
                
                # Identify circular dependencies (potential code smell)
                try:
                    cycles = list(nx.simple_cycles(G))
                    if cycles:
                        f.write("#### Circular Dependencies ⚠️\n\n")
                        f.write("The following circular dependencies were detected (these may cause issues):\n\n")
                        for i, cycle in enumerate(cycles[:10]):  # Show at most 10 cycles
                            cycle_str = " → ".join(cycle)
                            f.write("%d. Cycle: %s → %s\n" % (i+1, cycle_str, cycle[0]))
                        
                        if len(cycles) > 10:
                            f.write("\n...and %d more circular dependencies.\n" % (len(cycles) - 10))
                        f.write("\n")
                except Exception as e:
                    logging.error("Error detecting cycles: %s" % e)
            
            f.write("See repo_graph.graphml and repo_graph.json for detailed graph data.\n\n")
            
            # Add reference to MDC files
            f.write("## MDC Documentation Files\n\n")
            f.write("Cursor-compatible MDC documentation files have been generated in the `.cursor/rules` directory. These files provide context-aware documentation for:\n\n")
            f.write("- Individual files\n")
            f.write("- Directories\n")
            f.write("- The entire repository\n\n")
            f.write("These files include dependency information and are designed to provide contextual help within the Cursor IDE.\n\n")
            
            logging.info("Analysis report saved to repo_analysis_report.md")
        
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
    parser = argparse.ArgumentParser(description="Analyze a repository with support for Python, JavaScript, and TypeScript")
    parser.add_argument("--repo_url", help="GitHub repository URL (optional if --local_path is provided)")
    parser.add_argument("--local_path", help="Local path to repository (optional if --repo_url is provided)")
    parser.add_argument("--output_dir", default="output", help="Output directory for analysis files")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use for summaries")
    parser.add_argument("--oauth_token", help="OAuth token for private repositories")
    args = parser.parse_args()
    
    # Validate arguments
    if not args.repo_url and not args.local_path:
        logging.error("Error: Either --repo_url or --local_path must be provided")
        return
    
    # Set the OpenAI API key from environment
    if not os.environ.get("OPENAI_API_KEY"):
        logging.error("Error: OPENAI_API_KEY environment variable not set. Required for code summarization.")
        return

    # Run the analysis
    output_path = asyncio.run(analyze_repository(
        repo_url=args.repo_url,
        local_path=args.local_path,
        output_dir=args.output_dir,
        oauth_token=args.oauth_token
    ))
    
    if output_path:
        logging.info("Repository analysis complete! Results saved to %s" % output_path)
    else:
        logging.error("Repository analysis failed.")


if __name__ == "__main__":
    main()
