# dashboards/views.py
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdmin, IsInstructorOrAdmin, IsStudent
from classes.models import Class
from groups.models import GroupMembership
from ratings.models import RatingPeriod, RatingSubmission
from ratings.scope import student_periods, visible_periods


def display_name(user):
    return user.get_full_name() or user.username


class StudentDashboardView(APIView):
    """The student's own sessions. Shows their own submission state only."""
    permission_classes = [IsStudent]

    def get(self, request):
        periods = student_periods(request.user).select_related("classroom").distinct()
        memberships = {
            m.period_id: m for m in GroupMembership.objects.filter(student=request.user)
        }
        submitted_ids = set(
            RatingSubmission.objects.filter(
                rater=request.user, submitted_at__isnull=False
            ).values_list("period_id", flat=True)
        )
        data = []
        for p in periods:
            membership = memberships.get(p.id)
            data.append({
                "id": p.id,
                "title": p.title,
                "class_code": p.classroom.code,
                "status": p.status,
                "deadline": p.deadline,
                "in_group": membership is not None,
                "is_leader": bool(membership and membership.is_group_leader),
                "submitted": p.id in submitted_ids,
            })
        return Response(data)


class InstructorDashboardView(APIView):
    """Sessions in the instructor's classes, with who has submitted."""
    permission_classes = [IsInstructorOrAdmin]

    def get(self, request):
        periods = visible_periods(request.user).select_related("classroom").order_by("-created_at")
        data = []
        for p in periods:
            members = list(
                GroupMembership.objects.filter(period=p).select_related("student", "group")
            )
            submitted_ids = set(
                RatingSubmission.objects.filter(
                    period=p, submitted_at__isnull=False
                ).values_list("rater_id", flat=True)
            )
            data.append({
                "id": p.id,
                "title": p.title,
                "class_code": p.classroom.code,
                "status": p.status,
                "deadline": p.deadline,
                "total_raters": len(members),
                "submitted_count": sum(1 for m in members if m.student_id in submitted_ids),
                "members": [
                    {
                        "id": m.student_id,
                        "name": display_name(m.student),
                        "group": m.group.name,
                        "is_leader": m.is_group_leader,
                        "submitted": m.student_id in submitted_ids,
                    }
                    for m in members
                ],
            })
        return Response(data)


class AdminDashboardView(APIView):
    """System totals. Counts only, no individual ratings."""
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "users_by_role": {
                role: User.objects.filter(role=role).count()
                for role, _label in User.Role.choices
            },
            "classes": Class.objects.count(),
            "sessions": {
                "total": RatingPeriod.objects.count(),
                "open": RatingPeriod.objects.filter(status=RatingPeriod.Status.OPEN).count(),
            },
            "submissions": RatingSubmission.objects.filter(submitted_at__isnull=False).count(),
        })