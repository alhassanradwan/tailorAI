"""
services/agents package.

Exports AGENTS dict consumed by agent_router.py and prompt_builder.py.
Import order is safe — no circular dependency:
    agent_router  → services.agents (AGENTS)
    prompt_builder → services.agents.*_agent  (individual modules, NOT __init__)
"""

from .data_science_agent import DataScienceAgent
from .machine_learning_agent import MachineLearningAgent
from .deep_learning_agent import DeepLearningAgent

AGENTS = {
    'data_science':     DataScienceAgent.to_dict(),
    'machine_learning': MachineLearningAgent.to_dict(),
    'deep_learning':    DeepLearningAgent.to_dict(),
}

__all__ = [
    'AGENTS',
    'DataScienceAgent',
    'MachineLearningAgent',
    'DeepLearningAgent',
]