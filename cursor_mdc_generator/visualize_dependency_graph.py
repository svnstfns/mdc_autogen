from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt
import networkx as nx
import os
import logging
import traceback
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from collections import defaultdict
import json

# Try to import pygraphviz, but make it optional
try:
    import pygraphviz

    HAS_PYGRAPHVIZ = True
except ImportError:
    HAS_PYGRAPHVIZ = False
    logging.warning(
        "pygraphviz not available, falling back to spring layout for visualizations"
    )


def format_imported_items(items):
    """Format the imported items for display on edges."""
    if not items or len(items) > 5:  # If too many items, show count only
        return "{} items".format(len(items)) if items else ""

    formatted = []
    for item in items:
        name = item.get("name", "")
        alias = item.get("alias")
        item_type = item.get("type", "")

        if name == "*":
            formatted.append("*")
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
                comp_graphs.append(("Component {}".format(i + 1), subgraph))
        return comp_graphs

    return dir_graphs


def export_graph_to_cytoscape_json(G, vis_graph):
    """Export the graph data to a format suitable for Cytoscape.js"""
    cy_elements = []

    # Add nodes
    for node in vis_graph.nodes():
        node_type = (
            "python"
            if node.endswith(".py")
            else "javascript"
            if node.endswith((".js", ".jsx"))
            else "typescript"
        )
        cy_elements.append(
            {
                "data": {
                    "id": node,
                    "label": os.path.basename(node),
                    "fullPath": node,
                    "type": node_type,
                }
            }
        )

    # Add edges
    for u, v in vis_graph.edges():
        imported_items = G.edges.get((u, v), {}).get("imported_items", [])
        items_text = format_imported_items(imported_items)

        cy_elements.append(
            {
                "data": {
                    "id": f"{u}-{v}",
                    "source": u,
                    "target": v,
                    "imports": items_text,
                }
            }
        )

    return cy_elements


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
            if node.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
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
            if node.endswith(".py"):
                return "skyblue"
            elif node.endswith((".js", ".jsx")):
                return "lightgreen"
            elif node.endswith((".ts", ".tsx")):
                return "lightcoral"
            else:
                return "lightgray"

        # Create legend elements
        legend_elements = [
            mpatches.Patch(color="skyblue", label="Python"),
            mpatches.Patch(color="lightgreen", label="JavaScript"),
            mpatches.Patch(color="lightcoral", label="TypeScript"),
        ]

        # First create the overall graph (compact version)
        output_dir = os.path.dirname(output_path)
        base_filename = os.path.basename(output_path)
        name_without_ext = os.path.splitext(base_filename)[0]

        plt.figure(figsize=(12, 10))
        # Choose layout based on available packages
        if HAS_PYGRAPHVIZ:
            try:
                pos = graphviz_layout(
                    vis_graph, prog="neato"
                )  # 'neato' for cleaner overall view
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
            edge_color="gray",
            arrows=True,
            arrowsize=10,
            arrowstyle="-|>",
            connectionstyle="arc3,rad=0.1",
        )
        plt.legend(handles=legend_elements, loc="upper right")
        plt.title("Repository Dependency Graph (Overview)", size=16)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
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
            safe_name = "".join(c if c.isalnum() else "_" for c in subgraph_name)
            subgraph_path = os.path.join(
                subgraphs_dir, "%02d_%s.png" % (i + 1, safe_name)
            )

            plt.figure(figsize=(10, 8))

            # Layout for this specific subgraph
            if HAS_PYGRAPHVIZ:
                try:
                    sg_pos = graphviz_layout(
                        subgraph, prog="dot"
                    )  # 'dot' for hierarchical subgraphs
                except Exception as e:
                    logging.warning(
                        "Graphviz layout failed for subgraph %s: %s"
                        % (subgraph_name, e)
                    )
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
                font_size=10,  # Larger font for better readability in subgraphs
                edge_color="gray",
                arrows=True,
                arrowsize=15,
                arrowstyle="-|>",
                connectionstyle="arc3,rad=0.1",
            )

            # Draw edge labels if there are not too many edges
            if len(subgraph.edges()) <= 10:
                edge_labels = {}
                for u, v in subgraph.edges():
                    imported_items = G.edges.get((u, v), {}).get("imported_items", [])
                    label = format_imported_items(imported_items)
                    if label:
                        edge_labels[(u, v)] = label

                if edge_labels:
                    nx.draw_networkx_edge_labels(
                        subgraph, sg_pos, edge_labels=edge_labels, font_size=8
                    )

            plt.legend(handles=legend_elements, loc="upper right")
            plt.title(
                "Subgraph: %s (%d files)" % (subgraph_name, len(subgraph)), size=14
            )
            plt.tight_layout()
            plt.savefig(subgraph_path, dpi=300, bbox_inches="tight")
            plt.close()

        # Create an index HTML file for easy navigation with interactive graphs
        index_path = os.path.join(subgraphs_dir, "index.html")

        # Export graph data for interactive visualization
        main_graph_data = export_graph_to_cytoscape_json(G, vis_graph)
        subgraph_data = {}
        for i, (subgraph_name, subgraph) in enumerate(subgraphs):
            if len(subgraph) < 2:
                continue
            subgraph_data[f"subgraph_{i}"] = {
                "name": subgraph_name,
                "elements": export_graph_to_cytoscape_json(G, subgraph),
            }

        # Create JSON files for the graph data
        main_graph_json_path = os.path.join(subgraphs_dir, "main_graph.json")
        with open(main_graph_json_path, "w") as f:
            json.dump(main_graph_data, f)

        subgraphs_json_path = os.path.join(subgraphs_dir, "subgraphs.json")
        with open(subgraphs_json_path, "w") as f:
            json.dump(subgraph_data, f)

        # Generate HTML with Cytoscape.js
        with open(index_path, "w") as f:
            # Use a more reliable method to embed the JSON data
            html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Repository Dependency Graphs</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.25.0/cytoscape.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
        .container { width: 90%; margin: 0 auto; padding: 20px; }
        h1, h2, h3 { color: #333; }
        #cy { width: 100%; height: 600px; border: 1px solid #ddd; margin-bottom: 20px; }
        .graph-container { margin-bottom: 30px; }
        .controls { margin: 15px 0; display: flex; flex-wrap: wrap; gap: 10px; }
        .btn { padding: 8px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; border-radius: 4px; }
        .btn:hover { background: #45a049; }
        .subgraph-selector { padding: 8px; border-radius: 4px; border: 1px solid #ddd; }
        .legend { display: flex; margin: 10px 0; }
        .legend-item { display: flex; align-items: center; margin-right: 15px; }
        .legend-color { width: 20px; height: 20px; margin-right: 5px; border-radius: 3px; }
        .info-panel { background: #f5f5f5; padding: 15px; border-radius: 4px; margin-top: 10px; display: none; }
        .file-list { margin-top: 20px; }
        .file-list li { margin-bottom: 5px; }
        #loading { text-align: center; margin-top: 20px; padding: 10px; }
        #status { padding: 10px; margin: 10px 0; border-radius: 4px; display: none; }
        .status-error { background-color: #f8d7da; color: #721c24; }
        .status-success { background-color: #d4edda; color: #155724; }
        .node-details { margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Repository Dependency Graph Analysis</h1>
        
        <div class="graph-container">
            <h2>Interactive Dependency Graph</h2>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #6BAED6;"></div>
                    <span>Python</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #74C476;"></div>
                    <span>JavaScript</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #EF6548;"></div>
                    <span>TypeScript</span>
                </div>
            </div>
            
            <div class="controls">
                <select id="graphSelector" class="subgraph-selector">
                    <option value="main">Main Graph</option>
                </select>
                <button id="fitBtn" class="btn">Fit View</button>
                <button id="randomLayoutBtn" class="btn">Random Layout</button>
                <button id="gridLayoutBtn" class="btn">Grid Layout</button>
                <button id="concLayoutBtn" class="btn">Concentric Layout</button>
                <button id="spreadLayoutBtn" class="btn">Spread Layout</button>
                <button id="coseLayoutBtn" class="btn">COSE Layout (Default)</button>
            </div>
            
            <div id="cy"></div>
            <div id="loading">Loading graph data...</div>
            <div id="status"></div>
            
            <div id="infoPanel" class="info-panel"></div>
            
            <div class="file-list">
                <h3>Files in Current View</h3>
                <ul id="fileList"></ul>
            </div>
        </div>
    </div>

    <script>
    // Main graph data - will be replaced by Python
    var mainGraphData = MAIN_GRAPH_DATA_PLACEHOLDER;
    
    // Subgraphs data - will be replaced by Python
    var subgraphsData = SUBGRAPHS_DATA_PLACEHOLDER;
    
    $(document).ready(function() {
        function showStatus(message, isError) {
            $('#status').removeClass('status-error status-success')
                      .addClass(isError ? 'status-error' : 'status-success')
                      .html(message)
                      .show();
            
            // Auto-hide status after 5 seconds if it's a success message
            if (!isError) {
                setTimeout(function() {
                    $('#status').fadeOut();
                }, 5000);
            }
        }
        
        try {
            // Initialize Cytoscape
            var cy = cytoscape({
                container: document.getElementById('cy'),
                style: [
                    {
                        selector: 'node',
                        style: {
                            'label': 'data(label)',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'background-color': function(ele) {
                                switch(ele.data('type')) {
                                    case 'python': return '#6BAED6';
                                    case 'javascript': return '#74C476';
                                    case 'typescript': return '#EF6548';
                                    default: return '#ddd';
                                }
                            },
                            'color': '#fff',
                            'font-size': '12px',
                            'width': '60px', // Even larger nodes
                            'height': '60px', // Even larger nodes
                            'text-outline-color': '#555',
                            'text-outline-width': '1px'
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 2,
                            'curve-style': 'bezier',
                            'target-arrow-shape': 'triangle',
                            'line-color': '#999',
                            'target-arrow-color': '#999',
                            'opacity': 0.8
                        }
                    },
                    {
                        selector: 'edge[imports]',
                        style: {
                            'label': 'data(imports)',
                            'font-size': '10px',
                            'text-rotation': 'autorotate',
                            'text-background-opacity': 1,
                            'text-background-color': '#fff',
                            'text-background-padding': '2px'
                        }
                    }
                ],
                layout: {
                    name: 'cose',
                    animate: false,
                    nodeDimensionsIncludeLabels: true,
                    idealEdgeLength: 150, // More spread out
                    nodeOverlap: 20, // Prevent overlap
                    refresh: 20,
                    fit: true,
                    padding: 30,
                    randomize: false,
                    componentSpacing: 250, // More separation between components
                    nodeRepulsion: 8000, // Even more node repulsion
                    edgeElasticity: 100,
                    nestingFactor: 1.2,
                    gravity: 80,
                    numIter: 1000,
                    initialTemp: 200,
                    coolingFactor: 0.95,
                    minTemp: 1.0
                }
            });
            
            // Load main graph data directly from JavaScript variable
            $('#loading').show();
            try {
                cy.add(mainGraphData);
                runCoseLayout();
                updateFileList();
                $('#loading').hide();
                showStatus('Graph loaded successfully', false);
            } catch (err) {
                $('#loading').hide();
                showStatus('Error loading graph: ' + err.message, true);
                console.error('Error processing graph data:', err);
            }
            
            // Populate subgraph dropdown using JavaScript variable
            var selector = $('#graphSelector');
            try {
                Object.keys(subgraphsData).forEach(function(key, index) {
                    var subgraph = subgraphsData[key];
                    var nodeCount = subgraph.elements.filter(e => !e.data.source).length;
                    selector.append($('<option>', {
                        value: key,
                        text: subgraph.name + ' (' + nodeCount + ' files)'
                    }));
                });
            } catch (err) {
                showStatus('Error loading subgraphs: ' + err.message, true);
                console.error('Error processing subgraph data:', err);
            }
            
            // Graph selector change event
            $('#graphSelector').change(function() {
                var selectedValue = $(this).val();
                $('#loading').show();
                
                if (selectedValue === 'main') {
                    // Load main graph
                    cy.elements().remove();
                    try {
                        cy.add(mainGraphData);
                        runCoseLayout();
                        updateFileList();
                        $('#loading').hide();
                    } catch (err) {
                        $('#loading').hide();
                        showStatus('Error loading main graph: ' + err.message, true);
                    }
                } else {
                    // Load selected subgraph
                    try {
                        var subgraphData = subgraphsData[selectedValue];
                        cy.elements().remove();
                        cy.add(subgraphData.elements);
                        runCoseLayout();
                        updateFileList();
                        $('#loading').hide();
                    } catch (err) {
                        $('#loading').hide();
                        showStatus('Error loading subgraph: ' + err.message, true);
                    }
                }
            });
            
            // Node click event
            cy.on('tap', 'node', function(evt) {
                var node = evt.target;
                $('#infoPanel').html(
                    '<strong>File:</strong> ' + node.data('fullPath') + '<br>' +
                    '<strong>Type:</strong> ' + node.data('type').charAt(0).toUpperCase() + node.data('type').slice(1) + '<br>' +
                    '<div class="node-details">' +
                    '<strong>Connections:</strong> ' + node.degree() + ' (' + 
                    node.indegree() + ' in, ' + node.outdegree() + ' out)</div>'
                ).show();
            });
            
            // Background click - hide info panel
            cy.on('tap', function(evt) {
                if (evt.target === cy) {
                    $('#infoPanel').hide();
                }
            });
            
            // Helper function for COSE layout
            function runCoseLayout() {
                cy.layout({
                    name: 'cose',
                    animate: false,
                    nodeDimensionsIncludeLabels: true,
                    idealEdgeLength: 150,
                    nodeOverlap: 20,
                    componentSpacing: 250,
                    nodeRepulsion: 8000,
                    edgeElasticity: 100,
                    nestingFactor: 1.2,
                    gravity: 80,
                    numIter: 1000
                }).run();
                cy.fit();
            }
            
            // Control buttons
            $('#fitBtn').click(function() {
                cy.fit();
            });
            
            $('#randomLayoutBtn').click(function() {
                $('#loading').show();
                try {
                    cy.layout({
                        name: 'random', 
                        animate: false,
                        padding: 50
                    }).run();
                    cy.fit();
                    $('#loading').hide();
                } catch (err) {
                    $('#loading').hide();
                    showStatus('Error applying layout: ' + err.message, true);
                }
            });
            
            $('#gridLayoutBtn').click(function() {
                $('#loading').show();
                try {
                    cy.layout({
                        name: 'grid', 
                        animate: false,
                        padding: 50
                    }).run();
                    cy.fit();
                    $('#loading').hide();
                } catch (err) {
                    $('#loading').hide();
                    showStatus('Error applying layout: ' + err.message, true);
                }
            });
            
            $('#concLayoutBtn').click(function() {
                $('#loading').show();
                try {
                    cy.layout({
                        name: 'concentric', 
                        animate: false,
                        minNodeSpacing: 80, // More space between nodes
                        concentric: function(node) {
                            // Place nodes with more connections in the center
                            return node.degree();
                        },
                        levelWidth: function() { return 2; },
                        padding: 50
                    }).run();
                    cy.fit();
                    $('#loading').hide();
                } catch (err) {
                    $('#loading').hide();
                    showStatus('Error applying layout: ' + err.message, true);
                }
            });
            
            $('#spreadLayoutBtn').click(function() {
                $('#loading').show();
                try {
                    cy.layout({
                        name: 'spread',
                        animate: false,
                        minDist: 100, // Increased minimum distance between nodes
                        padding: 50,
                        expandingFactor: -1 // Negative is more spread out
                    }).run();
                    cy.fit();
                    $('#loading').hide();
                } catch (err) {
                    $('#loading').hide();
                    showStatus('Error applying layout: ' + err.message, true);
                }
            });
            
            $('#coseLayoutBtn').click(function() {
                $('#loading').show();
                try {
                    runCoseLayout();
                    $('#loading').hide();
                } catch (err) {
                    $('#loading').hide();
                    showStatus('Error applying layout: ' + err.message, true);
                }
            });
            
            // Update file list
            function updateFileList() {
                var fileList = $('#fileList');
                fileList.empty();
                
                cy.nodes().sort(function(a, b) {
                    return a.data('fullPath').localeCompare(b.data('fullPath'));
                }).forEach(function(node) {
                    fileList.append('<li>' + node.data('fullPath') + '</li>');
                });
            }
        } catch (err) {
            $('#loading').hide();
            showStatus('Critical error initializing graph: ' + err.message, true);
            console.error('Critical error:', err);
        }
    });
    </script>
</body>
</html>"""

            # Replace placeholders with actual data
            # This avoids issues with f-string formatting and escaping
            html_template = html_template.replace(
                "MAIN_GRAPH_DATA_PLACEHOLDER", json.dumps(main_graph_data)
            )
            html_template = html_template.replace(
                "SUBGRAPHS_DATA_PLACEHOLDER", json.dumps(subgraph_data)
            )

            # Write to file
            f.write(html_template)

        logging.info("Dependency graph visualization saved to %s" % output_path)
        logging.info("Interactive visualization created at %s" % index_path)
        logging.info("Subgraph visualizations saved to %s" % subgraphs_dir)

    except Exception as e:
        logging.error("Error visualizing dependency graph: %s" % e)
        traceback.print_exc()
