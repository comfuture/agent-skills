import { SiteFooter, SiteHeader } from "./site-chrome";

const workflow = [
  {
    index: "01",
    skill: "gh-create-issue",
    title: "Frame the work",
    body: "Turn repository evidence and user intent into an implementation-ready issue with explicit scope, non-goals, and acceptance criteria.",
  },
  {
    index: "02",
    skill: "gh-implement-issue",
    title: "Ship the change",
    body: "Carry one issue from contract through branch, atomic commits, validation, push, and an accurate pull request.",
  },
  {
    index: "03",
    skill: "gh-autoreview-resolve",
    title: "Resolve the review",
    body: "Run a bounded automated-review loop, validate every finding, prevent scope creep, and verify the final head.",
  },
];

const installs = [
  {
    host: "OpenAI / Codex",
    note: "OpenAI Curated Directory",
    command: "Sign in, open the Develoop listing, and select Add.",
    href: "https://chatgpt.com/plugins/plugins_6a69ee33e3048191ab7da89ec70dbbe2",
  },
  {
    host: "Claude Code",
    note: "Namespaced plugin skills",
    command: `claude plugin marketplace add comfuture/agent-skills
claude plugin install develoop@develoop --scope user`,
  },
  {
    host: "Antigravity",
    note: "Public repository install",
    command: `agy plugins install https://github.com/comfuture/agent-skills
agy plugin list`,
  },
  {
    host: "Standalone",
    note: "Open Agent Skills format",
    command: `npx skills add comfuture/agent-skills --skill '*' --agent '*' -y`,
  },
];

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Portable GitHub workflow skills</p>
            <h1>
              Close the loop
              <br />
              on GitHub work.
            </h1>
            <p className="hero-lede">
              Develoop gives Codex, Claude Code, Antigravity, and standalone
              agents one evidence-first path from a well-framed issue to a
              validated pull request and a resolved review.
            </p>
            <div className="hero-actions">
              <a className="primary-action" href="#install">
                Install Develoop <span aria-hidden="true">↘</span>
              </a>
              <a className="text-action" href="https://github.com/comfuture/agent-skills">
                View source <span aria-hidden="true">↗</span>
              </a>
            </div>
          </div>
          <div className="loop-visual" aria-label="Issue, implementation, and review form a continuous development loop">
            <div className="loop-orbit loop-orbit-outer" />
            <div className="loop-orbit loop-orbit-inner" />
            <span className="loop-node node-one">Issue</span>
            <span className="loop-node node-two">Build</span>
            <span className="loop-node node-three">Review</span>
            <div className="loop-core">
              <span>dev</span>
              <strong>∞</strong>
              <span>loop</span>
            </div>
          </div>
        </section>

        <section className="principle-strip" aria-label="Develoop principles">
          <span>Evidence before edits</span>
          <span>Scope before speed</span>
          <span>Verification before “done”</span>
        </section>

        <section className="workflow-section" id="skills">
          <div className="section-heading">
            <p className="eyebrow">One deliberate loop</p>
            <h2>Three skills. Clear handoffs.</h2>
            <p>
              Each skill can run independently. Together they preserve context
              across the places where GitHub work most often loses it.
            </p>
          </div>
          <div className="workflow-list">
            {workflow.map((step) => (
              <article className="workflow-step" key={step.skill}>
                <span className="step-index">{step.index}</span>
                <div>
                  <code>{step.skill}</code>
                  <h3>{step.title}</h3>
                </div>
                <p>{step.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="portable-section">
          <div>
            <p className="eyebrow">Same contract, native tools</p>
            <h2>Portable by design.</h2>
          </div>
          <div className="portable-copy">
            <p>
              The workflow names capabilities, not one vendor&apos;s buttons.
              Each host uses its own GitHub integration, shell, browser,
              delegation, and approval model while preserving the same
              evidence and safety gates.
            </p>
            <ul>
              <li>Codex and OpenAI presentation metadata</li>
              <li>Claude Code namespaced plugin adapter</li>
              <li>Antigravity minimal plugin adapter</li>
              <li>Open Agent Skills standalone layout</li>
            </ul>
          </div>
        </section>

        <section className="install-section" id="install">
          <div className="section-heading">
            <p className="eyebrow">Choose your host</p>
            <h2>Install once. Start a fresh task.</h2>
          </div>
          <div className="install-grid">
            {installs.map((install) => (
              <article className="install-option" key={install.host}>
                <div>
                  <h3>{install.host}</h3>
                  <span>{install.note}</span>
                </div>
                {install.href ? (
                  <section className="directory-install">
                    <p>{install.command}</p>
                    <a href={install.href}>Open in Plugins Directory ↗</a>
                  </section>
                ) : (
                  <pre>
                    <code>{install.command}</code>
                  </pre>
                )}
              </article>
            ))}
          </div>
          <p className="bundle-note">
            The repository also carries the separately licensed{" "}
            <code>writing-strategy</code> skill. It remains available in the
            bundle without changing Develoop&apos;s GitHub workflow focus.
          </p>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
