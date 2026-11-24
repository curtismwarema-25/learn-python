"""Embedding materialization for durable knowledge indexing jobs."""

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .embeddings import EmbeddingProviderError, get_embedding_provider
from .models import (
    KnowledgeChunkEmbedding,
    KnowledgeIndexChunk,
    KnowledgeIndexingJob,
    PreservedKnowledge
)
from .vector_store import get_vector_store


def _eligible(job):
    knowledge = job.knowledge
    return (
        job.status == KnowledgeIndexingJob.Status.INDEXED
        and knowledge.status == PreservedKnowledge.Status.ACTIVE
        and knowledge.current_version_id == job.version_id
        and knowledge.source_message.deleted_at is None
    )


def _mark_failed(job_id, error):
    KnowledgeIndexingJob.objects.filter(pk=job_id).update(
        embedding_status=KnowledgeIndexingJob.EmbeddingStatus.FAILED,
        embedding_error=str(error)[:2000],
        embedding_completed_at=timezone.now(),
        update_date=timezone.now()
    )


def embed_indexing_job(job_id: int, provider_name=None):
    """Generate and persist embeddings, rechecking eligibility before writes."""
    try:
        provider = get_embedding_provider(provider_name)
    except Exception as error:
        _mark_failed(job_id, error)
        raise

    with transaction.atomic():
        job = (
            KnowledgeIndexingJob.objects
            .select_for_update()
            .select_related(
                'knowledge__current_version',
                'knowledge__source_message'
            )
            .get(pk=job_id)
        )
        if not _eligible(job):
            KnowledgeChunkEmbedding.objects.filter(
                chunk__job=job,
                status__in=(
                    KnowledgeChunkEmbedding.Status.PENDING,
                    KnowledgeChunkEmbedding.Status.READY
                )
            ).update(status=KnowledgeChunkEmbedding.Status.OBSOLETE)
            job.embedding_status = KnowledgeIndexingJob.EmbeddingStatus.OBSOLETE
            job.save(update_fields=('embedding_status', 'update_date'))
            return job

        chunks = list(KnowledgeIndexChunk.objects.filter(
            job=job,
            invalidated_at__isnull=True
        ).order_by('chunk_index'))
        ready_count = KnowledgeChunkEmbedding.objects.filter(
            chunk__in=chunks,
            provider=provider.provider_name,
            model=provider.model,
            status=KnowledgeChunkEmbedding.Status.READY
        ).count()
        if (
            job.embedding_status == KnowledgeIndexingJob.EmbeddingStatus.COMPLETE
            and ready_count == len(chunks)
        ):
            return job

        KnowledgeChunkEmbedding.objects.filter(
            chunk__in=chunks
        ).exclude(
            provider=provider.provider_name,
            model=provider.model
        ).update(status=KnowledgeChunkEmbedding.Status.OBSOLETE)
        job.embedding_status = KnowledgeIndexingJob.EmbeddingStatus.PROCESSING
        job.embedding_provider = provider.provider_name
        job.embedding_model = provider.model
        job.embedding_attempt_count += 1
        job.embedding_error = ''
        job.embedding_started_at = timezone.now()
        job.embedding_completed_at = None
        job.save(update_fields=(
            'embedding_status', 'embedding_provider', 'embedding_model',
            'embedding_attempt_count', 'embedding_error',
            'embedding_started_at', 'embedding_completed_at', 'update_date'
        ))

    try:
        vectors = []
        batch_size = max(1, settings.FUEGO_EMBEDDING_BATCH_SIZE)
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            batch_vectors = provider.embed_batch([chunk.content for chunk in batch])
            if len(batch_vectors) != len(batch):
                raise EmbeddingProviderError('Provider returned the wrong batch size.')
            vectors.extend(provider.validate_vector(vector) for vector in batch_vectors)
    except Exception as error:
        _mark_failed(job_id, error)
        raise

    with transaction.atomic():
        job = (
            KnowledgeIndexingJob.objects
            .select_for_update()
            .select_related(
                'knowledge__current_version',
                'knowledge__source_message'
            )
            .get(pk=job_id)
        )
        if not _eligible(job):
            KnowledgeChunkEmbedding.objects.filter(
                chunk__job=job,
                status__in=(
                    KnowledgeChunkEmbedding.Status.PENDING,
                    KnowledgeChunkEmbedding.Status.READY
                )
            ).update(status=KnowledgeChunkEmbedding.Status.OBSOLETE)
            job.embedding_status = KnowledgeIndexingJob.EmbeddingStatus.OBSOLETE
            job.save(update_fields=('embedding_status', 'update_date'))
            return job

        store = get_vector_store()
        for chunk, vector in zip(chunks, vectors):
            store.upsert(chunk, provider, provider.model, vector)
        job.embedding_status = KnowledgeIndexingJob.EmbeddingStatus.COMPLETE
        job.embedding_completed_at = timezone.now()
        job.save(update_fields=(
            'embedding_status', 'embedding_completed_at', 'update_date'
        ))
        return job
