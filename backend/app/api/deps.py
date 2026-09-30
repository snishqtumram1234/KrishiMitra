from functools import lru_cache

from app.services.case_store import CaseStore, InMemoryCaseStore
from app.services.orchestrator import Orchestrator


@lru_cache
def get_store() -> CaseStore:
    return InMemoryCaseStore()


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()
