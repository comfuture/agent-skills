import type { Metadata } from "next";
import { PolicyPage } from "../site-chrome";

export const metadata: Metadata = { title: "Support" };

export default function SupportPage() {
  return (
    <PolicyPage
      eyebrow="Help"
      title="Support"
      subtitle="Help with installation, behavior, or the portable GitHub workflow"
    >
      <h2>Report a reproducible problem</h2>
      <p>
        Open an issue in the{" "}
        <a href="https://github.com/comfuture/agent-skills/issues">
          public GitHub repository
        </a>{" "}
        for bugs, documentation problems, or focused feature requests. Include
        the agent host, installation method, relevant tool versions, expected
        behavior, and the smallest safe reproduction.
      </p>

      <div className="notice">
        Remove credentials, private repository contents, customer data, and
        other sensitive material before posting publicly.
      </div>

      <h2>Private contact</h2>
      <p>
        For security or privacy matters that should not be public, email{" "}
        <a href="mailto:comfuture@gmail.com">comfuture@gmail.com</a>.
      </p>

      <h2>Installation quick reference</h2>
      <pre>
        <code>{`# Codex, from a repository checkout
codex plugin marketplace add /absolute/path/to/agent-skills
codex plugin add develoop@develoop

# Claude Code
claude plugin marketplace add comfuture/agent-skills
claude plugin install develoop@develoop --scope user

# Antigravity
agy plugins install https://github.com/comfuture/agent-skills

# Standalone Agent Skills
npx skills add comfuture/agent-skills --skill '*' --agent '*' -y`}</code>
      </pre>
      <p>
        Start a new task or reload plugins after installation so the host can
        discover the new skills.
      </p>
    </PolicyPage>
  );
}
