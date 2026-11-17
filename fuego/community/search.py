"""Permission-scoped search over existing Space conversations and resources."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from heapq import merge
from itertools import islice
import re
from typing import Iterator
from urllib.parse import urlsplit

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from chat.models import ChatSessionMessage

from .models import Resource


ITERATOR_CHUNK_SIZE = 100
RESULT_EXCERPT_LENGTH = 240
SEARCH_TERM_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class SearchHit:
    content_type: str
    source_id: str
    sort_id: int | str
    title: str
    excerpt: str
    created_at: datetime
    author: str | None
    channel_id: str | None
    channel_name: str | None
    channel_archived: bool | None
    source_domain: str | None
    relevance: int


@dataclass(frozen=True)
class SearchPage:
    count: int
    page: int
    page_size: int
    total_pages: int
    results: list[SearchHit]


def _terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        SEARCH_TERM_PATTERN.findall(query.casefold())
    ))


def _all_terms_match(fields: tuple[str, ...], terms: tuple[str, ...]) -> Q:
    condition = Q()
    for term in terms:
        term_condition = Q()
        for field in fields:
            term_condition |= Q(**{f'{field}__icontains': term})
        condition &= term_condition
    return condition


def _apply_date_range(queryset, start_date, end_date):
    current_timezone = timezone.get_current_timezone()
    if start_date is not None:
        lower_bound = timezone.make_aware(
            datetime.combine(start_date, time.min),
            current_timezone
        )
        queryset = queryset.filter(create_date__gte=lower_bound)
    if end_date is not None and end_date < date.max:
        upper_bound = timezone.make_aware(
            datetime.combine(end_date + timedelta(days=1), time.min),
            current_timezone
        )
        queryset = queryset.filter(create_date__lt=upper_bound)
    return queryset


def _excerpt(text: str, terms: tuple[str, ...]) -> str:
    normalized = ' '.join(text.split())
    if len(normalized) <= RESULT_EXCERPT_LENGTH:
        return normalized

    lowered = normalized.casefold()
    positions = [
        position
        for term in terms
        if (position := lowered.find(term)) >= 0
    ]
    match_position = min(positions, default=0)
    start = max(0, min(
        match_position - RESULT_EXCERPT_LENGTH // 3,
        len(normalized) - RESULT_EXCERPT_LENGTH
    ))
    end = start + RESULT_EXCERPT_LENGTH
    return (
        ('…' if start else '')
        + normalized[start:end]
        + ('…' if end < len(normalized) else '')
    )


def _message_hits(queryset, terms: tuple[str, ...]) -> Iterator[SearchHit]:
    for message in queryset.iterator(chunk_size=ITERATOR_CHUNK_SIZE):
        channel = message.chat_session.space_channel
        yield SearchHit(
            content_type='discussion',
            source_id=str(message.pk),
            sort_id=message.pk,
            title=f'#{channel.name}',
            excerpt=_excerpt(message.message, terms),
            created_at=message.create_date,
            author=message.user.username,
            channel_id=str(channel.pk),
            channel_name=channel.name,
            channel_archived=channel.archived_at is not None,
            source_domain=None,
            relevance=message.relevance
        )


def _resource_hits(queryset, terms: tuple[str, ...]) -> Iterator[SearchHit]:
    for resource in queryset.iterator(chunk_size=ITERATOR_CHUNK_SIZE):
        domain = urlsplit(resource.external_url).hostname
        excerpt_text = resource.description or resource.external_url
        yield SearchHit(
            content_type='resource',
            source_id=str(resource.pk),
            sort_id=str(resource.pk),
            title=resource.title,
            excerpt=_excerpt(excerpt_text, terms),
            created_at=resource.create_date,
            author=(
                resource.created_by.username
                if resource.created_by_id is not None
                else None
            ),
            channel_id=None,
            channel_name=None,
            channel_archived=None,
            source_domain=domain,
            relevance=resource.relevance
        )


def _sort_key(hit: SearchHit):
    return (
        -hit.relevance,
        -hit.created_at.timestamp(),
        hit.content_type,
        hit.sort_id
    )


def search_space(
    *,
    space,
    query: str,
    content_type: str,
    channel=None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 20
) -> SearchPage:
    """Search active Space resources and readable channel history."""
    normalized_query = ' '.join(query.split())
    terms = _terms(normalized_query)

    message_queryset = ChatSessionMessage.objects.none()
    if content_type in {'all', 'discussions'}:
        message_queryset = (
            ChatSessionMessage.objects
            .filter(chat_session__space_channel__space_id=space.pk)
            .filter(_all_terms_match(('message',), terms))
            .select_related('user', 'chat_session__space_channel')
            .annotate(
                relevance=Case(
                    When(message__iexact=normalized_query, then=Value(500)),
                    When(message__icontains=normalized_query, then=Value(400)),
                    default=Value(100),
                    output_field=IntegerField()
                )
            )
        )
        if channel is not None:
            message_queryset = message_queryset.filter(
                chat_session__space_channel=channel
            )
        message_queryset = _apply_date_range(
            message_queryset,
            start_date,
            end_date
        ).order_by('-relevance', '-create_date', 'pk')

    resource_queryset = Resource.objects.none()
    if content_type in {'all', 'resources'}:
        resource_queryset = (
            Resource.objects
            .filter(space_id=space.pk, status=Resource.Status.ACTIVE)
            .filter(_all_terms_match(
                ('title', 'description', 'external_url'),
                terms
            ))
            .select_related('created_by')
            .annotate(
                relevance=Case(
                    When(title__iexact=normalized_query, then=Value(600)),
                    When(title__icontains=normalized_query, then=Value(500)),
                    When(description__icontains=normalized_query, then=Value(300)),
                    When(external_url__icontains=normalized_query, then=Value(200)),
                    default=Value(100),
                    output_field=IntegerField()
                )
            )
        )
        resource_queryset = _apply_date_range(
            resource_queryset,
            start_date,
            end_date
        ).order_by('-relevance', '-create_date', 'pk')

    count = message_queryset.count() + resource_queryset.count()
    total_pages = (count + page_size - 1) // page_size
    offset = (page - 1) * page_size
    if offset >= count:
        results = []
    else:
        message_results = _message_hits(message_queryset, terms)
        resource_results = _resource_hits(resource_queryset, terms)
        ordered_results = merge(
            message_results,
            resource_results,
            key=_sort_key
        )
        results = list(islice(ordered_results, offset, offset + page_size))

    return SearchPage(
        count=count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=results
    )
