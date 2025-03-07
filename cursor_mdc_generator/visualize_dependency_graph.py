from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt
import networkx as nx
import os
import logging
import traceback
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from collections import defaultdict

# Try to import pygraphviz, but make it optional
try:
    import pygraphviz
    HAS_PYGRAPHVIZ = True
except ImportError:
    HAS_PYGRAPHVIZ = False
    logging.warning("pygraphviz not available, falling back to spring layout for visualizations")

def format_imported_items(items):
    """Format the imported items for display on edges."""
    if not items or len(items) > 5:  # If too many items, show count only
        return "{} items".format(len(items)) if items else ""
    
    formatted = []
    for item in items:
        name = item.get('name', '')
        alias = item.get('alias')
        item_type = item.get('type', '')
        
        if name == '*':
            formatted.append('*')
        elif alias:
            formatted.append("{} as {}".format(name, alias))
        else:
            formatted.append(name)
    
    return ", ".join(formatted)

def get_directory_from_path(path):
    """Extract the top-level directory from a path."""
    parts = path.split(os.sep)
    return parts[0] if parts else ""

def create_subgraphs(G):
    """Create subgraphs based on directory structure or connected components."""
    # Method 1: Directory-based subgraphs
    dir_subgraphs = defaultdict(set)
    for node in G.nodes():
        top_dir = get_directory_from_path(node)
        if top_dir:
            dir_subgraphs[top_dir].add(node)
    
    # If directory-based subgraphs are too small or too big, 
    # use connected components instead
    dir_graphs = []
    for directory, nodes in dir_subgraphs.items():
        if len(nodes) > 2:  # Only create subgraphs with at least 3 nodes
            subgraph = G.subgraph(nodes)
            dir_graphs.append((directory, subgraph))
    
    # Method 2: Connected components-based subgraphs
    # Use if directory-based approach produces too many small subgraphs
    if len(dir_graphs) > 10 or all(len(subg.nodes()) < 5 for _, subg in dir_graphs):
        comp_graphs = []
        # Use undirected version of the graph to find connected components
        undirected_G = G.to_undirected()
        for i, comp in enumerate(nx.connected_components(undirected_G)):
            if len(comp) > 2:  # Only create subgraphs with at least 3 nodes
                subgraph = G.subgraph(comp)
                comp_graphs.append(("Component {}".format(i+1), subgraph))
        return comp_graphs
    
    return dir_graphs

