"""Vector-store contract with a small SQLite implementation."""

from dataclasses import dataclass
import math
from typing import Protocol, Sequence

from django.db.models import F, Q
from django.utils import timezone

from .models import (
    KnowledgeChunkEmbedding,
    KnowledgeIndexingJob,
    PreservedKnowledge
)


@dataclass(frozen=True)
class VectorCandidate:
    chunk_id: int
    similarity: float


class VectorStore(Protocol):
    def upsert(self, chunk, provider, model, vector): ...
    def invalidate(self, chunk): ...
    def search(self, space, vector, provider, model, limit=20) -> list[VectorCandidate]: ...


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


class DatabaseVectorStore:
    """Portable initial store; replaceable without changing embedding code."""

    def upsert(self, chunk, provider, model, vector):
        embedding, _created = KnowledgeChunkEmbedding.objects.update_or_create(
            chunk=chunk,
            provider=provider.provider_name,
            model=model,
            defaults={
                'space': chunk.space,
                'knowledge_version': chunk.version,
                'dimensions': provider.dimensions,
                'vector': vector,
                'status': KnowledgeChunkEmbedding.Status.READY,
                'error_message': '',
                'generated_at': timezone.now()
            }
        )
        return embedding

    def invalidate(self, chunk):
        KnowledgeChunkEmbedding.objects.filter(
            chunk=chunk,
            status__in=(
                KnowledgeChunkEmbedding.Status.PENDING,
                KnowledgeChunkEmbedding.Status.READY
            )
        ).update(status=KnowledgeChunkEmbedding.Status.OBSOLETE)

    def search(self, space, vector, provider, model, limit=20):
        candidates = []
        eligible = Q(
            chunk__space=space,
            chunk__job__status=KnowledgeIndexingJob.Status.INDEXED,
            chunk__invalidated_at__isnull=True,
            chunk__knowledge__status=PreservedKnowledge.Status.ACTIVE,
            chunk__knowledge__current_version_id=F('chunk__version_id'),
            chunk__source_message__deleted_at__isnull=True,
            status=KnowledgeChunkEmbedding.Status.READY,
            provider=provider.provider_name,
            model=model
        )
        for embedding in KnowledgeChunkEmbedding.objects.filter(eligible).only('chunk_id', 'vector'):
            candidates.append(VectorCandidate(
                chunk_id=embedding.chunk_id,
                similarity=_cosine_similarity(vector, embedding.vector)
            ))
        candidates.sort(key=lambda candidate: (-candidate.similarity, candidate.chunk_id))
        return candidates[:limit]


def get_vector_store() -> VectorStore:
    return DatabaseVectorStore()
