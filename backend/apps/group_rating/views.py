from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.session_auth import _workspace_account
from apps.access_control.services import has_permission
from apps.accounts.models import Account

from .models import (
    IndividualResult,
    RatingActivity,
    RatingGroup,
    RatingMember,
    RatingSession,
    RatingSubmission,
)


def actor(request):
    account = _workspace_account(request.user)
    if account is None:
        raise exceptions.PermissionDenied("Authentication required.")
    return account


def require(account, code):
    if not has_permission(account, code):
        raise exceptions.PermissionDenied("Exact effective permission required.")


def account_name(account):
    profile = getattr(account, "profile", None)
    if profile is not None:
        name = " ".join(
            part for part in (
                getattr(profile, "first_name", ""),
                getattr(profile, "middle_name", ""),
                getattr(profile, "last_name", ""),
                getattr(profile, "suffix", ""),
            ) if part
        )
        if name:
            return name
    return account.school_id


class RatingWorkspaceView(APIView):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        account = actor(request)
        require(account, "group_rating.sheets.assigned.read")

        led_groups = RatingGroup.objects.filter(leader=account).select_related("session")
        memberships = RatingMember.objects.filter(account=account).select_related(
            "group", "group__session", "group__leader"
        )
        own_submission_ids = set(
            RatingSubmission.objects.filter(rater=account).values_list("session_id", flat=True)
        )

        sessions = {}
        for group in led_groups:
            sessions[group.session_id] = {
                "id": group.session_id,
                "title": group.session.title,
                "deadline": group.session.deadline.isoformat(),
                "status": group.session.status,
                "criteria": group.session.criteria,
                "role": "leader",
                "group": {"id": group.id, "name": group.name},
                "submitted": bool(group.session_id in own_submission_ids),
            }
        for membership in memberships:
            group = membership.group
            sessions[group.session_id] = {
                "id": group.session_id,
                "title": group.session.title,
                "deadline": group.session.deadline.isoformat(),
                "status": group.session.status,
                "criteria": group.session.criteria,
                "role": "student",
                "group": {"id": group.id, "name": group.name},
                "submitted": bool(group.session_id in own_submission_ids),
            }

        if has_permission(account, "group_rating.sheets.manage"):
            for session in RatingSession.objects.filter(created_by=account).order_by("-created_at"):
                sessions.setdefault(session.id, {
                    "id": session.id,
                    "title": session.title,
                    "deadline": session.deadline.isoformat(),
                    "status": session.status,
                    "criteria": session.criteria,
                    "role": "professor",
                    "group": None,
                    "submitted": False,
                })

        session_rows = sorted(sessions.values(), key=lambda item: item["deadline"])
        details = {}
        for row in session_rows:
            session = RatingSession.objects.filter(pk=row["id"]).first()
            if session is None:
                continue
            is_professor = session.created_by_id == account.pk
            is_leader = RatingGroup.objects.filter(session=session, leader=account).exists()
            membership = RatingMember.objects.filter(
                group__session=session, account=account
            ).select_related("group").first()

            own_result = IndividualResult.objects.filter(
                session=session, student=account, released_at__isnull=False
            ).first()

            groups = []
            for group in session.groups.select_related("leader").all():
                members = RatingMember.objects.filter(group=group).select_related(
                    "account", "account__profile"
                )
                member_rows = [
                    {
                        "school_id": member.account.school_id,
                        "name": account_name(member.account),
                    }
                    for member in members
                ]
                submitted_ids = set(
                    RatingSubmission.objects.filter(session=session, group=group).values_list(
                        "rater__school_id", flat=True
                    )
                )
                if is_professor or is_leader:
                    groups.append({
                        "id": group.pk,
                        "name": group.name,
                        "leader": {
                            "school_id": group.leader.school_id,
                            "name": account_name(group.leader),
                        },
                        "members": member_rows,
                        "submission_count": len(submitted_ids),
                        "member_count": len(member_rows),
                        "submitted_school_ids": sorted(submitted_ids),
                    })
                elif membership is not None and membership.group_id == group.pk:
                    groups.append({
                        "id": group.pk,
                        "name": group.name,
                        "leader": {
                            "school_id": group.leader.school_id,
                            "name": account_name(group.leader),
                        },
                        "members": [
                            item for item in member_rows
                            if item["school_id"] != account.school_id
                        ],
                    })

            details[row["id"]] = {
                "groups": groups,
                "own_result": None if own_result is None else {
                    "scores": own_result.scores,
                    "final_score": str(own_result.final_score),
                    "released_at": own_result.released_at.isoformat(),
                },
            }

        return Response({
            "sessions": session_rows,
            "details": details,
            "capabilities": {
                "create": has_permission(account, "group_rating.sheets.manage")
                    and has_permission(account, "group_rating.criteria.manage"),
                "publish": has_permission(account, "group_rating.invitations.manage"),
            },
        })


