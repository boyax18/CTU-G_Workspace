"""WF-03.02 staged role-permission management API (isolated review modes ONLY).

This API is deliberately NOT mounted by config.urls. Display does not imply
mutation authorization; existing delegated mutation services are the sole
write path, with their transaction, actor, policy, writer, and audit guards.
"""

from django.conf import settings
from django.db import DatabaseError
from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.registration_review_api import (
    RegistrationReviewAPI, ReviewAPIUnavailable, ReviewBurstThrottle, ReviewListThrottle,
)
from .delegation import (
    ROLE_PERMISSION_MANAGE, DelegationPolicyUnavailable, PermissionManagementDenied,
    PermissionManagementValidationError, is_governance_permission,
    is_reserved_role, require_delegation,
)
from .executor.client import enabled as executor_enabled
from .models import AccountRole, Permission, Role, RolePermission
from .mutations import RolePermissionStateConflict, grant_role_permission, revoke_role_permission
from .technical_admin import has_technical_authority
from .writer_boundary import WriterBoundaryUnavailable

MAX_ROLES = 128
MAX_PERMISSIONS = 1024
MAX_ID = 2_147_483_647


def _get_role(role_id):
    if type(role_id) is not int or not 1 <= role_id <= MAX_ID:
        raise exceptions.NotFound()
    role = Role.objects.filter(pk=role_id).first()
    if role is None:
        raise exceptions.NotFound()
    return role


def _get_permission(permission_id):
    if type(permission_id) is not int or not 1 <= permission_id <= MAX_ID:
        raise exceptions.NotFound()
    permission = Permission.objects.select_related('service').filter(pk=permission_id).first()
    if permission is None:
        raise exceptions.NotFound()
    return permission


def _change_allowed(actor, role, permission, actor_role_ids, allow_mutation):
    """UI hint only; the mutation service must reauthorize inside its locks."""
    if (not allow_mutation or not role.is_active or is_reserved_role(role.role_name)
            or role.pk in actor_role_ids or not permission.service.is_active
            or is_governance_permission(permission)):
        return False
    try:
        scope = require_delegation(actor, permission)
        return role.role_name in scope.role_names
    except (PermissionManagementDenied, PermissionManagementValidationError):
        return False


class RolePermissionAPI(RegistrationReviewAPI):
    """Inherit explicit CSRF, safe JSON parser, rate limits and no-store headers."""

    def review_gate_open(self):
        return getattr(settings, 'WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED', False) is True

    def initial(self, request, *args, **kwargs):
        # The executor's current role-permission contract has not been approved
        # for this new browser API. Refuse reads AND writes under that profile.
        if executor_enabled():
            raise ReviewAPIUnavailable()
        return super().initial(request, *args, **kwargs)

    def require_technical(self, request):
        actor = self.require_actor(request, ROLE_PERMISSION_MANAGE)
        if not has_technical_authority(actor, ROLE_PERMISSION_MANAGE):
            raise exceptions.PermissionDenied('Technical Super Admin authority required.')
        return actor

    def handle_exception(self, exc):
        if isinstance(exc, RolePermissionStateConflict):
            return Response({'error': {'code': 'state_changed',
                                       'message': 'Reload permission assignments before changing them.'}}, status=409)
        if isinstance(exc, DelegationPolicyUnavailable):
            exc = ReviewAPIUnavailable()
        elif isinstance(exc, PermissionManagementDenied):
            exc = exceptions.PermissionDenied()
        elif isinstance(exc, PermissionManagementValidationError):
            exc = exceptions.ValidationError('Invalid permission change.')
        elif isinstance(exc, (WriterBoundaryUnavailable, DatabaseError)):
            exc = ReviewAPIUnavailable()
        return super().handle_exception(exc)


class RolePermissionRolesView(RolePermissionAPI):
    http_method_names = ['get', 'head', 'options']
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        self.require_technical(request)
        if request.query_params:
            raise exceptions.ValidationError('Unsupported query fields.')
        roles = list(Role.objects.order_by('role_name', 'role_id')[:MAX_ROLES + 1])
        if len(roles) > MAX_ROLES:
            raise ReviewAPIUnavailable()
        return Response({'roles': [
            {'role_id': role.pk, 'role_name': role.role_name, 'is_active': role.is_active,
             'protected': is_reserved_role(role.role_name)} for role in roles
        ]})


class RolePermissionListView(RolePermissionAPI):
    http_method_names = ['get', 'head', 'options']
    throttle_classes = [ReviewListThrottle]

    def get(self, request, role_id):
        actor = self.require_technical(request)
        if request.query_params:
            raise exceptions.ValidationError('Unsupported query fields.')
        role = _get_role(role_id)
        all_permissions = list(Permission.objects.select_related('service')
                               .order_by('permission_code', 'permission_id')[:MAX_PERMISSIONS + 1])
        if len(all_permissions) > MAX_PERMISSIONS:
            raise ReviewAPIUnavailable()
        bound_ids = set(RolePermission.objects.filter(role=role, is_active=True)
                        .values_list('permission_id', flat=True))
        actor_role_ids = set(AccountRole.objects.filter(account=actor).values_list('role_id', flat=True))
        allow_mutation = getattr(settings, 'WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED', False) is True
        results = [
            {'permission_id': permission.pk, 'permission_code': permission.permission_code,
             'permission_name': permission.permission_name, 'service_code': permission.service.service_code,
             'assigned': permission.pk in bound_ids,
             'change_allowed': _change_allowed(actor, role, permission, actor_role_ids, allow_mutation)}
            for permission in all_permissions
        ]
        return Response({'role_id': role.pk, 'role_name': role.role_name, 'permissions': results})


class RolePermissionChangeView(RolePermissionAPI):
    http_method_names = ['post', 'options']
    throttle_classes = [ReviewBurstThrottle]

    def post(self, request, role_id, permission_id, action):
        actor = self.require_technical(request)
        if getattr(settings, 'WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED', False) is not True:
            raise ReviewAPIUnavailable()
        if action not in ('grant', 'revoke'):
            raise exceptions.NotFound()
        body = request.data
        if (type(body) is not dict or set(body) != {'expected_active'}
                or type(body['expected_active']) is not bool):
            raise exceptions.ValidationError('Provide exactly expected_active as a boolean.')
        role = _get_role(role_id)
        permission = _get_permission(permission_id)
        # These fast checks are only an early refusal. The existing mutation
        # service repeats the authoritative checks after locking DB state.
        actor_role_ids = set(AccountRole.objects.filter(account=actor).values_list('role_id', flat=True))
        if not _change_allowed(actor, role, permission, actor_role_ids, True):
            raise exceptions.PermissionDenied('Permission assignment not allowed.')
        present = RolePermission.objects.filter(role=role, permission=permission, is_active=True).exists()
        if present is not body['expected_active'] or present is (action == 'grant'):
            return Response({'error': {'code': 'state_changed',
                                       'message': 'Reload permission assignments before changing them.'}}, status=409)
        if action == 'grant':
            changed = grant_role_permission(actor=actor, role=role, permission=permission, expected_active=body['expected_active'])
        else:
            changed = revoke_role_permission(actor=actor, role=role, permission=permission, expected_active=body['expected_active'])
        return Response({'role_id': role.pk, 'permission_id': permission.pk,
                         'active': action == 'grant', 'changed': bool(changed)})
