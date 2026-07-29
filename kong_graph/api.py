"""
Kong Graph API Server.

REST API for the knowledge graph memory system.

Copyright 2026 Coinkong (Chef's Attraction). MIT License.
"""

import os
import pickle
from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from .graph import MemoryGraph
from .pipeline import store, store_batch, recall, get_graph, set_graph, get_stm
from .recency import ShortTermMemory

API_TOKEN = os.environ.get("KONG_API_TOKEN", os.environ.get("QMG_API_TOKEN", ""))
KONG_MODEL = os.environ.get("KONG_MODEL", os.environ.get("QMG_MODEL", None))


async def verify_token(request: Request):
    if request.url.path in ("/", "/docs", "/openapi.json", "/redoc"):
        return
    if not API_TOKEN:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI(
    title="Kong Graph API",
    version="1.0.0",
    description="Classical knowledge graph memory for AI agents — 99.4% retrieval with chunked embeddings",
    dependencies=[Depends(verify_token)],
)

# Initialize graph on startup
_graph = None


@app.on_event("startup")
async def startup():
    global _graph
    threshold = float(os.environ.get("KONG_SIMILARITY_THRESHOLD",
                                     os.environ.get("QMG_SIMILARITY_THRESHOLD", "0.3")))
    _graph = MemoryGraph(similarity_threshold=threshold, model=KONG_MODEL)
    set_graph(_graph)
    # Initialize short-term memory
    stm = get_stm()
    print(f"  Model: {_graph._model_name}")
    print(f"  Short-term memory: enabled (recency + working memory + conversation)")

    # Load persisted graph from disk if available
    data_dir = os.environ.get("KONG_DATA_DIR", os.environ.get("QMG_DATA_DIR", ""))
    if data_dir:
        pkl_path = os.path.join(data_dir, "graph.pkl")
        if os.path.exists(pkl_path):
            try:
                _graph = MemoryGraph.load(pkl_path, model=KONG_MODEL)
                set_graph(_graph)
                stats = _graph.stats()
                print(f"  Loaded {stats['nodes']} memories from disk ({pkl_path})")
            except Exception as e:
                print(f"  WARNING: Failed to load graph from {pkl_path}: {e}")


@app.on_event("shutdown")
async def shutdown():
    data_dir = os.environ.get("KONG_DATA_DIR", os.environ.get("QMG_DATA_DIR", ""))
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        pkl_path = os.path.join(data_dir, "graph.pkl")
        try:
            g = get_graph()
            g.save(pkl_path)
            print(f"  Saved {g.stats()['nodes']} memories to {pkl_path}")
        except Exception as e:
            print(f"  WARNING: Failed to save graph: {e}")


@app.get("/")
async def health():
    g = get_graph()
    return {
        "status": "operational",
        "service": "Kong Graph",
        "version": "1.0.0",
        "graph": g.stats() if g and g.memories else {"nodes": 0, "edges": 0},
        "auth": "enabled" if API_TOKEN else "disabled",
    }


class StoreRequest(BaseModel):
    text: str
    entities: Optional[List[str]] = None
    source: str = ""


@app.post("/store")
async def api_store(req: StoreRequest):
    result = store(
        text=req.text,
        entities=req.entities,
        source=req.source,
    )
    return result


class StoreBatchRequest(BaseModel):
    texts: List[str]
    sources: Optional[List[str]] = None


@app.post("/store-batch")
async def api_store_batch(req: StoreBatchRequest):
    result = store_batch(
        texts=req.texts,
        sources=req.sources,
    )
    return result


class RecallRequest(BaseModel):
    query: str
    k: int = 5
    hops: int = 2
    top_seeds: int = 5
    alpha: float = 0.4
    beta_conn: float = 0.35
    gamma_cov: float = 0.25
    max_candidates: int = 14


@app.post("/recall")
async def api_recall(req: RecallRequest):
    result = recall(
        query=req.query,
        K=req.k,
        hops=req.hops,
        top_seeds=req.top_seeds,
        alpha=req.alpha,
        beta_conn=req.beta_conn,
        gamma_cov=req.gamma_cov,
        max_candidates=req.max_candidates,
    )
    # Log recall pattern for self-learning
    g = get_graph()
    if g and result.get("memories"):
        node_ids = []
        for mem in result["memories"]:
            # Derive memory ID from text
            from .graph import Memory
            mid = Memory.make_id(mem["text"])
            if mid in g.memories:
                node_ids.append(mid)
        if node_ids:
            g.recall_tracker.log_recall(req.query, node_ids)
    return result


@app.post("/learn")
async def learn_weights():
    """Process recall history and update learned edge weights."""
    g = get_graph()
    if g is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    weights = g.learn()
    return {"learned_edges": len(weights), "weights": {f"{a}<->{b}": w for (a,b), w in list(weights.items())[:20]}}


@app.get("/scores")
async def memory_scores():
    """Get memory value scores based on recall frequency."""
    g = get_graph()
    if g is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    scores = g.get_memory_scores()
    return {"scored_memories": len(scores), "top": dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10])}


@app.get("/stats")
async def api_stats():
    g = get_graph()
    stm = get_stm()
    stats = g.stats() if g else {"nodes": 0, "edges": 0}
    stats["short_term_memory"] = stm.stats()
    return stats


def main():
    host = os.environ.get("KONG_HOST", os.environ.get("QMG_HOST", "0.0.0.0"))
    port = int(os.environ.get("KONG_PORT", os.environ.get("QMG_PORT", "8502")))
    print(f"🦍 Kong Graph API starting on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
