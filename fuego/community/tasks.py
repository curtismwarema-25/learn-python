"""Durable Celery entry points for knowledge embeddings."""

from fuego.celery import app as celery_app

from .embedding_pipeline import embed_indexing_job
from .embeddings import EmbeddingProviderError


@celery_app.task(bind=True, max_retries=4, name='community.embed_indexing_job')
def embed_indexing_job_task(self, job_id, provider_name=None):
    """Process one job with bounded exponential retry backoff."""
    try:
        job = embed_indexing_job(job_id, provider_name=provider_name)
    except EmbeddingProviderError as error:
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(
            exc=error,
            countdown=min(2 ** self.request.retries, 60)
        )
    return {
        'job_id': job.pk,
        'status': job.embedding_status
    }
