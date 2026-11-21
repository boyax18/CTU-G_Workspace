"""WF-03.02 isolated local-review and sandbox-only routes; never config.urls."""
from django.urls import path
from .role_permission_api import RolePermissionChangeView, RolePermissionListView, RolePermissionRolesView

urlpatterns = [
    path('roles/', RolePermissionRolesView.as_view(), name='wf0302-roles'),
    path('roles/<int:role_id>/permissions/', RolePermissionListView.as_view(), name='wf0302-role-permissions'),
    path('roles/<int:role_id>/permissions/<int:permission_id>/<str:action>/',
         RolePermissionChangeView.as_view(), name='wf0302-role-permission-change'),
]