class RatingSessionView(APIView):
    http_method_names = ["post", "options"]

    def post(self, request):
        account = actor(request)
        require(account, "group_rating.sheets.manage")
        require(account, "group_rating.criteria.manage")
        data = request.data
        if not isinstance(data, dict):
            raise exceptions.ParseError("Expected a JSON object.")
        title = str(data.get("title", "")).strip()
        deadline = data.get("deadline")
        criteria = data.get("criteria")
        if not title or not deadline or not isinstance(criteria, list):
            raise exceptions.ValidationError("Title, deadline and criteria are required.")
        criteria = [str(item).strip() for item in criteria if str(item).strip()]
        if not criteria:
            raise exceptions.ValidationError("At least one rating criterion is required.")
        try:
            from django.utils.dateparse import parse_datetime
            deadline_dt = parse_datetime(str(deadline))
            if deadline_dt is None:
                raise ValueError
        except (TypeError, ValueError):
            raise exceptions.ValidationError("Deadline must be a valid ISO date and time.")
        with transaction.atomic():
            session = RatingSession.objects.create(
                title=title,
                deadline=deadline_dt,
                criteria=criteria,
                created_by=account,
                status="draft",
            )
            RatingActivity.objects.create(
                session=session, actor=account, action="session_created",
                detail={"title": title},
            )
        return Response({"session": {"id": session.id, "title": session.title}}, status=201)


class RatingMemberView(APIView):
    http_method_names = ["post", "options"]

    def post(self, request, session_id):
        account = actor(request)
        require(account, "group_rating.members.manage")
        try:
            session = RatingSession.objects.get(pk=session_id)
        except RatingSession.DoesNotExist:
            raise exceptions.NotFound("Rating session unavailable.")
        group = RatingGroup.objects.filter(session=session, leader=account).first()
        if group is None:
            raise exceptions.PermissionDenied("You are not the leader of this rating group.")
        if session.status not in {"draft", "published"} or session.deadline <= timezone.now():
            raise exceptions.PermissionDenied("The member list can no longer be changed.")
        data = request.data
        school_ids = data.get("school_ids") if isinstance(data, dict) else None
        if not isinstance(school_ids, list):
            raise exceptions.ValidationError("school_ids must be a list.")
        accounts = list(Account.objects.filter(school_id__in=[str(x) for x in school_ids]))
        found = {item.school_id for item in accounts}
        missing = [str(x) for x in school_ids if str(x) not in found]
        if missing:
            raise exceptions.ValidationError({"school_ids": [f"Unknown school ID: {missing[0]}"]})
        with transaction.atomic():
            RatingMember.objects.filter(group=group).exclude(account__in=accounts).delete()
            for member in accounts:
                RatingMember.objects.get_or_create(group=group, account=member)
            RatingActivity.objects.create(
                session=session, actor=account, action="members_confirmed",
                detail={"member_count": len(accounts)},
            )
        return Response({"confirmed": len(accounts)})


class RatingPublishView(APIView):
    http_method_names = ["post", "options"]

    def post(self, request, session_id):
        account = actor(request)
        require(account, "group_rating.sheets.manage")
        require(account, "group_rating.invitations.manage")
        try:
            session = RatingSession.objects.get(pk=session_id, created_by=account)
        except RatingSession.DoesNotExist:
            raise exceptions.PermissionDenied("Rating session unavailable.")
        data = request.data
        groups = data.get("groups") if isinstance(data, dict) else None
        if not isinstance(groups, list):
            raise exceptions.ValidationError("groups must be a list.")
        with transaction.atomic():
            for item in groups:
                if not isinstance(item, dict):
                    raise exceptions.ValidationError("Each group must be an object.")
                name = str(item.get("name", "")).strip()
                school_id = str(item.get("leader_school_id", "")).strip()
                if not name or not school_id:
                    raise exceptions.ValidationError("Group name and leader school ID are required.")
                leader = Account.objects.filter(school_id=school_id).first()
                if leader is None:
                    raise exceptions.ValidationError({"leader_school_id": ["Unknown school ID."]})
                RatingGroup.objects.update_or_create(
                    session=session,
                    leader=leader,
                    defaults={"name": name},
                )
            session.status = "published"
            session.save(update_fields=["status", "updated_at"])
            RatingActivity.objects.create(
                session=session, actor=account, action="session_published",
                detail={"group_count": len(groups)},
            )
        return Response({"published": True, "group_count": len(groups)})


