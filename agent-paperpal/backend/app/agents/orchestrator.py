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

def build_pipeline():
    graph = StateGraph(JobState)
    
    graph.add_node('ingest', DocIngestionAgent().run)
    graph.add_node('parse', DocParseAgent().run)
    graph.add_node('interpret', RuleInterpretAgent().run)
    graph.add_node('transform', TransformAgent().run)
    graph.add_node('validate', ValidationAgent().run)
    graph.add_node('render', render_node)
    
    graph.set_entry_point('ingest')
    
    graph.add_conditional_edges('ingest', route_or_fail, {'next': 'parse', END: END})
    graph.add_conditional_edges('parse', route_or_fail, {'next': 'interpret', END: END})
    graph.add_conditional_edges('interpret', route_or_fail, {'next': 'transform', END: END})
    graph.add_conditional_edges('transform', route_or_fail, {'next': 'validate', END: END})
    
    # After validate: always go to render (even with some issues)
    graph.add_edge('validate', 'render')
    graph.add_edge('render', END)
    
    return graph.compile()

pipeline = build_pipeline()
