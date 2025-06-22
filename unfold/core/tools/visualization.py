"""
Visualization tools for MCP integration.
"""

import os
from typing import Any


class VisualizationTools:
    """Tools for data visualization and knowledge graph display."""

    def __init__(self, working_directory: str = None, graph_service=None):
        """Initialize visualization tools."""
        self.working_directory = working_directory or os.getcwd()
        self.graph_service = graph_service

    async def visualize_knowledge_graph(self) -> dict[str, Any]:
        """Display the knowledge graph in an interactive popup window."""
        try:
            if not self.graph_service:
                return {"success": False, "error": "Graph service not available"}

            # Import visualization libraries
            try:
                import tkinter as tk
                from tkinter import ttk

                import matplotlib.patches as patches
                import matplotlib.pyplot as plt
                import networkx as nx
            except ImportError as e:
                return {"success": False, "error": f"Visualization libraries not available: {e}"}

            # Get graph data
            graph_data = self.graph_service.get_graph_summary()
            
            if not graph_data or graph_data.get("total_nodes", 0) == 0:
                return {"success": False, "error": "No graph data available to visualize"}

            # Create NetworkX graph from service data
            G = nx.Graph()
            
            # Add nodes with attributes
            nodes = graph_data.get("nodes", [])
            for node in nodes:
                G.add_node(
                    node["id"], 
                    type=node.get("type", "unknown"),
                    name=node.get("name", "")
                )

            # Add edges
            edges = graph_data.get("edges", [])
            for edge in edges:
                G.add_edge(edge["source"], edge["target"], 
                          relationship=edge.get("relationship", ""))

            # Create visualization window
            root = tk.Tk()
            root.title("Unfold Knowledge Graph")
            root.geometry("1000x700")

            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Choose layout based on graph size
            num_nodes = len(G.nodes())
            if num_nodes < 50:
                pos = nx.spring_layout(G, k=1, iterations=50)
            elif num_nodes < 200:
                pos = nx.spring_layout(G, k=0.5, iterations=30)
            else:
                pos = nx.circular_layout(G)

            # Color nodes by type
            node_colors = []
            node_types = set()
            for node in G.nodes(data=True):
                node_type = node[1].get('type', 'unknown')
                node_types.add(node_type)
                
                if node_type == 'file':
                    node_colors.append('lightblue')
                elif node_type == 'directory':
                    node_colors.append('lightgreen')
                elif node_type == 'module':
                    node_colors.append('orange')
                elif node_type in ['function', 'class']:
                    node_colors.append('pink')
                else:
                    node_colors.append('gray')

            # Draw the graph
            nx.draw(G, pos, ax=ax,
                   node_color=node_colors,
                   node_size=100,
                   edge_color='gray',
                   alpha=0.7,
                   with_labels=False,
                   font_size=8)

            # Add title and statistics
            ax.set_title(f"Knowledge Graph\nNodes: {len(G.nodes())}, Edges: {len(G.edges())}", 
                        fontsize=14, fontweight='bold')

            # Create legend
            legend_elements = []
            colors = {'file': 'lightblue', 'directory': 'lightgreen', 
                     'module': 'orange', 'function': 'pink', 'class': 'pink'}
            
            for node_type in node_types:
                color = colors.get(node_type, 'gray')
                legend_elements.append(patches.Patch(color=color, label=node_type.title()))
            
            ax.legend(handles=legend_elements, loc='upper right')

            # Embed matplotlib in tkinter
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            canvas = FigureCanvasTkAgg(fig, master=root)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

            # Add toolbar with statistics
            toolbar_frame = ttk.Frame(root)
            toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

            stats_text = f"Working Directory: {self.working_directory} | Nodes: {len(G.nodes())} | Edges: {len(G.edges())} | Types: {len(node_types)}"
            stats_label = ttk.Label(toolbar_frame, text=stats_text)
            stats_label.pack(side=tk.LEFT, padx=5)

            # Close button
            close_button = ttk.Button(toolbar_frame, text="Close", 
                                    command=root.destroy)
            close_button.pack(side=tk.RIGHT, padx=5)

            # Show the window
            root.mainloop()

            return {
                "success": True,
                "nodes_displayed": len(G.nodes()),
                "edges_displayed": len(G.edges()),
                "node_types": list(node_types),
                "message": "Knowledge graph visualization displayed successfully"
            }

        except Exception as e:
            return {"success": False, "error": f"Visualization failed: {str(e)}"}

    async def export_graph_data(self, format_type: str = "json", output_path: str = None) -> dict[str, Any]:
        """Export graph data in various formats."""
        try:
            if not self.graph_service:
                return {"success": False, "error": "Graph service not available"}

            # Get graph data
            graph_data = self.graph_service.get_graph_summary()
            
            if not graph_data:
                return {"success": False, "error": "No graph data available"}

            # Determine output path
            if not output_path:
                output_path = f"knowledge_graph.{format_type}"

            output_file = os.path.join(self.working_directory, output_path)

            if format_type.lower() == "json":
                import json
                with open(output_file, 'w') as f:
                    json.dump(graph_data, f, indent=2)
            
            elif format_type.lower() == "csv":
                import csv
                # Export nodes
                nodes_file = output_file.replace('.csv', '_nodes.csv')
                with open(nodes_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['id', 'name', 'type'])
                    for node in graph_data.get("nodes", []):
                        writer.writerow([node["id"], node.get("name", ""), node.get("type", "")])
                
                # Export edges
                edges_file = output_file.replace('.csv', '_edges.csv')
                with open(edges_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['source', 'target', 'relationship'])
                    for edge in graph_data.get("edges", []):
                        writer.writerow([edge["source"], edge["target"], edge.get("relationship", "")])
                
                output_file = f"{nodes_file}, {edges_file}"
            
            elif format_type.lower() == "gexf":
                # Export as GEXF format for Gephi
                try:
                    import networkx as nx
                    
                    G = nx.Graph()
                    for node in graph_data.get("nodes", []):
                        G.add_node(node["id"], 
                                  name=node.get("name", ""),
                                  type=node.get("type", ""))
                    
                    for edge in graph_data.get("edges", []):
                        G.add_edge(edge["source"], edge["target"],
                                  relationship=edge.get("relationship", ""))
                    
                    nx.write_gexf(G, output_file)
                except ImportError:
                    return {"success": False, "error": "NetworkX not available for GEXF export"}
            
            else:
                return {"success": False, "error": f"Unsupported format: {format_type}"}

            return {
                "success": True,
                "format": format_type,
                "output_file": output_file,
                "nodes_exported": len(graph_data.get("nodes", [])),
                "edges_exported": len(graph_data.get("edges", []))
            }

        except Exception as e:
            return {"success": False, "error": f"Graph export failed: {str(e)}"}

    async def generate_graph_statistics(self) -> dict[str, Any]:
        """Generate detailed statistics about the knowledge graph."""
        try:
            if not self.graph_service:
                return {"success": False, "error": "Graph service not available"}

            # Get graph data
            graph_data = self.graph_service.get_graph_summary()
            
            if not graph_data:
                return {"success": False, "error": "No graph data available"}

            nodes = graph_data.get("nodes", [])
            edges = graph_data.get("edges", [])

            # Basic statistics
            total_nodes = len(nodes)
            total_edges = len(edges)

            # Node type distribution
            node_types = {}
            for node in nodes:
                node_type = node.get("type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1

            # Edge relationship distribution
            edge_relationships = {}
            for edge in edges:
                relationship = edge.get("relationship", "unknown")
                edge_relationships[relationship] = edge_relationships.get(relationship, 0) + 1

            # Calculate graph metrics if NetworkX is available
            graph_metrics = {}
            try:
                import networkx as nx
                
                G = nx.Graph()
                for node in nodes:
                    G.add_node(node["id"])
                for edge in edges:
                    G.add_edge(edge["source"], edge["target"])

                if len(G.nodes()) > 0:
                    graph_metrics = {
                        "density": nx.density(G),
                        "connected_components": nx.number_connected_components(G),
                        "average_clustering": nx.average_clustering(G),
                        "diameter": nx.diameter(G) if nx.is_connected(G) else "N/A (not connected)"
                    }

                    # Degree statistics
                    degrees = [d for n, d in G.degree()]
                    if degrees:
                        graph_metrics["average_degree"] = sum(degrees) / len(degrees)
                        graph_metrics["max_degree"] = max(degrees)
                        graph_metrics["min_degree"] = min(degrees)

            except ImportError:
                graph_metrics = {"note": "NetworkX not available for advanced metrics"}
            except Exception as e:
                graph_metrics = {"error": f"Error calculating metrics: {str(e)}"}

            return {
                "success": True,
                "basic_stats": {
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                    "node_types": node_types,
                    "edge_relationships": edge_relationships
                },
                "graph_metrics": graph_metrics,
                "working_directory": self.working_directory
            }

        except Exception as e:
            return {"success": False, "error": f"Statistics generation failed: {str(e)}"} 