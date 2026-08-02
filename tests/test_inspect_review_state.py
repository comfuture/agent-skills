from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "gh-autoreview-resolve" / "scripts" / "inspect_review_state.py"
SPEC = importlib.util.spec_from_file_location("inspect_review_state", SCRIPT)
assert SPEC and SPEC.loader
INSPECTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = INSPECTOR
SPEC.loader.exec_module(INSPECTOR)


def preflight(*, remaining: int = 5_000, used: int = 0, reset: int = 1_800_000_000) -> str:
    return json.dumps({
        "resources": {
            "graphql": {
                "limit": 5_000,
                "remaining": remaining,
                "used": used,
                "reset": reset,
            }
        }
    })


def graphql(data: dict[str, Any], *, cost: int = 1, remaining: int = 4_999) -> str:
    return json.dumps({
        "data": {
            **data,
            "rateLimit": {
                "cost": cost,
                "remaining": remaining,
                "used": 5_000 - remaining,
                "resetAt": "2027-01-15T08:00:00Z",
            },
        }
    })


def page(
    nodes: list[dict[str, Any]],
    *,
    has_next: bool,
    cursor: str | None,
    total: int = 101,
) -> dict[str, Any]:
    return {
        "totalCount": total,
        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
        "nodes": nodes,
    }


class QueueRunner:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[list[str]] = []

    def __call__(self, arguments: list[str], timeout: float | None = None) -> str:
        del timeout
        self.calls.append(arguments)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    @property
    def graphql_calls(self) -> list[list[str]]:
        return [call for call in self.calls if call[:2] == ["api", "graphql"]]


