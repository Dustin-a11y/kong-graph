"""
Kong Graph — Classical memory graph for AI agents.

Knowledge graphs + chunked embedding retrieval — 99.4% recall on LongMemEval.

Formerly part of Quantum Memory Graph. Now a standalone classical system.
See https://github.com/Dustin-a11y/quantum-memory-graph for quantum work.

Copyright 2026 Coinkong (Chef's Attraction). MIT License.
"""

__version__ = "1.3.0"

from .graph import MemoryGraph
from .learning import RecallTracker
from .subgraph_optimizer import optimize_subgraph
from .pipeline import recall, store, get_stm, set_stm
from .recency import ShortTermMemory, RecencyBooster, WorkingMemory, ConversationContext

__all__ = [
    "MemoryGraph", "RecallTracker", "optimize_subgraph", "recall", "store",
    "ShortTermMemory", "RecencyBooster", "WorkingMemory", "ConversationContext",
    "get_stm", "set_stm",
]
