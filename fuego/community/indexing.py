"""Deterministic, database-backed indexing for explicitly preserved knowledge."""

from dataclasses import dataclass
import re
import unicodedata

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import (
    KnowledgeChunkEmbedding,
    KnowledgeIndexChunk,
    KnowledgeIndexingJob,
    PreservedKnowledge
)


MAX_CHUNK_CHARACTERS = 1000
CHUNK_OVERLAP_CHARACTERS = 120
WORD_PATTERN = re.compile(r'\S+')


@dataclass(frozen=True)
class ChunkDraft:
    index: int
    content: str
    start_offset: int
    end_offset: int


def normalize_content(content: str) -> str:
    """Produce the canonical text used for both indexing and future embedding."""
    normalized = unicodedata.normalize('NFKC', content)
    return ' '.join(normalized.split())


def chunk_content(content: str) -> list[ChunkDraft]:
    """Split normalized text on word boundaries with deterministic overlap."""
    normalized = normalize_content(content)
    if not normalized:
        return []

    spans = [match.span() for match in WORD_PATTERN.finditer(normalized)]
    chunks = []
    start_word = 0
    while start_word < len(spans):
        start_offset = spans[start_word][0]
        end_word = start_word
        while end_word < len(spans):
            candidate_end = spans[end_word][1]
            if candidate_end - start_offset > MAX_CHUNK_CHARACTERS and end_word > start_word:
                break
            end_word += 1
        end_offset = spans[end_word - 1][1]
        chunks.append(ChunkDraft(
            index=len(chunks),
            content=normalized[start_offset:end_offset],
            start_offset=start_offset,
            end_offset=end_offset
        ))
        if end_word >= len(spans):
            break

        overlap_start = end_offset - CHUNK_OVERLAP_CHARACTERS
        next_word = end_word
        while next_word > start_word and spans[next_word - 1][0] >= overlap_start:
            next_word -= 1
        start_word = next_word if next_word > start_word else end_word
    return chunks


def _eligible(knowledge):
    return (
        knowledge.status == PreservedKnowledge.Status.ACTIVE
        and knowledge.current_version_id is not None
        and knowledge.source_message.deleted_at is None
    )


def invalidate_knowledge_index(knowledge):
    """Make every materialization for a knowledge record ineligible."""
    now = timezone.now()
    KnowledgeIndexChunk.objects.filter(
        knowledge=knowledge,
        invalidated_at__isnull=True
    ).update(invalidated_at=now)
    KnowledgeIndexingJob.objects.filter(
        knowledge=knowledge,
        status__in=(
            KnowledgeIndexingJob.Status.PENDING,
            KnowledgeIndexingJob.Status.INDEXED
        )
    ).update(
        status=KnowledgeIndexingJob.Status.OBSOLETE,
        embedding_status=KnowledgeIndexingJob.EmbeddingStatus.OBSOLETE,
        update_date=now
    )
    KnowledgeChunkEmbedding.objects.filter(
        chunk__knowledge=knowledge,
        status__in=(
            KnowledgeChunkEmbedding.Status.PENDING,
            KnowledgeChunkEmbedding.Status.READY
        )
    ).update(status=KnowledgeChunkEmbedding.Status.OBSOLETE)


def index_knowledge(knowledge_id: int):
    """Idempotently materialize the current eligible version.

    Index failures are retained on a retryable job instead of making the
    preservation or correction transaction fail after its authoritative data
    has been committed.
    """
    with transaction.atomic():
        knowledge = (
            PreservedKnowledge.objects
            .select_for_update()
            .select_related(
                'current_version',
                'source_message__user',
                'source_message__chat_session__space_channel'
            )
            .get(pk=knowledge_id)
        )
        if not _eligible(knowledge):
            invalidate_knowledge_index(knowledge)
            return None

        version = knowledge.current_version
        job, created = KnowledgeIndexingJob.objects.get_or_create(
            knowledge=knowledge,
            version=version,
            defaults={'space': knowledge.space}
        )
        if (
            not created
            and job.status == KnowledgeIndexingJob.Status.INDEXED
            and job.chunks.filter(invalidated_at__isnull=True).exists()
        ):
            return job

        now = timezone.now()
        KnowledgeIndexChunk.objects.filter(
            job__knowledge=knowledge
        ).exclude(job=job).filter(
            invalidated_at__isnull=True
        ).update(invalidated_at=now)
        KnowledgeIndexingJob.objects.filter(
            knowledge=knowledge
        ).exclude(pk=job.pk).filter(
            status__in=(
                KnowledgeIndexingJob.Status.PENDING,
                KnowledgeIndexingJob.Status.INDEXED
            )
        ).update(status=KnowledgeIndexingJob.Status.OBSOLETE)
        # Chunks are a rebuildable materialization. Remove prior rows so a
        # failed job can be retried without violating its position constraint.
        KnowledgeIndexChunk.objects.filter(job=job).delete()
        job.status = KnowledgeIndexingJob.Status.PENDING
        job.attempt_count += 1
        job.error_message = ''
        job.started_at = now
        job.completed_at = None
        job.save(update_fields=(
            'status', 'attempt_count', 'error_message', 'started_at',
            'completed_at', 'update_date'
        ))

        try:
            drafts = chunk_content(version.content)
            channel = knowledge.source_message.chat_session.space_channel
            KnowledgeIndexChunk.objects.bulk_create([
                KnowledgeIndexChunk(
                    job=job,
                    space=knowledge.space,
                    knowledge=knowledge,
                    version=version,
                    source_message=knowledge.source_message,
                    chunk_index=draft.index,
                    content=draft.content,
                    start_offset=draft.start_offset,
                    end_offset=draft.end_offset,
                    source_author=knowledge.source_message.user.username,
                    source_channel_id=channel.pk,
                    source_message_created_at=knowledge.source_message.create_date
                )
                for draft in drafts
            ])
            job.status = KnowledgeIndexingJob.Status.INDEXED
            job.completed_at = timezone.now()
            job.save(update_fields=('status', 'completed_at', 'update_date'))
        except Exception as error:
            job.status = KnowledgeIndexingJob.Status.FAILED
            job.error_message = str(error)[:4000]
            job.completed_at = timezone.now()
            job.save(update_fields=('status', 'error_message', 'completed_at', 'update_date'))
        return job


def schedule_knowledge_indexing(knowledge_id: int):
    """Materialize chunks now and enqueue embedding work after commit."""
    job = index_knowledge(knowledge_id)
    if job is None:
        return None

    def enqueue():
        from .tasks import embed_indexing_job_task
        embed_indexing_job_task.delay(job.pk)

    transaction.on_commit(enqueue)
    return job


def eligible_indexed_chunks(space, knowledge_id=None):
    """Return only chunks whose source is currently retrievable knowledge."""
    filters = Q(
        space=space,
        job__status=KnowledgeIndexingJob.Status.INDEXED,
        invalidated_at__isnull=True,
        knowledge__status=PreservedKnowledge.Status.ACTIVE,
        knowledge__current_version_id=F('version_id'),
        source_message__deleted_at__isnull=True
    )
    if knowledge_id is not None:
        filters &= Q(knowledge_id=knowledge_id)
    return KnowledgeIndexChunk.objects.filter(filters).select_related(
        'knowledge', 'version', 'source_message', 'job'
    ).order_by('knowledge_id', 'version_id', 'chunk_index')
