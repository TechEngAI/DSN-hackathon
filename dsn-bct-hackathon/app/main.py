from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.task_a import router as task_a_router
from app.task_b import router as task_b_router


app = FastAPI(title="DSN x BCT Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(task_a_router, prefix="/task-a")
app.include_router(task_b_router, prefix="/task-b")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "running", "version": "1.0"}
