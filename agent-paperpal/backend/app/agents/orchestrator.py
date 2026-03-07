# backend/app/agents/orchestrator.py
from langgraph.graph import StateGraph, END
from app.schemas.job_state import JobState

from app.agents.ingestion.agent import DocIngestionAgent
from app.agents.parsing.agent import DocParseAgent
from app.agents.interpretation.agent import RuleInterpretAgent
from app.agents.transformation.agent import TransformAgent
from app.agents.validation.agent import ValidationAgent
from app.services.renderer.renderer_service import RendererService

async def render_node(state: JobState) -> JobState:
    renderer = RendererService()
    await renderer.render(state)
    return state

def route_or_fail(state: JobState):
    return 'next' if not state.errors else END

def route_from_ingest(state: JobState):
    """Route to Stage 2 and 3 in parallel if successful."""
    if state.errors:
        return END
    return ['parse', 'interpret']

def build_pipeline():
    graph = StateGraph(JobState)
    
    graph.add_node('ingest', DocIngestionAgent().run)
    from app.agents.parsing.agent import run_parsing
    graph.add_node('parse', run_parsing)
    from app.agents.interpretation.agent import run_stage3
    graph.add_node('interpret', run_stage3)
    graph.add_node('transform', TransformAgent().run)
    graph.add_node('validate', ValidationAgent().run)
    graph.add_node('render', render_node)
    
    graph.set_entry_point('ingest')
    
    # Fan-out: run Stage 2 and Stage 3 in parallel
    graph.add_conditional_edges('ingest', route_from_ingest)
    
    # Fan-in: transform waits for both parse and interpret
    graph.add_edge('parse', 'transform')
    graph.add_edge('interpret', 'transform')
    
    graph.add_conditional_edges('transform', route_or_fail, {'next': 'validate', END: END})
    
    # After validate: always go to render
    graph.add_edge('validate', 'render')
    graph.add_edge('render', END)
    
    return graph.compile()

pipeline = build_pipeline()