class EmptyInspectionRunner:
    def __init__(self, reaction_content: str = "THUMBS_UP") -> None:
        self.calls: list[list[str]] = []
        self.reaction_content = reaction_content

    def __call__(self, arguments: list[str], timeout: float | None = None) -> str:
        del timeout
        self.calls.append(arguments)
        if arguments == ["api", "rate_limit", "--include"]:
            return preflight()
        query = next(value[6:] for value in arguments if value.startswith("query="))
        if "query Base" in query:
            return graphql({
                "repository": {
                    "pullRequest": {
                        "id": "PR_node",
                        "number": 7,
                        "url": "https://github.com/owner/repo/pull/7",
                        "state": "OPEN",
                        "isDraft": False,
                        "headRefOid": "abcdef0123456789abcdef0123456789abcdef01",
                        "mergeStateStatus": "CLEAN",
                        "updatedAt": "2027-01-15T07:00:00Z",
                        "commits": {
                            "nodes": [{
                                "commit": {
                                    "oid": "abcdef0123456789abcdef0123456789abcdef01",
                                    "statusCheckRollup": {"state": "SUCCESS"},
                                }
                            }]
                        },
                    }
                }
            })
        if "query Comments" in query:
            return graphql({
                "repository": {
                    "pullRequest": {
                        "comments": page([{
                            "id": "comment_node",
                            "databaseId": 11,
                            "url": "https://github.com/owner/repo/pull/7#issuecomment-11",
                            "body": "@codex review\nReview head: `abcdef0`",
                            "createdAt": "2027-01-15T07:01:00Z",
                            "author": {"login": "owner"},
                        }], has_next=False, cursor=None, total=1)
                    }
                }
            })
        if "query Reviews" in query:
            return graphql({"repository": {"pullRequest": {"reviews": page([], has_next=False, cursor=None, total=0)}}})
        if "query Threads" in query:
            return graphql({"repository": {"pullRequest": {"reviewThreads": page([], has_next=False, cursor=None, total=0)}}})
        if "query PullRequestReactions" in query:
            return graphql({"repository": {"pullRequest": {"reactions": page([], has_next=False, cursor=None, total=0)}}})
        if "query RequestReactions" in query:
            return graphql({
                "node": {
                    "reactions": page([{
                        "content": self.reaction_content,
                        "createdAt": "2027-01-15T07:02:00Z",
                        "user": {"login": "chatgpt-codex-connector"},
                    }], has_next=False, cursor=None, total=1)
                }
            })
        if "query Checks" in query:
            return graphql({
                "repository": {
                    "pullRequest": {
                        "headRefOid": "abcdef0123456789abcdef0123456789abcdef01",
                        "commits": {
                            "nodes": [{
                                "commit": {
                                    "oid": "abcdef0123456789abcdef0123456789abcdef01",
                                    "statusCheckRollup": {
                                        "state": "SUCCESS",
                                        "contexts": page([], has_next=False, cursor=None, total=0),
                                    },
                                }
                            }]
                        }
                    }
                }
            })
        if "query Transition" in query:
            return graphql({
                "repository": {
                    "pullRequest": {
                        "headRefOid": "abcdef0123456789abcdef0123456789abcdef01",
                        "updatedAt": "2027-01-15T07:00:00Z",
                        "comments": {
                            "totalCount": 1,
                            "nodes": [{
                                "id": "comment_node",
                                "createdAt": "2027-01-15T07:01:00Z",
                            }],
                        },
                        "reviews": {"totalCount": 0, "nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "reactions": {"totalCount": 0, "nodes": []},
                        "commits": {
                            "nodes": [{
                                "commit": {
                                    "statusCheckRollup": {
                                        "state": "SUCCESS",
                                        "contexts": {"totalCount": 0, "nodes": []},
                                    }
                                }
                            }]
                        },
                    }
                },
                "request": {
                    "reactions": {
                        "totalCount": 1,
                        "nodes": [{
                            "content": self.reaction_content,
                            "createdAt": "2027-01-15T07:02:00Z",
                            "user": {"login": "chatgpt-codex-connector"},
                        }],
                    }
                },
            })
        raise AssertionError(f"unexpected query: {query[:80]}")


class MultipageInspectionRunner(EmptyInspectionRunner):
    def __init__(self) -> None:
        super().__init__()
        self.comments = [
            {
                "id": f"comment_{index}",
                "databaseId": index,
                "url": f"https://github.com/owner/repo/pull/7#issuecomment-{index}",
                "body": f"comment {index}",
                "createdAt": f"2027-01-15T06:{index // 60:02d}:{index % 60:02d}Z",
                "author": {"login": "owner"},
            }
            for index in range(100)
        ]
        self.comments.append({
            "id": "active_request",
            "databaseId": 100,
            "url": "https://github.com/owner/repo/pull/7#issuecomment-100",
            "body": "@codex review\nReview head: `abcdef0`",
            "createdAt": "2027-01-15T07:01:00Z",
            "author": {"login": "owner"},
        })
        self.reviews = [
            {
                "databaseId": index,
                "url": f"https://github.com/owner/repo/pull/7#pullrequestreview-{index}",
                "body": f"review {index}",
                "state": "COMMENTED",
                "submittedAt": f"2027-01-15T06:{index // 60:02d}:{index % 60:02d}Z",
                "author": {"login": "reviewer"},
                "commit": {"oid": "abcdef0123456789abcdef0123456789abcdef01"},
            }
            for index in range(101)
        ]
        self.threads = [
            {
                "id": f"thread_{index}",
                "isResolved": True,
                "comments": page([], has_next=False, cursor=None, total=0),
            }
            for index in range(101)
        ]
        self.pull_request_reactions = [
            {
                "content": "EYES",
                "createdAt": f"2027-01-15T06:{index // 60:02d}:{index % 60:02d}Z",
                "user": {"login": "owner"},
            }
            for index in range(100)
        ]
        self.pull_request_reactions.append({
            "content": "EYES",
            "createdAt": "2027-01-15T07:02:00Z",
            "user": {"login": "chatgpt-codex-connector"},
        })
        self.request_reactions = [
            {
                "content": "EYES",
                "createdAt": f"2027-01-15T06:{index // 60:02d}:{index % 60:02d}Z",
                "user": {"login": "owner"},
            }
            for index in range(100)
        ]
        self.request_reactions.append({
            "content": "THUMBS_UP",
            "createdAt": "2027-01-15T07:03:00Z",
            "user": {"login": "chatgpt-codex-connector"},
        })
        self.contexts = [
            {
                "__typename": "CheckRun",
                "name": f"check-{index}",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
                "detailsUrl": f"https://github.com/owner/repo/runs/{index}",
            }
            for index in range(101)
        ]

    @staticmethod
    def _connection(items: list[dict[str, Any]], second_page: bool, name: str) -> dict[str, Any]:
        selected = items[100:] if second_page else items[:100]
        return page(
            selected,
            has_next=not second_page,
            cursor=None if second_page else f"{name}-cursor",
            total=len(items),
        )

    def __call__(self, arguments: list[str], timeout: float | None = None) -> str:
        if arguments == ["api", "rate_limit", "--include"]:
            self.calls.append(arguments)
            return preflight()
        query = next(value[6:] for value in arguments if value.startswith("query="))
        if "query Base" in query:
            return super().__call__(arguments, timeout)

        self.calls.append(arguments)
        second_page = any(value.startswith("cursor=") for value in arguments)
        if "query Comments" in query:
            connection = self._connection(self.comments, second_page, "comments")
            return graphql({"repository": {"pullRequest": {"comments": connection}}})
        if "query Reviews" in query:
            connection = self._connection(self.reviews, second_page, "reviews")
            return graphql({"repository": {"pullRequest": {"reviews": connection}}})
        if "query Threads" in query:
            connection = self._connection(self.threads, second_page, "threads")
            return graphql({"repository": {"pullRequest": {"reviewThreads": connection}}})
        if "query PullRequestReactions" in query:
            connection = self._connection(
                self.pull_request_reactions,
                second_page,
                "pull-request-reactions",
            )
            return graphql({"repository": {"pullRequest": {"reactions": connection}}})
        if "query RequestReactions" in query:
            connection = self._connection(
                self.request_reactions,
                second_page,
                "request-reactions",
            )
            return graphql({"node": {"reactions": connection}})
        if "query Checks" in query:
            connection = self._connection(self.contexts, second_page, "checks")
            return graphql({
                "repository": {
                    "pullRequest": {
                        "headRefOid": "abcdef0123456789abcdef0123456789abcdef01",
                        "commits": {
                            "nodes": [{
                                "commit": {
                                    "oid": "abcdef0123456789abcdef0123456789abcdef01",
                                    "statusCheckRollup": {
                                        "state": "SUCCESS",
                                        "contexts": connection,
                                    },
                                }
                            }]
                        },
                    }
                }
            })
        if "query Transition" in query:
            return graphql({
                "repository": {
                    "pullRequest": {
                        "headRefOid": "abcdef0123456789abcdef0123456789abcdef01",
                        "updatedAt": "2027-01-15T07:00:00Z",
                        "comments": {
                            "totalCount": 101,
                            "nodes": [{
                                "id": "active_request",
                                "createdAt": "2027-01-15T07:01:00Z",
                            }],
                        },
                        "reviews": {
                            "totalCount": 101,
                            "nodes": [{
                                "databaseId": 100,
                                "submittedAt": "2027-01-15T06:01:40Z",
                            }],
                        },
                        "reviewThreads": {
                            "totalCount": 101,
                            "nodes": [
                                {
                                    "id": item["id"],
                                    "isResolved": True,
                                    "comments": {"totalCount": 0},
                                }
                                for item in self.threads[-20:]
                            ],
                        },
                        "reactions": {
                            "totalCount": 101,
                            "nodes": self.pull_request_reactions[-20:],
                        },
                        "commits": {
                            "nodes": [{
                                "commit": {
                                    "statusCheckRollup": {
                                        "state": "SUCCESS",
                                        "contexts": {
                                            "totalCount": 101,
                                            "nodes": self.contexts[-20:],
                                        },
                                    }
                                }
                            }]
                        },
                    }
                },
                "request": {
                    "reactions": {
                        "totalCount": 101,
                        "nodes": self.request_reactions[-20:],
                    }
                },
            })
        raise AssertionError(f"unexpected query: {query[:80]}")


class FinalReserveCrossingRunner(EmptyInspectionRunner):
    def __call__(self, arguments: list[str], timeout: float | None = None) -> str:
        response = super().__call__(arguments, timeout)
        query_values = [value for value in arguments if value.startswith("query=")]
        if query_values and "query Transition" in query_values[0]:
            payload = json.loads(response)
            payload["data"]["rateLimit"].update({
                "cost": 2,
                "remaining": 199,
                "used": 4_801,
            })
            return json.dumps(payload)
        return response


class ChangingOldCheckRunner(EmptyInspectionRunner):
    def __init__(self) -> None:
        super().__init__()
        self.check_calls = 0
        self.initial_contexts = [
            {
                "__typename": "CheckRun",
                "name": f"check-{index}",
                "status": "IN_PROGRESS",
                "conclusion": None,
                "detailsUrl": f"https://github.com/owner/repo/runs/{index}",
            }
            for index in range(21)
        ]

    def __call__(self, arguments: list[str], timeout: float | None = None) -> str:
        response = super().__call__(arguments, timeout)
        query_values = [value for value in arguments if value.startswith("query=")]
        if not query_values:
            return response
        payload = json.loads(response)
        if "query Checks" in query_values[0]:
            self.check_calls += 1
            contexts = [dict(item) for item in self.initial_contexts]
            if self.check_calls == 2:
                contexts[0].update({"status": "COMPLETED", "conclusion": "SUCCESS"})
            rollup = payload["data"]["repository"]["pullRequest"]["commits"]["nodes"][0]["commit"]["statusCheckRollup"]
            rollup["state"] = "PENDING"
            rollup["contexts"] = page(
                contexts,
                has_next=False,
                cursor=None,
                total=21,
            )
            return json.dumps(payload)
        if "query Transition" in query_values[0]:
            rollup = payload["data"]["repository"]["pullRequest"]["commits"]["nodes"][0]["commit"]["statusCheckRollup"]
            rollup["state"] = "PENDING"
            rollup["contexts"] = {
                "totalCount": 21,
                "nodes": self.initial_contexts[-20:],
            }
            return json.dumps(payload)
        return response


class InspectReviewStateTests(unittest.TestCase):
    def test_unavailable_preflight_fails_closed_without_graphql(self) -> None:
        runner = QueueRunner([INSPECTOR.GhError("network unavailable")])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Test", "query Test { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "preflight_unavailable")
        self.assertEqual(runner.graphql_calls, [])
        self.assertIn("network unavailable", session.telemetry()["preflight"]["error"])

    def test_preflight_missing_remaining_fails_closed_without_graphql(self) -> None:
        runner = QueueRunner([json.dumps({
            "resources": {"graphql": {"limit": 5_000, "used": 1}}
        })])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Test", "query Test { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "preflight_unavailable")
        self.assertEqual(runner.graphql_calls, [])
        self.assertIn("omitted", session.telemetry()["preflight"]["error"])

    def test_reserve_preflight_blocks_graphql_and_reports_reset(self) -> None:
        runner = QueueRunner([preflight(remaining=200, used=4_800)])
        session = INSPECTOR.GraphQLSession(
            INSPECTOR.InspectionConfig(reserve=200, query_cost_buffer=1),
            runner,
        )

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Test", "query Test { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "rate_limited")
        self.assertEqual(runner.graphql_calls, [])
        self.assertEqual(session.telemetry()["preflight"]["remaining"], 200)
        self.assertEqual(
            session.telemetry()["preflight"]["reset_at"],
            "2027-01-15T08:00:00Z",
        )

    def test_graphql_pages_emit_cost_and_remaining_telemetry(self) -> None:
        runner = QueueRunner([
            preflight(),
            graphql({"page": page([{"id": index} for index in range(100)], has_next=True, cursor="cursor-1")}, cost=2, remaining=4_998),
            graphql({"page": page([{"id": 100}], has_next=False, cursor=None)}, cost=1, remaining=4_997),
        ])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        nodes, total = INSPECTOR.collect_pages(
            session,
            "comments",
            lambda cursor: session.graphql(
                "Page",
                "query Page($cursor:String) { page(after:$cursor) { nodes { id } } rateLimit { cost } }",
                {"cursor": cursor},
                connection="comments",
                cursor=cursor,
            )["page"],
        )

        self.assertEqual(len(nodes), 101)
        self.assertEqual(total, 101)
        self.assertEqual(session.page_counts["comments"], 2)
        telemetry = session.telemetry()["graphql"]
        self.assertEqual(telemetry["cost"], 1)
        self.assertEqual(telemetry["total_cost"], 3)
        self.assertEqual(telemetry["remaining"], 4_997)
        self.assertEqual(telemetry["used"], 3)
        self.assertEqual(telemetry["requests"], 2)

    def test_every_top_level_connection_can_advance_past_100_items(self) -> None:
        responses: list[str | Exception] = [preflight()]
        for offset in range(len(INSPECTOR.REQUIRED_CONNECTIONS)):
            responses.extend([
                graphql({"page": page([{"id": index} for index in range(100)], has_next=True, cursor=f"cursor-{offset}")}, remaining=4_999 - (offset * 2)),
                graphql({"page": page([{"id": 100}], has_next=False, cursor=None)}, remaining=4_998 - (offset * 2)),
            ])
        runner = QueueRunner(responses)
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        for connection in INSPECTOR.REQUIRED_CONNECTIONS:
            nodes, total = INSPECTOR.collect_pages(
                session,
                connection,
                lambda cursor: session.graphql(
                    "Page",
                    "query Page($cursor:String) { page(after:$cursor) { nodes { id } } rateLimit { cost } }",
                    {"cursor": cursor},
                    connection=connection,
                    cursor=cursor,
                )["page"],
            )
            self.assertEqual((len(nodes), total), (101, 101))
            self.assertEqual(session.page_counts[connection], 2)

    def test_nested_thread_comments_start_after_embedded_page_and_advance(self) -> None:
        runner = QueueRunner([
            preflight(),
            graphql({"page": page([{"id": 100}], has_next=True, cursor="nested-2")}),
            graphql({"page": page([{"id": 101}], has_next=False, cursor=None, total=102)}),
        ])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        nodes, total = INSPECTOR.collect_pages(
            session,
            "review_thread_comments:thread-1",
            lambda cursor: session.graphql(
                "Nested",
                "query Nested($cursor:String) { page(after:$cursor) { nodes { id } } rateLimit { cost } }",
                {"cursor": cursor},
                connection="review_thread_comments:thread-1",
                cursor=cursor,
            )["page"],
            initial_cursor="nested-1",
        )

        self.assertEqual([node["id"] for node in nodes], [100, 101])
        self.assertEqual(total, 102)
        self.assertTrue(any("cursor=nested-1" in item for item in runner.graphql_calls[0]))
        self.assertTrue(any("cursor=nested-2" in item for item in runner.graphql_calls[1]))

    def test_repeated_cursor_fails_closed_without_repeating_request(self) -> None:
        runner = QueueRunner([
            preflight(),
            graphql({"page": page([], has_next=True, cursor="same")}),
        ])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            INSPECTOR.collect_pages(
                session,
                "nested",
                lambda cursor: session.graphql(
                    "Nested",
                    "query Nested($cursor:String) { page(after:$cursor) { nodes { id } } rateLimit { cost } }",
                    {"cursor": cursor},
                    connection="nested",
                    cursor=cursor,
                )["page"],
                initial_cursor="same",
            )

        self.assertEqual(caught.exception.outcome, "pagination_incomplete")
        self.assertIn("no progress", caught.exception.reason)
        self.assertEqual(len(runner.graphql_calls), 1)

    def test_quota_reserve_stops_before_next_page(self) -> None:
        runner = QueueRunner([
            preflight(remaining=202),
            graphql({"page": page([], has_next=True, cursor="next")}, remaining=200),
        ])
        session = INSPECTOR.GraphQLSession(
            INSPECTOR.InspectionConfig(reserve=200, query_cost_buffer=1),
            runner,
        )

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            INSPECTOR.collect_pages(
                session,
                "comments",
                lambda cursor: session.graphql(
                    "Page",
                    "query Page($cursor:String) { page(after:$cursor) { nodes { id } } rateLimit { cost } }",
                    {"cursor": cursor},
                    connection="comments",
                    cursor=cursor,
                )["page"],
            )

        self.assertEqual(caught.exception.outcome, "rate_limited")
        self.assertEqual(len(runner.graphql_calls), 1)

    def test_query_crossing_reserve_fails_closed_after_response(self) -> None:
        runner = QueueRunner([
            preflight(remaining=201),
            graphql({"viewer": {"login": "owner"}}, cost=2, remaining=199),
        ])
        session = INSPECTOR.GraphQLSession(
            INSPECTOR.InspectionConfig(reserve=200, query_cost_buffer=1),
            runner,
        )

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Final", "query Final { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "rate_limited")
        self.assertIn("crossed reserve", caught.exception.reason)
        self.assertEqual(session.telemetry()["graphql"]["remaining"], 199)

    def test_page_ceiling_stops_before_repeating_connection(self) -> None:
        runner = QueueRunner([
            preflight(),
            graphql({"page": page([], has_next=True, cursor="next")}),
        ])
        session = INSPECTOR.GraphQLSession(
            INSPECTOR.InspectionConfig(max_pages=1),
            runner,
        )

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            INSPECTOR.collect_pages(
                session,
                "comments",
                lambda cursor: session.graphql(
                    "Page",
                    "query Page($cursor:String) { page(after:$cursor) { nodes { id } } rateLimit { cost } }",
                    {"cursor": cursor},
                    connection="comments",
                    cursor=cursor,
                )["page"],
            )

        self.assertEqual(caught.exception.outcome, "budget_exhausted")
        self.assertEqual(len(runner.graphql_calls), 1)

    def test_execution_time_ceiling_stops_before_graphql(self) -> None:
        runner = QueueRunner([preflight()])
        session = INSPECTOR.GraphQLSession(
            INSPECTOR.InspectionConfig(max_seconds=1),
            runner,
        )
        session.query_seconds = 1

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Page", "query Page { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "budget_exhausted")
        self.assertEqual(runner.graphql_calls, [])

    def test_final_query_crossing_execution_ceiling_fails_closed(self) -> None:
        class Clock:
            now = 0.0

            def monotonic(self) -> float:
                return self.now

        clock = Clock()

        class SlowRunner(QueueRunner):
            def __call__(self, arguments: list[str], timeout: float | None = None) -> str:
                response = super().__call__(arguments, timeout)
                if arguments[:2] == ["api", "graphql"]:
                    clock.now += 2
                return response

        runner = SlowRunner([
            preflight(),
            graphql({"viewer": {"login": "owner"}}),
        ])
        session = INSPECTOR.GraphQLSession(
            INSPECTOR.InspectionConfig(max_seconds=1),
            runner,
            monotonic=clock.monotonic,
        )

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Final", "query Final { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "budget_exhausted")
        self.assertIn("crossed execution-time ceiling", caught.exception.reason)

    def test_production_runner_preserves_retry_after_header_on_error(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh", "api", "graphql"],
            returncode=1,
            stdout=(
                "HTTP/2.0 403 Forbidden\n"
                "Retry-After: 60\n\n"
                '{"message":"You have exceeded a secondary rate limit"}'
            ),
            stderr="gh: HTTP 403",
        )
        with (
            mock.patch.object(INSPECTOR.shutil, "which", return_value="/usr/bin/gh"),
            mock.patch.object(INSPECTOR.subprocess, "run", return_value=completed),
        ):
            with self.assertRaises(INSPECTOR.GhError) as caught:
                INSPECTOR.run_gh(["api", "graphql", "--include"], timeout=10)

        self.assertTrue(INSPECTOR.is_secondary_rate_limit(str(caught.exception)))
        self.assertEqual(INSPECTOR.parse_retry_after(str(caught.exception)), 60)

    def test_production_runner_turns_subprocess_timeout_into_gh_timeout(self) -> None:
        expired = subprocess.TimeoutExpired(cmd=["gh", "api", "graphql"], timeout=1)
        with (
            mock.patch.object(INSPECTOR.shutil, "which", return_value="/usr/bin/gh"),
            mock.patch.object(INSPECTOR.subprocess, "run", side_effect=expired),
        ):
            with self.assertRaises(INSPECTOR.GhTimeout):
                INSPECTOR.run_gh(["api", "graphql", "--include"], timeout=1)

    def test_session_classifies_runner_timeout_as_budget_exhausted(self) -> None:
        runner = QueueRunner([
            preflight(),
            INSPECTOR.GhTimeout("gh request timed out after 1s"),
        ])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Page", "query Page { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "budget_exhausted")
        self.assertEqual(len(runner.graphql_calls), 1)

    def test_secondary_limit_is_not_retried(self) -> None:
        runner = QueueRunner([
            preflight(),
            INSPECTOR.GhError("You have exceeded a secondary rate limit. Retry-After: 60"),
        ])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Page", "query Page { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "rate_limited")
        self.assertEqual(caught.exception.retry_after, 60)
        self.assertIn("secondary", caught.exception.reason)
        self.assertEqual(len(runner.graphql_calls), 1)

    def test_primary_limit_graphql_error_is_not_retried(self) -> None:
        runner = QueueRunner([
            preflight(),
            json.dumps({
                "data": None,
                "errors": [{"message": "API rate limit exceeded for user"}],
            }),
        ])
        session = INSPECTOR.GraphQLSession(INSPECTOR.InspectionConfig(), runner)

        with self.assertRaises(INSPECTOR.InspectionStop) as caught:
            session.graphql("Page", "query Page { viewer { login } }", {})

        self.assertEqual(caught.exception.outcome, "rate_limited")
        self.assertIn("primary", caught.exception.reason)
        self.assertEqual(len(runner.graphql_calls), 1)

    def test_full_mocked_snapshot_preserves_anchored_pass_semantics(self) -> None:
        runner = EmptyInspectionRunner()

        result = INSPECTOR.inspect(
            "owner/repo",
            7,
            None,
            4_000,
            runner=runner,
        )

        self.assertEqual(result["review"]["outcome"], "passed")
        self.assertEqual(result["review"]["unresolved_count"], 0)
        self.assertTrue(result["pagination"]["complete"])
        self.assertTrue(result["trigger"]["reaction_head_anchored"])
        self.assertEqual(result["trigger"]["reactions"]["thumbs_up"], 1)
        self.assertEqual(result["rate_limit"]["graphql"]["total_cost"], 9)
        self.assertNotIn("reactions", INSPECTOR.COMMENTS_QUERY.casefold())
        self.assertIn("node(id:$requestId)", INSPECTOR.REQUEST_REACTIONS_QUERY)

    def test_full_mocked_snapshot_wires_every_top_level_cursor(self) -> None:
        runner = MultipageInspectionRunner()

        result = INSPECTOR.inspect(
            "owner/repo",
            7,
            None,
            4_000,
            runner=runner,
        )

        self.assertEqual(result["review"]["outcome"], "passed")
        self.assertTrue(result["inspection"]["complete"])
        self.assertEqual(result["review"]["unresolved_count"], 0)
        for connection in INSPECTOR.REQUIRED_CONNECTIONS:
            self.assertEqual(result["pagination"]["pages"][connection], 2)
            self.assertEqual(result["activity"][connection], 101)

    def test_final_snapshot_query_cannot_cross_reserve_and_report_complete(self) -> None:
        result = INSPECTOR.inspect(
            "owner/repo",
            7,
            None,
            4_000,
            config=INSPECTOR.InspectionConfig(
                reserve=200,
                query_cost_buffer=1,
            ),
            runner=FinalReserveCrossingRunner(),
        )

        self.assertEqual(result["inspection"]["outcome"], "rate_limited")
        self.assertFalse(result["inspection"]["complete"])
        self.assertEqual(result["review"]["outcome"], "rate_limited")
        self.assertIsNone(result["review"]["unresolved_count"])

    def test_check_change_outside_last_twenty_fails_snapshot_closed(self) -> None:
        result = INSPECTOR.inspect(
            "owner/repo",
            7,
            None,
            4_000,
            runner=ChangingOldCheckRunner(),
        )

        self.assertEqual(result["inspection"]["outcome"], "pagination_incomplete")
        self.assertFalse(result["inspection"]["complete"])
        self.assertIsNone(result["review"]["unresolved_count"])
        self.assertEqual(
            result["pagination"]["unfinished"][0]["connection"],
            "check_contexts_verify",
        )

    def test_partial_data_cannot_report_success_or_zero_unresolved(self) -> None:
        runner = EmptyInspectionRunner()
        result = INSPECTOR.inspect(
            "owner/repo",
            7,
            None,
            4_000,
            config=INSPECTOR.InspectionConfig(max_requests=2),
            runner=runner,
        )

        self.assertEqual(result["review"]["outcome"], "budget_exhausted")
        self.assertIsNone(result["review"]["unresolved_count"])
        self.assertFalse(result["pagination"]["complete"])
        self.assertTrue(result["pagination_incomplete"])

    def test_backoff_is_exponential_capped_and_jitter_bounded(self) -> None:
        exact = [
            INSPECTOR.backoff_seconds(index, 60, 300, 0.15, 0.5)
            for index in range(5)
        ]
        self.assertEqual(exact, [60, 120, 240, 300, 300])
        self.assertEqual(INSPECTOR.backoff_seconds(0, 60, 300, 0.15, 0.0), 51)
        self.assertEqual(INSPECTOR.backoff_seconds(0, 60, 300, 0.15, 1.0), 69)
        self.assertLessEqual(INSPECTOR.backoff_seconds(9, 60, 300, 0.15, 1.0), 300)

    def test_single_observer_lock_rejects_duplicate_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = INSPECTOR.ObserverLock("owner/repo", 7, root)
            duplicate = INSPECTOR.ObserverLock("owner/repo", 7, root)
            first.acquire()
            try:
                with self.assertRaises(INSPECTOR.InspectionStop) as caught:
                    duplicate.acquire()
                self.assertEqual(caught.exception.outcome, "observer_active")
            finally:
                first.release()

            duplicate.acquire()
            duplicate.release()

    def test_advisory_lock_reuses_stale_metadata_without_unlinking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stale = INSPECTOR.ObserverLock("owner/repo", 7, root)
            stale.path.write_text(
                json.dumps({"pid": 999_999_999, "started_at": "2020-01-01T00:00:00Z"}),
                encoding="utf-8",
            )
            inode = stale.path.stat().st_ino

            stale.acquire()
            stale.release()

            self.assertEqual(stale.path.stat().st_ino, inode)
            metadata = json.loads(stale.path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["pid"], INSPECTOR.os.getpid())

    @unittest.skipUnless(hasattr(INSPECTOR.os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_observer_lock_refuses_symlink_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.txt"
            target.write_text("must stay intact", encoding="utf-8")
            lock_path = root / "develoop-owner_repo-7.lock"
            lock_path.symlink_to(target)
            lock = INSPECTOR.ObserverLock("owner/repo", 7, root)

            with self.assertRaises(INSPECTOR.InspectionStop) as caught:
                lock.acquire()

            self.assertEqual(caught.exception.outcome, "observer_unavailable")
            self.assertEqual(target.read_text(encoding="utf-8"), "must stay intact")

    def test_timing_parser_rejects_non_finite_values(self) -> None:
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value):
                with self.assertRaises(INSPECTOR.argparse.ArgumentTypeError):
                    INSPECTOR.positive_float(value)

    def test_unchanged_watch_uses_lightweight_probe_without_full_resnapshot(self) -> None:
        runner = EmptyInspectionRunner(reaction_content="EYES")

        class Clock:
            now = 0.0

            def monotonic(self) -> float:
                return self.now

            def sleep(self, seconds: float) -> None:
                self.now += seconds

        class NoopLock:
            def __init__(self, *_: Any, **__: Any) -> None:
                pass

            def acquire(self) -> None:
                pass

            def release(self) -> None:
                pass

        clock = Clock()
        with mock.patch.object(INSPECTOR, "ObserverLock", NoopLock):
            result = INSPECTOR.watch(
                "owner/repo",
                7,
                None,
                4_000,
                config=INSPECTOR.InspectionConfig(),
                poll_initial=60,
                poll_max=300,
                max_wait=61,
                full_refresh_interval=600,
                jitter=0,
                runner=runner,
                sleep=clock.sleep,
                monotonic=clock.monotonic,
            )

        queries = [
            next(value[6:] for value in call if value.startswith("query="))
            for call in runner.calls
            if call[:2] == ["api", "graphql"]
        ]
        self.assertEqual(result["observer"]["outcome"], "watch_timeout")
        self.assertEqual(result["observer"]["probes"], 1)
        self.assertEqual(sum("query Base" in query for query in queries), 1)
        self.assertEqual(sum("query Threads" in query for query in queries), 1)
        self.assertEqual(sum("query Checks" in query for query in queries), 2)
        self.assertEqual(sum("query Transition" in query for query in queries), 2)

    def test_unchanged_watch_forces_periodic_authoritative_snapshot(self) -> None:
        runner = EmptyInspectionRunner(reaction_content="EYES")

        class Clock:
            now = 0.0

            def monotonic(self) -> float:
                return self.now

            def sleep(self, seconds: float) -> None:
                self.now += seconds

        class NoopLock:
            def __init__(self, *_: Any, **__: Any) -> None:
                pass

            def acquire(self) -> None:
                pass

            def release(self) -> None:
                pass

        clock = Clock()
        with mock.patch.object(INSPECTOR, "ObserverLock", NoopLock):
            result = INSPECTOR.watch(
                "owner/repo",
                7,
                None,
                4_000,
                config=INSPECTOR.InspectionConfig(),
                poll_initial=60,
                poll_max=300,
                max_wait=61,
                full_refresh_interval=60,
                jitter=0,
                runner=runner,
                sleep=clock.sleep,
                monotonic=clock.monotonic,
            )

        queries = [
            next(value[6:] for value in call if value.startswith("query="))
            for call in runner.calls
            if call[:2] == ["api", "graphql"]
        ]
        self.assertEqual(result["observer"]["outcome"], "watch_timeout")
        self.assertEqual(sum("query Base" in query for query in queries), 2)
        self.assertEqual(sum("query Threads" in query for query in queries), 2)
        self.assertEqual(sum("query Checks" in query for query in queries), 4)
        self.assertEqual(sum("query Transition" in query for query in queries), 3)


if __name__ == "__main__":
    unittest.main()
