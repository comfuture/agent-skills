#!/usr/bin/env python3
"""Inspect one GitHub PR's automated-review state through gh CLI."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


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


class GhError(RuntimeError):
    pass


def run_gh(arguments: list[str]) -> str:
    if shutil.which("gh") is None:
        raise GhError("gh CLI is not installed or not on PATH")
    result = subprocess.run(
        ["gh", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
        raise GhError(detail)
    return result.stdout


def parse_json_output(output: str) -> Any:
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise GhError(f"gh returned invalid JSON: {error}") from error


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


def at_or_after(value: str | None, minimum: datetime | None) -> bool:
    if minimum is None:
        return True
    parsed = parse_time(value)
    return parsed is not None and parsed >= minimum


def is_connector(author: str | None) -> bool:
    login = (author or "").casefold()
    return any(marker in login for marker in CONNECTOR_MARKERS)


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
) -> str:
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


QUERY = r"""
query($owner:String!, $name:String!, $number:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      number
      url
      state
      isDraft
      headRefOid
      mergeStateStatus
      updatedAt
      reactions(last:100) {
        pageInfo { hasPreviousPage }
        nodes { content createdAt user { login } }
      }
      comments(last:100) {
        pageInfo { hasPreviousPage }
        nodes {
          databaseId
          url
          body
          createdAt
          author { login }
          reactions(last:100) {
            pageInfo { hasPreviousPage }
            nodes { content createdAt user { login } }
          }
        }
      }
      reviews(last:100) {
        pageInfo { hasPreviousPage }
        nodes {
          databaseId
          url
          body
          state
          submittedAt
          author { login }
          commit { oid }
        }
      }
      reviewThreads(first:100) {
        pageInfo { hasNextPage }
        nodes {
          id
          isResolved
          comments(first:100) {
            pageInfo { hasNextPage }
            nodes {
              databaseId
              url
              body
              path
              line
              originalLine
              createdAt
              author { login }
            }
          }
        }
      }
      commits(last:1) {
        nodes {
          commit {
            oid
            statusCheckRollup {
              state
              contexts(first:100) {
                pageInfo { hasNextPage }
                nodes {
                  ... on CheckRun { name status conclusion detailsUrl }
                  ... on StatusContext { context state targetUrl }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def inspect(repository: str, number: int, after: datetime | None, body_limit: int) -> dict[str, Any]:
    owner, name = repository.split("/", 1)
    payload = parse_json_output(run_gh([
        "api",
        "graphql",
        "-F", f"owner={owner}",
        "-F", f"name={name}",
        "-F", f"number={number}",
        "-f", f"query={QUERY}",
    ]))
    pr = (((payload.get("data") or {}).get("repository") or {}).get("pullRequest"))
    if pr is None:
        raise GhError(f"pull request {repository}#{number} was not found or is not accessible")

    comments = (pr.get("comments") or {}).get("nodes") or []
    eligible_requests = [
        comment for comment in comments
        if str(comment.get("body") or "").lstrip().startswith("@codex review")
        and at_or_after(comment.get("createdAt"), after)
    ]
    active_request = max(eligible_requests, key=lambda item: item.get("createdAt") or "", default=None)
    trigger_time = parse_time(active_request.get("createdAt")) if active_request else after
    commit_node = (((pr.get("commits") or {}).get("nodes") or [{}])[-1].get("commit") or {})
    current_head_oid = pr.get("headRefOid")
    reaction_head_anchored = bool(
        active_request and request_reviews_head(active_request, current_head_oid)
    )
    pr_reaction_connection = pr.get("reactions") or {}
    request_reaction_connection = (active_request or {}).get("reactions") or {}
    observed_reactions = merge_reaction_counts(
        reaction_counts(pr_reaction_connection.get("nodes"), trigger_time),
        reaction_counts(request_reaction_connection.get("nodes"), trigger_time),
    )
    trigger_reactions = dict(observed_reactions)
    ignored_thumbs_up = 0
    if not reaction_head_anchored:
        ignored_thumbs_up = trigger_reactions["thumbs_up"]
        trigger_reactions["thumbs_up"] = 0

    reviews = (pr.get("reviews") or {}).get("nodes") or []
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

    threads = (pr.get("reviewThreads") or {}).get("nodes") or []
    unresolved_threads = []
    connector_thread_response = False
    nested_pagination = False
    for thread in threads:
        thread_comments = (thread.get("comments") or {}).get("nodes") or []
        nested_pagination = nested_pagination or bool((thread.get("comments") or {}).get("pageInfo", {}).get("hasNextPage"))
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
    connector_response = bool(connector_issue_comments or connector_reviews or connector_thread_response)

    rollup = commit_node.get("statusCheckRollup") or {}
    contexts = (rollup.get("contexts") or {}).get("nodes") or []
    pagination_incomplete = any([
        bool((pr.get("comments") or {}).get("pageInfo", {}).get("hasPreviousPage")),
        bool((pr.get("reviews") or {}).get("pageInfo", {}).get("hasPreviousPage")),
        bool((pr.get("reviewThreads") or {}).get("pageInfo", {}).get("hasNextPage")),
        bool((rollup.get("contexts") or {}).get("pageInfo", {}).get("hasNextPage")),
        bool(pr_reaction_connection.get("pageInfo", {}).get("hasPreviousPage")),
        bool(request_reaction_connection.get("pageInfo", {}).get("hasPreviousPage")),
        nested_pagination,
    ])
    outcome = classify_review_state(
        unresolved_count=len(unresolved_threads),
        eyes=trigger_reactions["eyes"],
        thumbs_up=trigger_reactions["thumbs_up"],
        clean_response=clean_response,
        connector_response=connector_response,
        pagination_incomplete=pagination_incomplete,
    )

    return {
        "repository": repository,
        "pr": {
            "number": pr.get("number"),
            "url": pr.get("url"),
            "state": pr.get("state"),
            "is_draft": pr.get("isDraft"),
            "head_oid": pr.get("headRefOid"),
            "merge_state": pr.get("mergeStateStatus"),
            "updated_at": pr.get("updatedAt"),
        },
        "trigger": {
            "surface": "comment" if active_request else "pull_request",
            "request_comment": None if active_request is None else {
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
            "unresolved_count": len(unresolved_threads),
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
            "head_oid": commit_node.get("oid"),
            "rollup_state": rollup.get("state"),
            "contexts": contexts,
        },
        "pagination_incomplete": pagination_incomplete,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", nargs="?", help="PR number or github.com pull request URL")
    parser.add_argument("--repo", help="Repository in OWNER/REPO format")
    parser.add_argument("--after", help="Ignore older review requests and connector events")
    parser.add_argument("--body-limit", type=int, default=4_000, help="Maximum body characters per item")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    parser.add_argument("--self-test", action="store_true", help="Run state-classifier tests without GitHub")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if args.body_limit < 100:
        parser.error("--body-limit must be at least 100")

    try:
        repository, number = resolve_target(args.pr, args.repo)
        result = inspect(repository, number, parse_time(args.after), args.body_limit)
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
