#!/usr/bin/env python3
"""Inspect or watch one GitHub PR's automated-review state through gh CLI."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows hosts
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - exercised on POSIX hosts
    msvcrt = None


PR_URL_RE = re.compile(r"^https://github\.com/([^/]+/[^/]+)/pull/(\d+)(?:/.*)?$")
REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
CONNECTOR_MARKERS = ("chatgpt-codex-connector",)
CLEAN_RESPONSE_MARKERS = (
    "didn't find any major issues",
    "did not find any major issues",
    "no major issues found",
)
REVIEWED_COMMIT_RE = re.compile(r"reviewed commit:\s*`?([0-9a-f]{7,40})", re.IGNORECASE)
REVIEW_HEAD_RE = re.compile(r"review head:\s*`?([0-9a-f]{7,40})", re.IGNORECASE)
RETRY_AFTER_RE = re.compile(r"retry[- ]after[:= ]+(\d+)", re.IGNORECASE)
RATE_LIMIT_MARKERS = (
    "rate limit",
    "rate_limit",
    "api rate limit exceeded",
)
SECONDARY_RATE_LIMIT_MARKERS = (
    "secondary rate limit",
    "abuse detection",
)
TERMINAL_OUTCOMES = {
    "passed",
    "review_feedback",
    "review_response",
    "pagination_incomplete",
    "rate_limited",
    "budget_exhausted",
    "preflight_unavailable",
    "observer_unavailable",
}
REQUIRED_CONNECTIONS = (
    "comments",
    "reviews",
    "review_threads",
    "pull_request_reactions",
    "request_reactions",
    "check_contexts",
)


class GhError(RuntimeError):
    pass


class GhTimeout(GhError):
    pass


@dataclass
class InspectionStop(RuntimeError):
    outcome: str
    reason: str
    connection: str | None = None
    cursor: str | None = None
    retry_after: int | None = None

    def __str__(self) -> str:
        return self.reason


@dataclass
class InspectionConfig:
    reserve: int = 200
    query_cost_buffer: int = 5
    max_requests: int = 40
    max_pages: int = 20
    max_seconds: float = 90.0
    page_size: int = 100


@dataclass
class GraphQLSession:
    config: InspectionConfig
    runner: Callable[[list[str], float | None], str]
    monotonic: Callable[[], float] = time.monotonic
    deadline: float | None = None
    started_at: float = field(init=False)
    preflight_done: bool = False
    preflight: dict[str, Any] = field(default_factory=dict)
    request_count: int = 0
    total_cost: int = 0
    last_rate_limit: dict[str, Any] = field(default_factory=dict)
    operations: list[dict[str, Any]] = field(default_factory=list)
    page_counts: dict[str, int] = field(default_factory=dict)
    status: str = "ok"
    stop_reason: str | None = None
    retry_after: int | None = None
    query_seconds: float = 0.0

    def __post_init__(self) -> None:
        self.started_at = self.monotonic()

    def run_preflight(self) -> None:
        if self.preflight_done:
            return
        self.preflight_done = True
        timeout = self._remaining_timeout()
        if timeout <= 0:
            self._stop(
                "budget_exhausted",
                "inspection deadline reached before REST rate-limit preflight",
            )
        try:
            raw = self.runner(["api", "rate_limit", "--include"], timeout)
            _, body = parse_included_response(raw)
            payload = parse_json_output(body)
            graphql = ((payload.get("resources") or {}).get("graphql") or {})
            reset_at = graphql.get("reset")
            self.preflight = {
                "limit": graphql.get("limit"),
                "cost": None,
                "remaining": graphql.get("remaining"),
                "used": graphql.get("used"),
                "reset_at": epoch_to_iso(reset_at),
                "source": "rest_rate_limit",
            }
            if graphql.get("remaining") is None:
                self.preflight["error"] = "REST rate-limit response omitted GraphQL remaining quota"
                self._stop(
                    "preflight_unavailable",
                    "REST GraphQL-quota preflight omitted the remaining value",
                )
            elif int(graphql["remaining"]) < (
                self.config.reserve + self.config.query_cost_buffer
            ):
                self._stop(
                    "rate_limited",
                    "GraphQL remaining quota "
                    f"({graphql['remaining']}) cannot preserve reserve ({self.config.reserve}) "
                    f"plus query-cost buffer ({self.config.query_cost_buffer})",
                )
        except InspectionStop:
            raise
        except GhTimeout as error:
            self._stop("budget_exhausted", str(error))
        except (GhError, TypeError, ValueError) as error:
            detail = str(error)
            if isinstance(error, GhError) and is_rate_limit_error(detail):
                kind = "secondary" if is_secondary_rate_limit(detail) else "primary"
                self._stop(
                    "rate_limited",
                    f"GitHub {kind} rate limit stopped REST preflight: {detail}",
                    retry_after=parse_retry_after(detail),
                )
            self.preflight = {
                "limit": None,
                "cost": None,
                "remaining": None,
                "used": None,
                "reset_at": None,
                "source": "rest_rate_limit",
                "error": detail,
            }
            self._stop(
                "preflight_unavailable",
                f"REST GraphQL-quota preflight failed closed: {detail}",
            )

    def _stop(
        self,
        outcome: str,
        reason: str,
        *,
        connection: str | None = None,
        cursor: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.status = outcome
        self.stop_reason = reason
        self.retry_after = retry_after
        raise InspectionStop(
            outcome,
            reason,
            connection=connection,
            cursor=cursor,
            retry_after=retry_after,
        )

    def _guard(self, connection: str | None, cursor: str | None) -> None:
        if self.status != "ok":
            self._stop(
                self.status,
                self.stop_reason or "inspection session has already stopped",
                connection=connection,
                cursor=cursor,
                retry_after=self.retry_after,
            )
        if self.request_count >= self.config.max_requests:
            self._stop(
                "budget_exhausted",
                f"GraphQL request ceiling ({self.config.max_requests}) reached",
                connection=connection,
                cursor=cursor,
            )
        if self._remaining_timeout() <= 0:
            self._stop(
                "budget_exhausted",
                f"inspection execution/deadline ceiling ({self.config.max_seconds:g}s) reached",
                connection=connection,
                cursor=cursor,
            )
        remaining = self.last_rate_limit.get("remaining")
        if remaining is None:
            remaining = self.preflight.get("remaining")
        if remaining is not None and int(remaining) < (
            self.config.reserve + self.config.query_cost_buffer
        ):
            self._stop(
                "rate_limited",
                "GraphQL remaining quota "
                f"({remaining}) cannot preserve reserve ({self.config.reserve}) "
                f"plus query-cost buffer ({self.config.query_cost_buffer})",
                connection=connection,
                cursor=cursor,
            )

    def _remaining_timeout(self) -> float:
        remaining = self.config.max_seconds - self.query_seconds
        if self.deadline is not None:
            remaining = min(remaining, self.deadline - self.monotonic())
        return max(0.0, remaining)

    def graphql(
        self,
        operation: str,
        query: str,
        variables: dict[str, Any],
        *,
        connection: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        self.run_preflight()
        self._guard(connection, cursor)
        arguments = ["api", "graphql", "--include", "-f", f"query={query}"]
        for key, value in variables.items():
            if value is None:
                continue
            flag = "-F" if isinstance(value, (bool, int)) else "-f"
            rendered = str(value).lower() if isinstance(value, bool) else str(value)
            arguments.extend([flag, f"{key}={rendered}"])
        self.request_count += 1
        query_started = self.monotonic()
        try:
            raw = self.runner(arguments, self._remaining_timeout())
        except GhTimeout as error:
            self.query_seconds += self.monotonic() - query_started
            self.operations.append({
                "operation": operation,
                "cost": None,
                "remaining": None,
                "used": None,
                "reset_at": None,
                "error": str(error),
            })
            self._stop(
                "budget_exhausted",
                str(error),
                connection=connection,
                cursor=cursor,
            )
        except GhError as error:
            self.query_seconds += self.monotonic() - query_started
            detail = str(error)
            if is_rate_limit_error(detail):
                self.operations.append({
                    "operation": operation,
                    "cost": None,
                    "remaining": None,
                    "used": None,
                    "reset_at": None,
                    "error": detail,
                })
                retry_after = parse_retry_after(detail)
                kind = "secondary" if is_secondary_rate_limit(detail) else "primary"
                self._stop(
                    "rate_limited",
                    f"GitHub {kind} rate limit stopped {operation}: {detail}",
                    connection=connection,
                    cursor=cursor,
                    retry_after=retry_after,
                )
            raise
        self.query_seconds += self.monotonic() - query_started

        _, body = parse_included_response(raw)
        payload = parse_json_output(body)
        errors = payload.get("errors") or []
        if errors:
            detail = "; ".join(str(item.get("message") or item) for item in errors)
            if is_rate_limit_error(detail):
                kind = "secondary" if is_secondary_rate_limit(detail) else "primary"
                self._stop(
                    "rate_limited",
                    f"GitHub {kind} rate limit stopped {operation}: {detail}",
                    connection=connection,
                    cursor=cursor,
                    retry_after=parse_retry_after(detail),
                )
            raise GhError(f"GitHub GraphQL {operation} failed: {detail}")

        data = payload.get("data") or {}
        rate_limit = data.get("rateLimit") or {}
        normalized_rate = {
            "cost": rate_limit.get("cost"),
            "remaining": rate_limit.get("remaining"),
            "used": rate_limit.get("used"),
            "reset_at": rate_limit.get("resetAt"),
        }
        if rate_limit:
            self.last_rate_limit = normalized_rate
            if rate_limit.get("cost") is not None:
                self.total_cost += int(rate_limit["cost"])
        else:
            normalized_rate["error"] = "GraphQL response omitted rateLimit telemetry"
        self.operations.append({"operation": operation, **normalized_rate})
        remaining = normalized_rate.get("remaining")
        if remaining is not None and int(remaining) < self.config.reserve:
            self._stop(
                "rate_limited",
                f"GraphQL query {operation} crossed reserve: {remaining} remaining, "
                f"reserve {self.config.reserve}",
                connection=connection,
                cursor=cursor,
            )
        if self.query_seconds > self.config.max_seconds:
            self._stop(
                "budget_exhausted",
                f"GraphQL query {operation} crossed execution-time ceiling "
                f"({self.query_seconds:.3f}s > {self.config.max_seconds:g}s)",
                connection=connection,
                cursor=cursor,
            )
        if self.deadline is not None and self.monotonic() > self.deadline:
            self._stop(
                "budget_exhausted",
                f"GraphQL query {operation} crossed the observer deadline",
                connection=connection,
                cursor=cursor,
            )
        return data

    def record_page(self, connection: str) -> None:
        self.page_counts[connection] = self.page_counts.get(connection, 0) + 1

    def telemetry(self) -> dict[str, Any]:
        last = self.last_rate_limit
        preflight = self.preflight
        telemetry_error = None
        if not last:
            telemetry_error = (
                "No GraphQL query completed; query cost is unavailable. "
                "Quota values come from the REST preflight."
            )
        return {
            "status": self.status,
            "reason": self.stop_reason,
            "retry_after_seconds": self.retry_after,
            "reserve": self.config.reserve,
            "query_cost_buffer": self.config.query_cost_buffer,
            "preflight": self.preflight,
            "graphql": {
                "cost": last.get("cost"),
                "remaining": last.get("remaining", preflight.get("remaining")),
                "used": last.get("used", preflight.get("used")),
                "reset_at": last.get("reset_at", preflight.get("reset_at")),
                "total_cost": self.total_cost,
                "requests": self.request_count,
                "query_seconds": self.query_seconds,
                "error": telemetry_error,
                "operations": self.operations,
            },
        }


def run_gh(arguments: list[str], timeout: float | None = None) -> str:
    if shutil.which("gh") is None:
        raise GhError("gh CLI is not installed or not on PATH")
    try:
        result = subprocess.run(
            ["gh", *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise GhTimeout(f"gh request timed out after {timeout:g}s") from error
    if result.returncode:
        detail = "\n".join(
            part for part in (result.stderr.strip(), result.stdout.strip()) if part
        ) or "unknown gh error"
        raise GhError(detail)
    return result.stdout


def parse_json_output(output: str) -> Any:
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise GhError(f"gh returned invalid JSON: {error}") from error


def parse_included_response(output: str) -> tuple[dict[str, str], str]:
    normalized = output.replace("\r\n", "\n")
    if not normalized.startswith("HTTP/"):
        return {}, output
    header_text, separator, body = normalized.partition("\n\n")
    if not separator:
        raise GhError("gh --include response omitted the HTTP body separator")
    headers: dict[str, str] = {}
    for line in header_text.splitlines()[1:]:
        name, colon, value = line.partition(":")
        if colon:
            headers[name.strip().casefold()] = value.strip()
    return headers, body


def resolve_target(target: str | None, repository: str | None) -> tuple[str, int]:
    if target:
        match = PR_URL_RE.match(target)
        if match:
            url_repository, number = match.groups()
            if repository and repository != url_repository:
                raise GhError("--repo does not match the pull request URL")
            return url_repository, int(number)
        if not target.isdigit() or int(target) < 1:
            raise GhError("PR must be a positive number or a github.com pull request URL")
        number = int(target)
    else:
        view = parse_json_output(run_gh(["pr", "view", "--json", "number,url"]))
        match = PR_URL_RE.match(view.get("url", ""))
        if not match:
            raise GhError("could not resolve the current branch pull request")
        url_repository, _ = match.groups()
        return repository or url_repository, int(view["number"])

    if repository is None:
        repository = run_gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]).strip()
    if not REPO_RE.match(repository):
        raise GhError("repository must use OWNER/REPO format")
    return repository, number


def parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise GhError("--after must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def epoch_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def at_or_after(value: str | None, minimum: datetime | None) -> bool:
    if minimum is None:
        return True
    parsed = parse_time(value)
    return parsed is not None and parsed >= minimum


def is_connector(author: str | None) -> bool:
    login = (author or "").casefold()
    return any(marker in login for marker in CONNECTOR_MARKERS)


def is_rate_limit_error(detail: str) -> bool:
    folded = detail.casefold()
    return any(marker in folded for marker in RATE_LIMIT_MARKERS)


def is_secondary_rate_limit(detail: str) -> bool:
    folded = detail.casefold()
    return any(marker in folded for marker in SECONDARY_RATE_LIMIT_MARKERS)


def parse_retry_after(detail: str) -> int | None:
    match = RETRY_AFTER_RE.search(detail)
    return int(match.group(1)) if match else None


def reaction_counts(
    reactions: list[dict[str, Any]] | None,
    minimum: datetime | None,
) -> dict[str, int]:
    counts = {"eyes": 0, "thumbs_up": 0}
    for reaction in reactions or []:
        if not is_connector((reaction.get("user") or {}).get("login")):
            continue
        if not at_or_after(reaction.get("createdAt"), minimum):
            continue
        content = str(reaction.get("content", "")).upper()
        if content == "EYES":
            counts["eyes"] += 1
        elif content == "THUMBS_UP":
            counts["thumbs_up"] += 1
    return counts


def merge_reaction_counts(*counts: dict[str, int]) -> dict[str, int]:
    return {
        key: sum(item.get(key, 0) for item in counts)
        for key in ("eyes", "thumbs_up")
    }


def body_reviews_head(
    item: dict[str, Any],
    head_oid: str | None,
    marker: re.Pattern[str],
) -> bool:
    if not head_oid:
        return False
    match = marker.search(str(item.get("body") or ""))
    return bool(match and head_oid.casefold().startswith(match.group(1).casefold()))


def response_reviews_head(item: dict[str, Any], head_oid: str | None) -> bool:
    if not head_oid:
        return False
    commit_oid = str((item.get("commit") or {}).get("oid") or "")
    if commit_oid:
        return commit_oid.casefold() == head_oid.casefold()
    return body_reviews_head(item, head_oid, REVIEWED_COMMIT_RE)


def request_reviews_head(item: dict[str, Any], head_oid: str | None) -> bool:
    return body_reviews_head(item, head_oid, REVIEW_HEAD_RE)


def clip(value: str | None, limit: int) -> str:
    text = value or ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def classify_review_state(
    *,
    unresolved_count: int,
    eyes: int,
    thumbs_up: int,
    clean_response: bool,
    connector_response: bool,
    pagination_incomplete: bool = False,
    forced_outcome: str | None = None,
) -> str:
    if forced_outcome:
        return forced_outcome
    if unresolved_count:
        return "review_feedback"
    if pagination_incomplete:
        return "pagination_incomplete"
    if thumbs_up or clean_response:
        return "passed"
    if connector_response:
        return "review_response"
    if eyes:
        return "in_progress"
    return "not_started_or_pending"


def collect_pages(
    session: GraphQLSession,
    connection: str,
    fetch_page: Callable[[str | None], dict[str, Any]],
    *,
    initial_cursor: str | None = None,
) -> tuple[list[dict[str, Any]], int | None]:
    nodes: list[dict[str, Any]] = []
    cursor = initial_cursor
    requested_cursors: set[str | None] = set()
    total_count: int | None = None

    while True:
        page_number = session.page_counts.get(connection, 0)
        if page_number >= session.config.max_pages:
            session._stop(
                "budget_exhausted",
                f"page ceiling ({session.config.max_pages}) reached for {connection}",
                connection=connection,
                cursor=cursor,
            )
        if cursor in requested_cursors:
            session._stop(
                "pagination_incomplete",
                f"cursor made no progress for {connection}: {cursor!r} was already requested",
                connection=connection,
                cursor=cursor,
            )
        requested_cursors.add(cursor)
        page = fetch_page(cursor)
        session.record_page(connection)
        nodes.extend(page.get("nodes") or [])
        if page.get("totalCount") is not None:
            total_count = int(page["totalCount"])
        page_info = page.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            return nodes, total_count
        next_cursor = page_info.get("endCursor")
        if not next_cursor or next_cursor == cursor or next_cursor in requested_cursors:
            session._stop(
                "pagination_incomplete",
                f"cursor made no progress for {connection}: next cursor {next_cursor!r}",
                connection=connection,
                cursor=next_cursor,
            )
        cursor = str(next_cursor)


RATE_LIMIT_FRAGMENT = "rateLimit { cost remaining used resetAt }"

BASE_QUERY = rf"""
query Base($owner:String!, $name:String!, $number:Int!) {{
  repository(owner:$owner, name:$name) {{
    pullRequest(number:$number) {{
      id number url state isDraft headRefOid mergeStateStatus updatedAt
      commits(last:1) {{
        nodes {{
          commit {{
            oid
            statusCheckRollup {{ state }}
          }}
        }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

COMMENTS_QUERY = rf"""
query Comments($owner:String!, $name:String!, $number:Int!, $pageSize:Int!, $cursor:String) {{
  repository(owner:$owner, name:$name) {{
    pullRequest(number:$number) {{
      comments(first:$pageSize, after:$cursor) {{
        totalCount
        pageInfo {{ hasNextPage endCursor }}
        nodes {{ id databaseId url body createdAt author {{ login }} }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

REVIEWS_QUERY = rf"""
query Reviews($owner:String!, $name:String!, $number:Int!, $pageSize:Int!, $cursor:String) {{
  repository(owner:$owner, name:$name) {{
    pullRequest(number:$number) {{
      reviews(first:$pageSize, after:$cursor) {{
        totalCount
        pageInfo {{ hasNextPage endCursor }}
        nodes {{
          databaseId url body state submittedAt author {{ login }} commit {{ oid }}
        }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

THREADS_QUERY = rf"""
query Threads($owner:String!, $name:String!, $number:Int!, $pageSize:Int!, $cursor:String) {{
  repository(owner:$owner, name:$name) {{
    pullRequest(number:$number) {{
      reviewThreads(first:$pageSize, after:$cursor) {{
        totalCount
        pageInfo {{ hasNextPage endCursor }}
        nodes {{
          id isResolved
          comments(first:$pageSize) {{
            totalCount
            pageInfo {{ hasNextPage endCursor }}
            nodes {{
              databaseId url body path line originalLine createdAt author {{ login }}
            }}
          }}
        }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

THREAD_COMMENTS_QUERY = rf"""
query ThreadComments($threadId:ID!, $pageSize:Int!, $cursor:String) {{
  node(id:$threadId) {{
    ... on PullRequestReviewThread {{
      comments(first:$pageSize, after:$cursor) {{
        totalCount
        pageInfo {{ hasNextPage endCursor }}
        nodes {{
          databaseId url body path line originalLine createdAt author {{ login }}
        }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

PR_REACTIONS_QUERY = rf"""
query PullRequestReactions($owner:String!, $name:String!, $number:Int!, $pageSize:Int!, $cursor:String) {{
  repository(owner:$owner, name:$name) {{
    pullRequest(number:$number) {{
      reactions(first:$pageSize, after:$cursor) {{
        totalCount
        pageInfo {{ hasNextPage endCursor }}
        nodes {{ content createdAt user {{ login }} }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

REQUEST_REACTIONS_QUERY = rf"""
query RequestReactions($requestId:ID!, $pageSize:Int!, $cursor:String) {{
  node(id:$requestId) {{
    ... on IssueComment {{
      reactions(first:$pageSize, after:$cursor) {{
        totalCount
        pageInfo {{ hasNextPage endCursor }}
        nodes {{ content createdAt user {{ login }} }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

CHECKS_QUERY = rf"""
query Checks($owner:String!, $name:String!, $number:Int!, $pageSize:Int!, $cursor:String) {{
  repository(owner:$owner, name:$name) {{
    pullRequest(number:$number) {{
      headRefOid
      commits(last:1) {{
        nodes {{
          commit {{
            oid
            statusCheckRollup {{
              state
              contexts(first:$pageSize, after:$cursor) {{
                totalCount
                pageInfo {{ hasNextPage endCursor }}
                nodes {{
                  __typename
                  ... on CheckRun {{ name status conclusion detailsUrl }}
                  ... on StatusContext {{ context state targetUrl }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""

TRANSITION_QUERY = rf"""
query Transition($owner:String!, $name:String!, $number:Int!, $requestId:ID!, $hasRequest:Boolean!) {{
  repository(owner:$owner, name:$name) {{
    pullRequest(number:$number) {{
      headRefOid updatedAt
      comments(last:1) {{ totalCount nodes {{ id createdAt }} }}
      reviews(last:1) {{ totalCount nodes {{ databaseId submittedAt }} }}
      reviewThreads(last:20) {{
        totalCount
        nodes {{ id isResolved comments(last:1) {{ totalCount }} }}
      }}
      reactions(last:20) {{ totalCount nodes {{ content createdAt user {{ login }} }} }}
      commits(last:1) {{
        nodes {{
          commit {{
            statusCheckRollup {{
              state
              contexts(last:20) {{
                totalCount
                nodes {{
                  __typename
                  ... on CheckRun {{ name status conclusion detailsUrl }}
                  ... on StatusContext {{ context state targetUrl }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
  }}
  request: node(id:$requestId) @include(if:$hasRequest) {{
    ... on IssueComment {{
      reactions(last:20) {{ totalCount nodes {{ content createdAt user {{ login }} }} }}
    }}
  }}
  {RATE_LIMIT_FRAGMENT}
}}
"""


def pr_connection(data: dict[str, Any], name: str) -> dict[str, Any]:
    pr = (((data.get("repository") or {}).get("pullRequest")) or {})
    return pr.get(name) or {}


def base_variables(repository: str, number: int) -> dict[str, Any]:
    owner, name = repository.split("/", 1)
    return {"owner": owner, "name": name, "number": number}


def page_variables(
    repository: str,
    number: int,
    page_size: int,
    cursor: str | None,
) -> dict[str, Any]:
    return {**base_variables(repository, number), "pageSize": page_size, "cursor": cursor}


def collect_check_snapshot(
    session: GraphQLSession,
    repository: str,
    number: int,
    expected_head_oid: str | None,
    connection: str,
) -> tuple[list[dict[str, Any]], int | None, str | None, str | None]:
    metadata: dict[str, str | None] = {"head_oid": None, "rollup_state": None}

    def fetch_page(cursor: str | None) -> dict[str, Any]:
        check_data = session.graphql(
            "Checks",
            CHECKS_QUERY,
            page_variables(repository, number, session.config.page_size, cursor),
            connection=connection,
            cursor=cursor,
        )
        check_pr = ((check_data.get("repository") or {}).get("pullRequest") or {})
        if check_pr.get("headRefOid") != expected_head_oid:
            session._stop(
                "pagination_incomplete",
                "pull request head changed while check contexts were being collected",
                connection=connection,
                cursor=cursor,
            )
        commits = (check_pr.get("commits") or {}).get("nodes") or [{}]
        commit = commits[-1].get("commit") or {}
        rollup = commit.get("statusCheckRollup") or {}
        metadata["head_oid"] = commit.get("oid")
        metadata["rollup_state"] = rollup.get("state")
        return rollup.get("contexts") or {}

    contexts, total = collect_pages(session, connection, fetch_page)
    return contexts, total, metadata["head_oid"], metadata["rollup_state"]


def latest_marker(items: list[dict[str, Any]], *fields: str) -> dict[str, Any] | None:
    if not items:
        return None
    latest = items[-1]
    return {field: latest.get(field) for field in fields}


def recent_thread_markers(threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": thread.get("id"),
            "isResolved": thread.get("isResolved"),
            "comments": {
                "totalCount": (thread.get("comments") or {}).get("totalCount")
            },
        }
        for thread in threads[-20:]
    ]


def fingerprint_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def incomplete_result(
    repository: str,
    number: int,
    session: GraphQLSession,
    stop: InspectionStop,
) -> dict[str, Any]:
    return {
        "repository": repository,
        "inspection": {
            "outcome": stop.outcome,
            "complete": False,
            "reason": stop.reason,
        },
        "pr": {
            "number": number,
            "url": f"https://github.com/{repository}/pull/{number}",
            "state": None,
            "is_draft": None,
            "head_oid": None,
            "merge_state": None,
            "updated_at": None,
        },
        "trigger": {
            "surface": None,
            "request_comment": None,
            "after": None,
            "reactions": {"eyes": 0, "thumbs_up": 0},
            "observed_reactions": {"eyes": 0, "thumbs_up": 0},
            "reaction_head_anchored": False,
            "ignored_thumbs_up": 0,
        },
        "review": {
            "outcome": stop.outcome,
            "clean_response": False,
            "stale_clean_response": False,
            "connector_response": False,
            "unresolved_count": None,
            "unresolved_threads": [],
            "connector_issue_comments": [],
            "connector_reviews": [],
        },
        "checks": {"head_oid": None, "rollup_state": None, "contexts": []},
        "rate_limit": session.telemetry(),
        "pagination": {
            "complete": False,
            "pages": session.page_counts,
            "unfinished": [{
                "connection": stop.connection or "inspection",
                "cursor": stop.cursor,
                "reason": stop.reason,
            }],
        },
        "pagination_incomplete": True,
    }


def inspect(
    repository: str,
    number: int,
    after: datetime | None,
    body_limit: int,
    *,
    config: InspectionConfig | None = None,
    runner: Callable[[list[str], float | None], str] = run_gh,
    session: GraphQLSession | None = None,
) -> dict[str, Any]:
    session = session or GraphQLSession(config or InspectionConfig(), runner)
    variables = base_variables(repository, number)
    try:
        data = session.graphql("Base", BASE_QUERY, variables, connection="base")
    except InspectionStop as stop:
        return incomplete_result(repository, number, session, stop)

    pr = (((data.get("repository") or {}).get("pullRequest")) or None)
    if pr is None:
        raise GhError(f"pull request {repository}#{number} was not found or is not accessible")

    incomplete: InspectionStop | None = None
    comments: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    threads: list[dict[str, Any]] = []
    pr_reactions: list[dict[str, Any]] = []
    request_reactions: list[dict[str, Any]] = []
    contexts: list[dict[str, Any]] = []
    totals: dict[str, int | None] = {}
    base_commit = (((pr.get("commits") or {}).get("nodes") or [{}])[-1].get("commit") or {})
    checks_head_oid = base_commit.get("oid")
    checks_rollup_state = (base_commit.get("statusCheckRollup") or {}).get("state")

    try:
        comments, totals["comments"] = collect_pages(
            session,
            "comments",
            lambda cursor: pr_connection(
                session.graphql(
                    "Comments",
                    COMMENTS_QUERY,
                    page_variables(repository, number, session.config.page_size, cursor),
                    connection="comments",
                    cursor=cursor,
                ),
                "comments",
            ),
        )
        reviews, totals["reviews"] = collect_pages(
            session,
            "reviews",
            lambda cursor: pr_connection(
                session.graphql(
                    "Reviews",
                    REVIEWS_QUERY,
                    page_variables(repository, number, session.config.page_size, cursor),
                    connection="reviews",
                    cursor=cursor,
                ),
                "reviews",
            ),
        )
        threads, totals["review_threads"] = collect_pages(
            session,
            "review_threads",
            lambda cursor: pr_connection(
                session.graphql(
                    "Threads",
                    THREADS_QUERY,
                    page_variables(repository, number, session.config.page_size, cursor),
                    connection="review_threads",
                    cursor=cursor,
                ),
                "reviewThreads",
            ),
        )
        pr_reactions, totals["pull_request_reactions"] = collect_pages(
            session,
            "pull_request_reactions",
            lambda cursor: pr_connection(
                session.graphql(
                    "PullRequestReactions",
                    PR_REACTIONS_QUERY,
                    page_variables(repository, number, session.config.page_size, cursor),
                    connection="pull_request_reactions",
                    cursor=cursor,
                ),
                "reactions",
            ),
        )

        eligible_requests = [
            comment for comment in comments
            if str(comment.get("body") or "").lstrip().startswith("@codex review")
            and at_or_after(comment.get("createdAt"), after)
        ]
        active_request = max(
            eligible_requests,
            key=lambda item: item.get("createdAt") or "",
            default=None,
        )
        if active_request:
            request_reactions, totals["request_reactions"] = collect_pages(
                session,
                "request_reactions",
                lambda cursor: (
                    session.graphql(
                        "RequestReactions",
                        REQUEST_REACTIONS_QUERY,
                        {
                            "requestId": active_request["id"],
                            "pageSize": session.config.page_size,
                            "cursor": cursor,
                        },
                        connection="request_reactions",
                        cursor=cursor,
                    ).get("node") or {}
                ).get("reactions") or {},
            )
        else:
            totals["request_reactions"] = 0
            session.page_counts["request_reactions"] = 0

        (
            contexts,
            totals["check_contexts"],
            checks_head_oid,
            checks_rollup_state,
        ) = collect_check_snapshot(
            session,
            repository,
            number,
            pr.get("headRefOid"),
            "check_contexts",
        )

        for thread in threads:
            initial = thread.get("comments") or {}
            thread["_all_comments"] = list(initial.get("nodes") or [])
            page_info = initial.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                continue
            connection = f"review_thread_comments:{thread.get('id')}"
            cursor = page_info.get("endCursor")
            if not cursor:
                session._stop(
                    "pagination_incomplete",
                    f"nested review-thread comments omitted an end cursor for {thread.get('id')}",
                    connection=connection,
                )
            more_comments, _ = collect_pages(
                session,
                connection,
                lambda nested_cursor, thread_id=thread["id"]: (
                    session.graphql(
                        "ThreadComments",
                        THREAD_COMMENTS_QUERY,
                        {
                            "threadId": thread_id,
                            "pageSize": session.config.page_size,
                            "cursor": nested_cursor,
                        },
                        connection=connection,
                        cursor=nested_cursor,
                    ).get("node") or {}
                ).get("comments") or {},
                initial_cursor=str(cursor),
            )
            thread["_all_comments"].extend(more_comments)

        (
            verified_contexts,
            verified_total,
            verified_head_oid,
            verified_rollup_state,
        ) = collect_check_snapshot(
            session,
            repository,
            number,
            pr.get("headRefOid"),
            "check_contexts_verify",
        )
        if (
            verified_contexts != contexts
            or verified_total != totals.get("check_contexts")
            or verified_head_oid != checks_head_oid
            or verified_rollup_state != checks_rollup_state
        ):
            session._stop(
                "pagination_incomplete",
                "check contexts changed during the paginated snapshot; rerun after they stabilize",
                connection="check_contexts_verify",
            )

        expected_fingerprint = fingerprint_json({
            "head_oid": pr.get("headRefOid"),
            "updated_at": pr.get("updatedAt"),
            "comments": totals.get("comments"),
            "reviews": totals.get("reviews"),
            "review_threads": totals.get("review_threads"),
            "pull_request_reactions": totals.get("pull_request_reactions"),
            "request_reactions": totals.get("request_reactions"),
            "check_contexts": totals.get("check_contexts"),
            "rollup_state": checks_rollup_state,
            "latest_comment": latest_marker(comments, "id", "createdAt"),
            "latest_review": latest_marker(reviews, "databaseId", "submittedAt"),
            "recent_review_threads": recent_thread_markers(threads),
            "recent_pull_request_reactions": pr_reactions[-20:],
            "recent_request_reactions": request_reactions[-20:],
            "recent_check_contexts": contexts[-20:],
        })
        final_fingerprint = transition_probe(
            repository,
            number,
            active_request.get("id") if active_request else None,
            pr["id"],
            session,
        )
        if final_fingerprint != expected_fingerprint:
            session._stop(
                "pagination_incomplete",
                "pull request state changed during the paginated snapshot; rerun after it stabilizes",
                connection="snapshot_consistency",
            )
    except InspectionStop as stop:
        incomplete = stop

    eligible_requests = [
        comment for comment in comments
        if str(comment.get("body") or "").lstrip().startswith("@codex review")
        and at_or_after(comment.get("createdAt"), after)
    ]
    active_request = max(
        eligible_requests,
        key=lambda item: item.get("createdAt") or "",
        default=None,
    )
    trigger_time = parse_time(active_request.get("createdAt")) if active_request else after
    current_head_oid = pr.get("headRefOid")
    reaction_head_anchored = bool(
        active_request and request_reviews_head(active_request, current_head_oid)
    )
    observed_reactions = merge_reaction_counts(
        reaction_counts(pr_reactions, trigger_time),
        reaction_counts(request_reactions, trigger_time),
    )
    trigger_reactions = dict(observed_reactions)
    ignored_thumbs_up = 0
    if not reaction_head_anchored:
        ignored_thumbs_up = trigger_reactions["thumbs_up"]
        trigger_reactions["thumbs_up"] = 0

    connector_issue_comments = [
        item for item in comments
        if is_connector((item.get("author") or {}).get("login"))
        and at_or_after(item.get("createdAt"), trigger_time)
    ]
    connector_reviews = [
        item for item in reviews
        if is_connector((item.get("author") or {}).get("login"))
        and at_or_after(item.get("submittedAt"), trigger_time)
    ]

    unresolved_threads = []
    connector_thread_response = False
    for thread in threads:
        thread_comments = thread.get("_all_comments")
        if thread_comments is None:
            thread_comments = (thread.get("comments") or {}).get("nodes") or []
        connector_thread_response = connector_thread_response or any(
            is_connector((item.get("author") or {}).get("login"))
            and at_or_after(item.get("createdAt"), trigger_time)
            for item in thread_comments
        )
        if thread.get("isResolved"):
            continue
        unresolved_threads.append({
            "id": thread.get("id"),
            "comments": [
                {
                    "database_id": item.get("databaseId"),
                    "author": (item.get("author") or {}).get("login"),
                    "created_at": item.get("createdAt"),
                    "path": item.get("path"),
                    "line": item.get("line"),
                    "original_line": item.get("originalLine"),
                    "url": item.get("url"),
                    "body": clip(item.get("body"), body_limit),
                }
                for item in thread_comments
            ],
        })

    connector_responses = [*connector_issue_comments, *connector_reviews]
    clean_response_candidates = [
        item for item in connector_responses
        if any(
            marker in str(item.get("body") or "").casefold()
            for marker in CLEAN_RESPONSE_MARKERS
        )
    ]
    clean_response = any(
        response_reviews_head(item, current_head_oid)
        for item in clean_response_candidates
    )
    stale_clean_response = any(
        not response_reviews_head(item, current_head_oid)
        for item in clean_response_candidates
    )
    connector_response = bool(
        connector_issue_comments or connector_reviews or connector_thread_response
    )

    pagination_complete = incomplete is None
    forced_outcome = (
        incomplete.outcome
        if incomplete and incomplete.outcome in {"rate_limited", "budget_exhausted"}
        else None
    )
    outcome = classify_review_state(
        unresolved_count=len(unresolved_threads),
        eyes=trigger_reactions["eyes"],
        thumbs_up=trigger_reactions["thumbs_up"],
        clean_response=clean_response,
        connector_response=connector_response,
        pagination_incomplete=not pagination_complete,
        forced_outcome=forced_outcome,
    )
    unfinished = []
    if incomplete:
        unfinished.append({
            "connection": incomplete.connection or "inspection",
            "cursor": incomplete.cursor,
            "reason": incomplete.reason,
        })

    return {
        "repository": repository,
        "inspection": {
            "outcome": "complete" if pagination_complete else incomplete.outcome,
            "complete": pagination_complete,
            "reason": None if pagination_complete else incomplete.reason,
        },
        "pr": {
            "number": pr.get("number"),
            "url": pr.get("url"),
            "state": pr.get("state"),
            "is_draft": pr.get("isDraft"),
            "head_oid": pr.get("headRefOid"),
            "merge_state": pr.get("mergeStateStatus"),
            "updated_at": pr.get("updatedAt"),
            "node_id": pr.get("id"),
        },
        "trigger": {
            "surface": "comment" if active_request else "pull_request",
            "request_comment": None if active_request is None else {
                "node_id": active_request.get("id"),
                "database_id": active_request.get("databaseId"),
                "url": active_request.get("url"),
                "body": clip(active_request.get("body"), body_limit),
                "created_at": active_request.get("createdAt"),
            },
            "after": after.isoformat().replace("+00:00", "Z") if after else None,
            "reactions": trigger_reactions,
            "observed_reactions": observed_reactions,
            "reaction_head_anchored": reaction_head_anchored,
            "ignored_thumbs_up": ignored_thumbs_up,
        },
        "review": {
            "outcome": outcome,
            "clean_response": clean_response,
            "stale_clean_response": stale_clean_response,
            "connector_response": connector_response,
            "unresolved_count": len(unresolved_threads) if pagination_complete else None,
            "unresolved_threads": unresolved_threads,
            "connector_issue_comments": [
                {
                    "database_id": item.get("databaseId"),
                    "created_at": item.get("createdAt"),
                    "url": item.get("url"),
                    "body": clip(item.get("body"), body_limit),
                }
                for item in connector_issue_comments
            ],
            "connector_reviews": [
                {
                    "database_id": item.get("databaseId"),
                    "submitted_at": item.get("submittedAt"),
                    "state": item.get("state"),
                    "commit_oid": (item.get("commit") or {}).get("oid"),
                    "url": item.get("url"),
                    "body": clip(item.get("body"), body_limit),
                }
                for item in connector_reviews
            ],
        },
        "checks": {
            "head_oid": checks_head_oid,
            "rollup_state": checks_rollup_state,
            "contexts": contexts,
        },
        "activity": {
            "comments": totals.get("comments"),
            "reviews": totals.get("reviews"),
            "review_threads": totals.get("review_threads"),
            "pull_request_reactions": totals.get("pull_request_reactions"),
            "request_reactions": totals.get("request_reactions"),
            "check_contexts": totals.get("check_contexts"),
            "latest_comment": latest_marker(comments, "id", "createdAt"),
            "latest_review": latest_marker(reviews, "databaseId", "submittedAt"),
            "recent_review_threads": recent_thread_markers(threads),
            "recent_pull_request_reactions": pr_reactions[-20:],
            "recent_request_reactions": request_reactions[-20:],
            "recent_check_contexts": contexts[-20:],
        },
        "rate_limit": session.telemetry(),
        "pagination": {
            "complete": pagination_complete,
            "pages": session.page_counts,
            "unfinished": unfinished,
        },
        "pagination_incomplete": not pagination_complete,
    }


def transition_fingerprint_from_result(result: dict[str, Any]) -> str:
    pr = result.get("pr") or {}
    activity = result.get("activity") or {}
    checks = result.get("checks") or {}
    payload = {
        "head_oid": pr.get("head_oid"),
        "updated_at": pr.get("updated_at"),
        "comments": activity.get("comments"),
        "reviews": activity.get("reviews"),
        "review_threads": activity.get("review_threads"),
        "pull_request_reactions": activity.get("pull_request_reactions"),
        "request_reactions": activity.get("request_reactions"),
        "check_contexts": activity.get("check_contexts"),
        "rollup_state": checks.get("rollup_state"),
        "latest_comment": activity.get("latest_comment"),
        "latest_review": activity.get("latest_review"),
        "recent_review_threads": activity.get("recent_review_threads") or [],
        "recent_pull_request_reactions": activity.get("recent_pull_request_reactions") or [],
        "recent_request_reactions": activity.get("recent_request_reactions") or [],
        "recent_check_contexts": activity.get("recent_check_contexts") or [],
    }
    return fingerprint_json(payload)


def transition_probe(
    repository: str,
    number: int,
    request_id: str | None,
    pr_id: str,
    session: GraphQLSession,
) -> str:
    data = session.graphql(
        "Transition",
        TRANSITION_QUERY,
        {
            **base_variables(repository, number),
            "requestId": request_id or pr_id,
            "hasRequest": bool(request_id),
        },
        connection="transition_probe",
    )
    pr = (((data.get("repository") or {}).get("pullRequest")) or {})
    request = data.get("request") or {}
    commit = (((pr.get("commits") or {}).get("nodes") or [{}])[-1].get("commit") or {})
    rollup = commit.get("statusCheckRollup") or {}
    pr_reactions = pr.get("reactions") or {}
    request_reactions = request.get("reactions") or {}
    comments = pr.get("comments") or {}
    reviews = pr.get("reviews") or {}
    review_threads = pr.get("reviewThreads") or {}
    contexts = rollup.get("contexts") or {}
    payload = {
        "head_oid": pr.get("headRefOid"),
        "updated_at": pr.get("updatedAt"),
        "comments": comments.get("totalCount"),
        "reviews": reviews.get("totalCount"),
        "review_threads": review_threads.get("totalCount"),
        "pull_request_reactions": pr_reactions.get("totalCount"),
        "request_reactions": request_reactions.get("totalCount") if request_id else 0,
        "check_contexts": contexts.get("totalCount"),
        "rollup_state": rollup.get("state"),
        "latest_comment": latest_marker(comments.get("nodes") or [], "id", "createdAt"),
        "latest_review": latest_marker(reviews.get("nodes") or [], "databaseId", "submittedAt"),
        "recent_review_threads": recent_thread_markers(review_threads.get("nodes") or []),
        "recent_pull_request_reactions": pr_reactions.get("nodes") or [],
        "recent_request_reactions": request_reactions.get("nodes") or [],
        "recent_check_contexts": contexts.get("nodes") or [],
    }
    return fingerprint_json(payload)


def backoff_seconds(
    unchanged_polls: int,
    initial: float,
    maximum: float,
    jitter_ratio: float,
    random_value: float,
) -> float:
    base = min(maximum, initial * (2 ** max(0, unchanged_polls)))
    factor = 1 + ((random_value * 2) - 1) * jitter_ratio
    return max(1.0, min(maximum, base * factor))


def secure_observer_lock_directory(directory: Path | None = None) -> Path:
    if directory is None:
        runtime_directory = os.environ.get("XDG_RUNTIME_DIR")
        root = (
            Path(runtime_directory) / "develoop-observer-locks"
            if runtime_directory
            else Path.home() / ".develoop-observer-locks"
        )
    else:
        root = directory
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata = root.lstat()
    except OSError as error:
        raise GhError(f"could not prepare observer lock directory {root}: {error}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise GhError(f"observer lock directory must be a real directory: {root}")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise GhError(f"observer lock directory is not owned by the current user: {root}")
    try:
        root.chmod(0o700)
    except OSError as error:
        raise GhError(f"could not secure observer lock directory {root}: {error}") from error
    return root


class ObserverLock:
    def __init__(self, repository: str, number: int, directory: Path | None = None) -> None:
        safe_repo = re.sub(r"[^A-Za-z0-9_.-]", "_", repository)
        self.path = secure_observer_lock_directory(directory) / f"develoop-{safe_repo}-{number}.lock"
        self.owned = False
        self.descriptor: int | None = None

    def acquire(self) -> None:
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags, 0o600)
        except OSError as error:
            raise InspectionStop(
                "observer_unavailable",
                f"observer lock path is unsafe or unavailable: {self.path}: {error}",
            ) from error
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or (hasattr(os, "getuid") and metadata.st_uid != os.getuid())
        ):
            os.close(descriptor)
            raise InspectionStop(
                "observer_unavailable",
                f"observer lock must be a single-link regular file owned by the current user: {self.path}",
            )
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        try:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif msvcrt is not None:  # pragma: no cover - Windows-only path
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"\0")
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:  # pragma: no cover - Python always exposes one on supported hosts
                os.close(descriptor)
                raise InspectionStop(
                    "observer_unavailable",
                    "this host does not provide an advisory file-lock implementation",
                )
        except (BlockingIOError, OSError):
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                owner = os.read(descriptor, 4_096).decode("utf-8", errors="replace").strip("\0\n ")
            finally:
                os.close(descriptor)
            raise InspectionStop(
                "observer_active",
                f"another observer owns {self.path}: {owner or 'owner unknown'}",
            )

        payload = json.dumps({"pid": os.getpid(), "started_at": utc_now()}).encode("utf-8")
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, payload)
        os.fsync(descriptor)
        self.descriptor = descriptor
        self.owned = True

    def release(self) -> None:
        if not self.owned or self.descriptor is None:
            return
        if fcntl is not None:
            fcntl.flock(self.descriptor, fcntl.LOCK_UN)
        elif msvcrt is not None:  # pragma: no cover - Windows-only path
            os.lseek(self.descriptor, 0, os.SEEK_SET)
            msvcrt.locking(self.descriptor, msvcrt.LK_UNLCK, 1)
        os.close(self.descriptor)
        self.descriptor = None
        self.owned = False

    def __enter__(self) -> ObserverLock:
        self.acquire()
        return self

    def __exit__(self, *_: Any) -> None:
        self.release()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def watch(
    repository: str,
    number: int,
    after: datetime | None,
    body_limit: int,
    *,
    config: InspectionConfig,
    poll_initial: float,
    poll_max: float,
    max_wait: float,
    full_refresh_interval: float,
    jitter: float,
    runner: Callable[[list[str], float | None], str] = run_gh,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    lock = ObserverLock(repository, number)
    try:
        lock.acquire()
    except InspectionStop as stop:
        session = GraphQLSession(config, runner, monotonic=monotonic)
        result = incomplete_result(repository, number, session, stop)
        result["review"]["outcome"] = stop.outcome
        result["observer"] = {"outcome": stop.outcome, "reason": stop.reason}
        return result

    started = monotonic()
    deadline = started + max_wait
    probes = 0
    unchanged_polls = 0
    last_full_snapshot = started
    session = GraphQLSession(
        config,
        runner,
        monotonic=monotonic,
        deadline=deadline,
    )
    try:
        result = inspect(
            repository,
            number,
            after,
            body_limit,
            session=session,
        )
        while result["review"]["outcome"] not in TERMINAL_OUTCOMES:
            elapsed = monotonic() - started
            if elapsed >= max_wait:
                result["observer"] = {
                    "outcome": "watch_timeout",
                    "elapsed_seconds": elapsed,
                    "probes": probes,
                    "unchanged_polls": unchanged_polls,
                }
                result["rate_limit"] = session.telemetry()
                return result
            delay = backoff_seconds(
                unchanged_polls,
                poll_initial,
                poll_max,
                jitter,
                random.random(),
            )
            sleep(min(delay, max_wait - elapsed))
            if monotonic() - started >= max_wait:
                result["observer"] = {
                    "outcome": "watch_timeout",
                    "elapsed_seconds": monotonic() - started,
                    "probes": probes,
                    "unchanged_polls": unchanged_polls,
                }
                result["rate_limit"] = session.telemetry()
                return result
            baseline = transition_fingerprint_from_result(result)
            request_comment = (result.get("trigger") or {}).get("request_comment") or {}
            try:
                fingerprint = transition_probe(
                    repository,
                    number,
                    request_comment.get("node_id"),
                    result["pr"]["node_id"],
                    session,
                )
            except InspectionStop as stop:
                result["review"]["outcome"] = stop.outcome
                result["inspection"] = {
                    "outcome": stop.outcome,
                    "complete": False,
                    "reason": stop.reason,
                }
                result["pagination_incomplete"] = True
                result["pagination"]["complete"] = False
                result["pagination"]["unfinished"].append({
                    "connection": stop.connection or "transition_probe",
                    "cursor": stop.cursor,
                    "reason": stop.reason,
                })
                result["rate_limit"] = session.telemetry()
                result["observer"] = {
                    "outcome": stop.outcome,
                    "elapsed_seconds": monotonic() - started,
                    "probes": probes,
                    "unchanged_polls": unchanged_polls,
                }
                return result
            probes += 1
            if fingerprint == baseline:
                unchanged_polls += 1
                if monotonic() - last_full_snapshot >= full_refresh_interval:
                    result = inspect(
                        repository,
                        number,
                        after,
                        body_limit,
                        session=session,
                    )
                    last_full_snapshot = monotonic()
                continue
            unchanged_polls = 0
            result = inspect(
                repository,
                number,
                after,
                body_limit,
                session=session,
            )
            last_full_snapshot = monotonic()
        result["observer"] = {
            "outcome": result["review"]["outcome"],
            "elapsed_seconds": monotonic() - started,
            "probes": probes,
            "unchanged_polls": unchanged_polls,
        }
        result["rate_limit"] = session.telemetry()
        return result
    finally:
        lock.release()


def self_test() -> None:
    cases = [
        ({"unresolved_count": 0, "eyes": 1, "thumbs_up": 0, "clean_response": False, "connector_response": False}, "in_progress"),
        ({"unresolved_count": 0, "eyes": 0, "thumbs_up": 1, "clean_response": False, "connector_response": False}, "passed"),
        ({"unresolved_count": 0, "eyes": 0, "thumbs_up": 0, "clean_response": True, "connector_response": True}, "passed"),
        ({"unresolved_count": 1, "eyes": 0, "thumbs_up": 1, "clean_response": True, "connector_response": True}, "review_feedback"),
        ({"unresolved_count": 0, "eyes": 0, "thumbs_up": 0, "clean_response": False, "connector_response": True}, "review_response"),
        ({"unresolved_count": 0, "eyes": 0, "thumbs_up": 0, "clean_response": False, "connector_response": False}, "not_started_or_pending"),
        ({"unresolved_count": 0, "eyes": 0, "thumbs_up": 1, "clean_response": True, "connector_response": True, "pagination_incomplete": True}, "pagination_incomplete"),
        ({"unresolved_count": 1, "eyes": 0, "thumbs_up": 0, "clean_response": False, "connector_response": False, "pagination_incomplete": True}, "review_feedback"),
        ({"unresolved_count": 0, "eyes": 0, "thumbs_up": 1, "clean_response": True, "connector_response": True, "forced_outcome": "budget_exhausted"}, "budget_exhausted"),
    ]
    for inputs, expected in cases:
        actual = classify_review_state(**inputs)
        if actual != expected:
            raise AssertionError(f"expected {expected}, got {actual} for {inputs}")
    minimum = parse_time("2026-07-24T00:00:00Z")
    combined = merge_reaction_counts(
        reaction_counts([
            {
                "content": "EYES",
                "createdAt": "2026-07-24T00:00:01Z",
                "user": {"login": "chatgpt-codex-connector"},
            },
            {
                "content": "THUMBS_UP",
                "createdAt": "2026-07-23T23:59:59Z",
                "user": {"login": "chatgpt-codex-connector"},
            },
        ], minimum),
        reaction_counts([
            {
                "content": "THUMBS_UP",
                "createdAt": "2026-07-24T00:00:02Z",
                "user": {"login": "chatgpt-codex-connector"},
            },
        ], minimum),
    )
    if combined != {"eyes": 1, "thumbs_up": 1}:
        raise AssertionError(f"expected combined reactions, got {combined}")
    head_oid = "abcdef0123456789abcdef0123456789abcdef01"
    if not request_reviews_head(
        {"body": "@codex review\n\nReview head: `abcdef0`"},
        head_oid,
    ):
        raise AssertionError("expected a matching review request marker to anchor reactions")
    if request_reviews_head(
        {"body": "@codex review\n\nReview head: `1234567`"},
        head_oid,
    ):
        raise AssertionError("expected a stale review request marker to fail closed")
    if request_reviews_head({"body": "@codex review"}, head_oid):
        raise AssertionError("expected an unanchored review request to fail closed")
    if not response_reviews_head({"commit": {"oid": head_oid}}, head_oid):
        raise AssertionError("expected matching review commit to apply to the current head")
    if not response_reviews_head({"body": "Reviewed commit: `abcdef0`"}, head_oid):
        raise AssertionError("expected reviewed commit marker to apply to the current head")
    if response_reviews_head({"body": "Didn't find any major issues."}, head_oid):
        raise AssertionError("expected an unanchored response to fail closed")
    if response_reviews_head({"commit": {"oid": "1234567"}}, head_oid):
        raise AssertionError("expected a stale review commit to fail closed")
    print("inspect_review_state self-test passed")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be finite and greater than 0")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", nargs="?", help="PR number or github.com pull request URL")
    parser.add_argument("--repo", help="Repository in OWNER/REPO format")
    parser.add_argument("--after", help="Ignore older review requests and connector events")
    parser.add_argument("--body-limit", type=positive_int, default=4_000, help="Maximum body characters per item")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    parser.add_argument("--self-test", action="store_true", help="Run state-classifier tests without GitHub")
    parser.add_argument("--watch", action="store_true", help="Own the bounded adaptive polling loop")
    parser.add_argument("--reserve", type=non_negative_int, default=200, help="GraphQL points to keep in reserve")
    parser.add_argument("--query-cost-buffer", type=positive_int, default=5, help="Points budgeted before each GraphQL query")
    parser.add_argument("--max-requests", type=positive_int, default=40, help="Maximum GraphQL requests per invocation")
    parser.add_argument("--max-pages", type=positive_int, default=20, help="Maximum pages per connection")
    parser.add_argument("--max-seconds", type=positive_float, default=90.0, help="Maximum GraphQL inspection time")
    parser.add_argument("--page-size", type=positive_int, default=100, help="GraphQL connection page size (1-100)")
    parser.add_argument("--poll-initial", type=positive_float, default=60.0, help="Initial watch delay in seconds")
    parser.add_argument("--poll-max", type=positive_float, default=300.0, help="Maximum watch delay in seconds")
    parser.add_argument("--max-wait", type=positive_float, default=1_200.0, help="Maximum total watch time in seconds")
    parser.add_argument("--full-refresh-interval", type=positive_float, default=600.0, help="Maximum seconds between authoritative watch snapshots")
    parser.add_argument("--jitter", type=float, default=0.15, help="Watch jitter ratio from 0 through 0.5")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if args.body_limit < 100:
        parser.error("--body-limit must be at least 100")
    if args.page_size > 100:
        parser.error("--page-size must be at most 100")
    if not 0 <= args.jitter <= 0.5:
        parser.error("--jitter must be between 0 and 0.5")
    if args.poll_max < args.poll_initial:
        parser.error("--poll-max must be at least --poll-initial")

    config = InspectionConfig(
        reserve=args.reserve,
        query_cost_buffer=args.query_cost_buffer,
        max_requests=args.max_requests,
        max_pages=args.max_pages,
        max_seconds=args.max_seconds,
        page_size=args.page_size,
    )
    try:
        repository, number = resolve_target(args.pr, args.repo)
        if args.watch:
            result = watch(
                repository,
                number,
                parse_time(args.after),
                args.body_limit,
                config=config,
                poll_initial=args.poll_initial,
                poll_max=args.poll_max,
                max_wait=args.max_wait,
                full_refresh_interval=args.full_refresh_interval,
                jitter=args.jitter,
            )
        else:
            result = inspect(
                repository,
                number,
                parse_time(args.after),
                args.body_limit,
                config=config,
            )
    except GhError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
