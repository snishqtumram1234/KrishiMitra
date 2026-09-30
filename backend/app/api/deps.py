from functools import lru_cache

from app.config import get_settings
from app.services.case_store import CaseStore, InMemoryCaseStore
from app.services.orchestrator import Orchestrator


@lru_cache
def get_store() -> CaseStore:
    s = get_settings()
    if s.store_backend == "supabase":
        from app.services.supabase_store import SupabaseCaseStore

        return SupabaseCaseStore(s.supabase_url, s.supabase_service_key)
    if s.store_backend == "memory":
        return InMemoryCaseStore()
    raise ValueError(f"Unknown STORE_BACKEND: {s.store_backend!r}")


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()
