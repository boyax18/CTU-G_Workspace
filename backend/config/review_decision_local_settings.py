"""Local WF-02 decision profile with account-status writes and SMTP disabled."""

from .review_local_settings import *  # noqa: F401,F403 -- inherits the loopback and explicit local guards

ROOT_URLCONF = "config.review_decision_local_urls"

# Keep account management reads available while omitting its status-write routes.
WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = True
WORKSPACE_ACCOUNT_DIRECTORY_ENABLED = True
WORKSPACE_ACCOUNT_STATUS_ENABLED = False