class RatingSubmissionView(APIView):
    http_method_names = ["post", "options"]

    def post(self, request, session_id):
        account = actor(request)
        require(account, "group_rating.submissions.self.manage")
        try:
            session = RatingSession.objects.get(pk=session_id)
            membership = RatingMember.objects.select_related("group").get(
                group__session=session, account=account
            )
        except RatingSession.DoesNotExist:
            raise exceptions.NotFound("Rating session unavailable.")
        except RatingMember.DoesNotExist:
            raise exceptions.PermissionDenied("You are not in a group for this session.")
        if session.status != "published":
            raise exceptions.PermissionDenied("This rating session is not open.")
        if timezone.now() > session.deadline:
            raise exceptions.PermissionDenied("The rating deadline has passed.")
        if RatingSubmission.objects.filter(session=session, rater=account).exists():
            raise exceptions.PermissionDenied("This rating submission is already locked.")
        data = request.data
        ratings = data.get("ratings") if isinstance(data, dict) else None
        if not isinstance(ratings, dict):
            raise exceptions.ValidationError("ratings must be an object.")
        targets = list(
            RatingMember.objects.filter(group=membership.group)
            .exclude(account=account)
            .values_list("account__school_id", flat=True)
        )
        for target in targets:
            values = ratings.get(target)
            if not isinstance(values, dict):
                raise exceptions.ValidationError("A rating row is required for every group member.")
            for criterion in session.criteria:
                value = values.get(criterion)
                if type(value) is not int or value < 1 or value > 5:
                    raise exceptions.ValidationError("Ratings must be whole numbers from 1 to 5.")
        with transaction.atomic():
            submission = RatingSubmission.objects.create(
                session=session,
                rater=account,
                group=membership.group,
                ratings=ratings,
            )
            RatingActivity.objects.create(
                session=session, actor=account, action="ratings_submitted",
                detail={"submission_id": submission.id},
            )
        return Response({"submitted": True})


class RatingReleaseView(APIView):
    http_method_names = ["post", "options"]

    def post(self, request, session_id):
        account = actor(request)
        require(account, "group_rating.results.assigned.read")
        try:
            session = RatingSession.objects.get(pk=session_id, created_by=account)
        except RatingSession.DoesNotExist:
            raise exceptions.PermissionDenied("Rating session unavailable.")
        with transaction.atomic():
            for group in session.groups.all():
                members = RatingMember.objects.filter(group=group)
                for member in members.select_related("account"):
                    student = member.account
                    incoming = []
                    for submission in session.submissions.filter(group=group).exclude(rater=student):
                        incoming.append(submission.ratings.get(student.school_id, {}))
                    if not incoming:
                        continue
                    criterion_scores = {}
                    for criterion in session.criteria:
                        values = [
                            row.get(criterion)
                            for row in incoming
                            if type(row.get(criterion)) is int
                        ]
                        criterion_scores[criterion] = (
                            round(sum(values) / len(values), 2) if values else 0
                        )
                    final_score = (
                        round(sum(criterion_scores.values()) / len(criterion_scores), 2)
                        if criterion_scores else 0
                    )
                    IndividualResult.objects.update_or_create(
                        session=session,
                        student=student,
                        group=group,
                        defaults={
                            "scores": criterion_scores,
                            "final_score": final_score,
                            "released_at": timezone.now(),
                        },
                    )
            session.status = "released"
            session.save(update_fields=["status", "updated_at"])
            RatingActivity.objects.create(
                session=session, actor=account, action="results_released",
                detail={},
            )
        return Response({"released": True})
