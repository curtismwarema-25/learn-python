"""Shared Space role checks."""

from .models import SpaceMembership


OWNER = 'owner'
ADMINISTRATOR = SpaceMembership.Role.ADMINISTRATOR
MODERATOR = SpaceMembership.Role.MODERATOR
MEMBER = SpaceMembership.Role.MEMBER
MANAGER_ROLES = {OWNER, ADMINISTRATOR}


def get_space_role(space, user):
    """Return the caller's Space role, or None when they are not a member."""
    if not getattr(user, 'is_authenticated', False):
        return None
    if space.owner_id == user.pk:
        return OWNER
    return (
        SpaceMembership.objects
        .filter(space=space, user_id=user.pk)
        .values_list('role', flat=True)
        .first()
    )


def is_space_manager(space, user):
    return get_space_role(space, user) in MANAGER_ROLES
