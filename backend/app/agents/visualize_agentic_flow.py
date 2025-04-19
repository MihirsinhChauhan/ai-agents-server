from app.agents.orchestrator import DebtOptimizerOrchestrator
from langchain_core.runnables.graph import MermaidDrawMethod
import os

def save_workflow_diagram(output_path: str = "workflow_diagram.png"):
    """
    Save the LangGraph workflow diagram as a PNG file.

    Args:
        output_path (str): Path where the PNG file will be saved.
    """
    try:
        # Initialize the orchestrator
        agentic_flow = DebtOptimizerOrchestrator()

        # Build the workflow and get the graph
        workflow = agentic_flow._build_workflow()
        graph = workflow.get_graph()

        # Generate the Mermaid diagram as PNG bytes
        png_bytes = graph.draw_mermaid_png(draw_method=MermaidDrawMethod.API)

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the PNG to the specified file
        with open(output_path, "wb") as f:
            f.write(png_bytes)

        print(f"Workflow diagram saved to {output_path}")

    except Exception as e:
        print(f"Error saving workflow diagram: {str(e)}")

if __name__ == "__main__":
    save_workflow_diagram(output_path="outputs/workflow_diagram.png")