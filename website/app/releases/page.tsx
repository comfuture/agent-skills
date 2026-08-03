import type { Metadata } from "next";
import { PolicyPage } from "../site-chrome";

export const metadata: Metadata = { title: "Release Notes" };

export default function ReleasesPage() {
  return (
    <PolicyPage
      eyebrow="Changelog"
      title="Release Notes"
      subtitle="Public Develoop release history"
    >
      <p className="release-tag">Quota-safe automated review</p>
      <h2>Develoop 0.1.1</h2>
      <p>
        This patch makes automated review inspection observable, adaptive, and
        complete even when GitHub GraphQL quota or pagination is constrained.
      </p>
      <ul>
        <li>
          Reports per-query GraphQL cost, remaining quota, usage, and reset
          guidance while preserving a configurable reserve.
        </li>
        <li>
          Follows every review-classification cursor, including nested thread
          comments and complete check-context verification.
        </li>
        <li>
          Replaces fixed full-snapshot polling with adaptive backoff, periodic
          authoritative refreshes, and single-observer coordination.
        </li>
        <li>
          Fails closed on missing quota evidence, repeated cursors, partial
          data, unsafe observer locks, and execution-budget exhaustion.
        </li>
      </ul>
      <hr />
      <p className="release-tag">Initial multi-agent release</p>
      <h2>Develoop 0.1.0</h2>
      <p>
        The first Develoop release packages a continuous GitHub delivery loop
        for Codex, Claude Code, Antigravity, and standalone Agent Skills hosts.
      </p>
      <ul>
        <li>
          Renames <code>issue-creator</code> to the consistent{" "}
          <code>gh-create-issue</code> identifier.
        </li>
        <li>
          Packages issue creation, issue implementation, and bounded automated
          review resolution behind host-native adapters.
        </li>
        <li>
          Adds explicit capability mapping for GitHub integrations, CLI
          fallbacks, browser verification, delegation, and approvals.
        </li>
        <li>
          Keeps the separately licensed <code>writing-strategy</code> skill in
          the bundle without using it as Develoop&apos;s product focus.
        </li>
        <li>
          Adds public support, privacy, terms, and release information.
        </li>
      </ul>
      <p>
        Existing standalone users of <code>issue-creator</code> should update
        installation references and invocations to <code>gh-create-issue</code>.
      </p>
      <p>
        Release questions may be sent to{" "}
        <a href="mailto:comfuture@gmail.com">comfuture@gmail.com</a>.
      </p>
    </PolicyPage>
  );
}
