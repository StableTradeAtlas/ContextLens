from __future__ import annotations

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "FastAPI is not installed. Run `pip install -r requirements.txt`, "
        "or use the dependency-free demo: `python -m app.web_demo`."
    ) from exc

from app.agent import answer_question
from app.ingest import ingest
from app.web_demo import VERSION, health_payload
from app.storage import count_records


class AskRequest(BaseModel):
    question: str
    top_k: int = 10
    language: str = "zh"
    mode: str = "general"
    output_style: str = "evidence_brief"
    use_deepseek: bool = False


app = FastAPI(title="ContextLens 文脉镜 API", version=VERSION)


@app.on_event("startup")
def startup() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)


@app.get("/health")
def health() -> dict:
    return health_payload()


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    return answer_question(
        req.question,
        top_k=req.top_k,
        language=req.language,
        mode=req.mode,
        output_style=req.output_style,
        use_deepseek=req.use_deepseek,
    )
