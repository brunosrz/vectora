"""Vectora Agents — specs dos sub-agents do deep-agent.

Os sub-agents (coder, search) são declarados como ``SUBAGENT_SPEC`` e
consumidos por ``agent_factory._subagent_specs()`` em ``create_deep_agent``.
"""

from backend.agents.coder import SUBAGENT_SPEC as CODER_SPEC
from backend.agents.search import SUBAGENT_SPEC as SEARCH_SPEC

__all__ = ["CODER_SPEC", "SEARCH_SPEC"]
