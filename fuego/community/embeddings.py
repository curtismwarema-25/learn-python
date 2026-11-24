"""Provider-independent embedding contracts and the local test provider."""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import Sequence

from django.conf import settings


class EmbeddingProviderError(Exception):
    """Base error raised when an embedding provider cannot serve a request."""


class RetryableEmbeddingProviderError(EmbeddingProviderError):
    """Provider failure that should be retried by the worker."""


class EmbeddingProvider(ABC):
    provider_name: str
    model: str
    dimensions: int

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = [self.embed(text) for text in texts]
        if len(vectors) != len(texts):
            raise EmbeddingProviderError('Provider returned the wrong batch size.')
        return vectors

    def validate_vector(self, vector: Sequence[float]) -> list[float]:
        if len(vector) != self.dimensions:
            raise EmbeddingProviderError(
                'Provider returned %s dimensions; expected %s.'
                % (len(vector), self.dimensions)
            )
        validated = []
        for value in vector:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EmbeddingProviderError('Provider returned a non-numeric vector value.')
            if not math.isfinite(value):
                raise EmbeddingProviderError('Provider returned a non-finite vector value.')
            validated.append(float(value))
        return validated


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline provider for development and tests."""

    provider_name = 'fake'

    def __init__(self, model=None, dimensions=None):
        self.model = model or settings.FUEGO_EMBEDDING_MODEL
        self.dimensions = dimensions or settings.FUEGO_EMBEDDING_DIMENSIONS
        if self.dimensions <= 0:
            raise EmbeddingProviderError('Embedding dimensions must be positive.')

    def embed(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise EmbeddingProviderError('Cannot embed empty text.')
        values = []
        counter = 0
        while len(values) < self.dimensions:
            digest = hashlib.sha256(
                ('%s:%s:%s' % (self.model, counter, text)).encode('utf-8')
            ).digest()
            values.extend((byte / 127.5) - 1.0 for byte in digest)
            counter += 1
        return self.validate_vector(values[:self.dimensions])


def get_embedding_provider(name=None) -> EmbeddingProvider:
    provider_name = name or settings.FUEGO_EMBEDDING_PROVIDER
    if provider_name == 'fake':
        return FakeEmbeddingProvider()
    raise EmbeddingProviderError(
        'Embedding provider %r is not configured. External providers require an explicit adapter.'
        % provider_name
    )
