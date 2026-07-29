import type { Metadata } from "next";
import { PolicyPage } from "../site-chrome";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <PolicyPage
      eyebrow="Policy"
      title="Privacy Policy"
      subtitle="Effective July 29, 2026"
    >
      <p>
        Develoop is an open-source bundle of Agent Skills maintained by
        Changkyun Kim. It does not operate developer-controlled user accounts,
        an application backend, or analytics for plugin usage.
      </p>

      <h2>How the skills handle data</h2>
      <p>
        The skills instruct your agent host to inspect repository files and,
        when authorized, interact with GitHub issues, branches, commits, pull
        requests, checks, comments, reactions, and review threads. That work is
        performed by your agent host, a GitHub integration, or the GitHub CLI
        in your environment. Develoop does not receive your GitHub token,
        repository contents, prompts, or generated output.
      </p>

      <h2>State-changing actions</h2>
      <p>
        Depending on your request and permissions, an agent using Develoop may
        create or edit issues, assign issues, create branches and commits, push
        changes, open or update pull requests, reply to or resolve review
        threads, and merge a pull request. The skills require authorization and
        verification gates, but the host remains responsible for enforcing
        permissions and showing any approval prompts.
      </p>

      <h2>Third-party processing</h2>
      <p>
        Codex, Claude Code, Antigravity, GitHub, model providers, connected
        integrations, and local tooling process data under their own policies.
        Review their settings before using Develoop with private or sensitive
        repositories.
      </p>

      <h2>Website data</h2>
      <p>
        This informational website does not use forms, advertising, behavioral
        analytics, tracking pixels, or application cookies. Its hosting
        provider may process ordinary request information such as IP address,
        user agent, timestamp, and requested path for security and reliable
        delivery.
      </p>

      <h2>Contact</h2>
      <p>
        Privacy questions may be sent to{" "}
        <a href="mailto:comfuture@gmail.com">comfuture@gmail.com</a>.
      </p>
    </PolicyPage>
  );
}