def visualize_dependency_graph(G, output_path):
    """
    Create visual representations of the dependency graph, with separate images for subgraphs.
    
    Args:
        G: NetworkX graph object representing the dependency graph
        output_path: Base path to save the visualizations
    """
    try:
        # Create a simplified graph for visualization
        vis_graph = nx.DiGraph()
        
        # Only include Python, JavaScript, and TypeScript files to reduce complexity
        for node in G.nodes():
            if node.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')):
                vis_graph.add_node(node)
        
        # Add edges between nodes that exist in the visual graph
        for u, v in G.edges():
            if u in vis_graph and v in vis_graph:
                vis_graph.add_edge(u, v)
        
        # If the graph is empty, add a message node
        if len(vis_graph) == 0:
            logging.warning("No Python/JavaScript/TypeScript files found to visualize")
            return
        
        # Get file coloring function for consistent colors
        def get_node_color(node):
            if node.endswith('.py'):
                return 'skyblue'
            elif node.endswith(('.js', '.jsx')):
                return 'lightgreen'
            elif node.endswith(('.ts', '.tsx')):
                return 'lightcoral'
            else:
                return 'lightgray'
        
        # Create legend elements
        legend_elements = [
            mpatches.Patch(color='skyblue', label='Python'),
            mpatches.Patch(color='lightgreen', label='JavaScript'),
            mpatches.Patch(color='lightcoral', label='TypeScript')
        ]
        
        # First create the overall graph (compact version)
        output_dir = os.path.dirname(output_path)
        base_filename = os.path.basename(output_path)
        name_without_ext = os.path.splitext(base_filename)[0]
        
        plt.figure(figsize=(12, 10))
        # Choose layout based on available packages
        if HAS_PYGRAPHVIZ:
            try:
                pos = graphviz_layout(vis_graph, prog='neato')  # 'neato' for cleaner overall view
            except Exception as e:
                logging.warning("Graphviz layout failed: %s" % e)
                pos = nx.spring_layout(vis_graph, seed=42)
        else:
            pos = nx.spring_layout(vis_graph, seed=42)
        
        # Draw the overall graph
        node_colors = [get_node_color(node) for node in vis_graph.nodes()]
        nx.draw(
            vis_graph, 
            pos, 
            with_labels=True, 
            node_color=node_colors,
            node_size=1200, 
            font_size=8,
            edge_color='gray',
            arrows=True,
            arrowsize=10,
            arrowstyle='-|>',
            connectionstyle='arc3,rad=0.1'
        )
        plt.legend(handles=legend_elements, loc='upper right')
        plt.title('Repository Dependency Graph (Overview)', size=16)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create directory for subgraph images if it doesn't exist
        subgraphs_dir = os.path.join(output_dir, name_without_ext + "_subgraphs")
        os.makedirs(subgraphs_dir, exist_ok=True)
        
        # Get subgraphs based on directory structure or components
        subgraphs = create_subgraphs(vis_graph)
        
        # Create separate visualizations for each subgraph
        for i, (subgraph_name, subgraph) in enumerate(subgraphs):
            if len(subgraph) < 2:  # Skip very small subgraphs
                continue
                
            # Create a file name based on the subgraph name
            safe_name = ''.join(c if c.isalnum() else '_' for c in subgraph_name)
            subgraph_path = os.path.join(subgraphs_dir, "%02d_%s.png" % (i+1, safe_name))
            
            plt.figure(figsize=(10, 8))
            
            # Layout for this specific subgraph
            if HAS_PYGRAPHVIZ:
                try:
                    sg_pos = graphviz_layout(subgraph, prog='dot')  # 'dot' for hierarchical subgraphs
                except Exception as e:
                    logging.warning("Graphviz layout failed for subgraph %s: %s" % (subgraph_name, e))
                    sg_pos = nx.spring_layout(subgraph, seed=42)
            else:
                sg_pos = nx.spring_layout(subgraph, seed=42)
            
            # Draw the subgraph
            nx.draw(
                subgraph, 
                sg_pos, 
                with_labels=True, 
                node_color=[get_node_color(node) for node in subgraph.nodes()],
                node_size=1800,  # Larger nodes for better readability in subgraphs
                font_size=10,    # Larger font for better readability in subgraphs
                edge_color='gray',
                arrows=True,
                arrowsize=15,
                arrowstyle='-|>',
                connectionstyle='arc3,rad=0.1'
            )
            
            # Draw edge labels if there are not too many edges
            if len(subgraph.edges()) <= 10:
                edge_labels = {}
                for u, v in subgraph.edges():
                    imported_items = G.edges.get((u, v), {}).get('imported_items', [])
                    label = format_imported_items(imported_items)
                    if label:
                        edge_labels[(u, v)] = label
                
                if edge_labels:
                    nx.draw_networkx_edge_labels(
                        subgraph, 
                        sg_pos, 
                        edge_labels=edge_labels,
                        font_size=8
                    )
            
            plt.legend(handles=legend_elements, loc='upper right')
            plt.title('Subgraph: %s (%d files)' % (subgraph_name, len(subgraph)), size=14)
            plt.tight_layout()
            plt.savefig(subgraph_path, dpi=300, bbox_inches='tight')
            plt.close()
        
        # Create an index HTML file for easy navigation
        index_path = os.path.join(subgraphs_dir, "index.html")
        with open(index_path, 'w') as f:
            f.write("<!DOCTYPE html>\n<html>\n<head>\n")
            f.write("<title>Repository Dependency Subgraphs</title>\n")
            f.write("<style>body{font-family:Arial,sans-serif;margin:20px;line-height:1.6}")
            f.write("h1,h2{color:#333}img{max-width:100%;height:auto;border:1px solid #ddd;}")
            f.write("hr{margin:30px 0;border:0;border-top:1px solid #ddd}")
            f.write("</style>\n</head>\n<body>\n")
            f.write("<h1>Repository Dependency Graph Analysis</h1>\n")
            
            # Link to overall graph
            f.write("<h2>Overall Dependency Graph</h2>\n")
            f.write("<p><a href='../%s' target='_blank'>" % base_filename)
            f.write("<img src='../%s' alt='Overall Graph' style='max-width:800px;'></a></p>\n" % base_filename)
            
            # Add links to all subgraphs
            f.write("<h2>Subgraphs by Component</h2>\n")
            if subgraphs:
                for i, (subgraph_name, subgraph) in enumerate(subgraphs):
                    if len(subgraph) < 2:  # Skip very small subgraphs
                        continue
                    safe_name = ''.join(c if c.isalnum() else '_' for c in subgraph_name)
                    subgraph_filename = "%02d_%s.png" % (i+1, safe_name)
                    
                    f.write("<hr>\n<h3>%d. %s (%d files)</h3>\n" % (i+1, subgraph_name, len(subgraph)))
                    f.write("<p><a href='%s' target='_blank'>" % subgraph_filename)
                    f.write("<img src='%s' alt='%s' style='max-width:800px;'></a></p>\n" % (subgraph_filename, subgraph_name))
                    
                    # List files in this subgraph
                    f.write("<p><strong>Files in this subgraph:</strong></p>\n<ul>\n")
                    for node in sorted(subgraph.nodes()):
                        f.write("<li>%s</li>\n" % node)
                    f.write("</ul>\n")
            else:
                f.write("<p>No significant subgraphs found.</p>\n")
            
            f.write("</body>\n</html>")
        
        logging.info("Dependency graph visualization saved to %s" % output_path)
        logging.info("Subgraph visualizations saved to %s" % subgraphs_dir)
        logging.info("HTML index created at %s" % index_path)
    
    except Exception as e:
        logging.error("Error visualizing dependency graph: %s" % e)
        traceback.print_exc()

