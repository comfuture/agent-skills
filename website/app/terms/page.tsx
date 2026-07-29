import type { Metadata } from "next";
import { PolicyPage } from "../site-chrome";

export const metadata: Metadata = { title: "Terms of Use" };

export default function TermsPage() {
  return (
    <PolicyPage
      eyebrow="Policy"
      title="Terms of Use"
      subtitle="Effective July 29, 2026"
    >
      <p>
        Develoop is open-source software, not a hosted development service.
        Repository code, scripts, metadata, and the three GitHub workflow skills
        are provided under the MIT License. The bundled{" "}
        <code>writing-strategy</code> content is separately provided under
        CC-BY-NC-SA-4.0.
      </p>

      <h2>Your authority and responsibility</h2>
      <p>
        Use Develoop only with repositories and GitHub resources you are
        authorized to access or modify. You are responsible for reviewing agent
        plans, diffs, commands, issue and pull-request text, review replies,
        merge decisions, and other outputs before relying on or publishing
        them.
      </p>

      <h2>State changes and backups</h2>
      <p>
        Agent workflows may change local files and remote GitHub state. Maintain
        appropriate backups, branch protections, required reviews, least-
        privilege credentials, and recovery procedures. Do not include secrets
        or sensitive data in prompts, issues, comments, or public logs.
      </p>

      <h2>No warranty</h2>
      <p>
        The software and skill content are provided “as is,” without warranty of
        any kind. To the fullest extent permitted by law, the authors and
        copyright holders are not liable for claims, damages, data loss,
        incorrect output, security incidents, costs, or other liability arising
        from the software or its use.
      </p>

      <h2>Third-party terms</h2>
      <p>
        GitHub, Codex, Claude Code, Antigravity, model providers, integrations,
        package managers, and hosting services are governed by their own terms.
        You are responsible for complying with them.
      </p>

      <h2>Contact</h2>
      <p>
        Questions may be sent to{" "}
        <a href="mailto:comfuture@gmail.com">comfuture@gmail.com</a>.
      </p>
    </PolicyPage>
  );
}
