export function SiteHeader() {
  return (
    <header className="site-header">
      <a className="wordmark" href="/" aria-label="Develoop home">
        <span>deve</span>
        <strong>loop</strong>
      </a>
      <nav aria-label="Primary navigation">
        <a href="/#skills">Skills</a>
        <a href="/#install">Install</a>
        <a href="/support">Support</a>
        <a href="https://github.com/comfuture/agent-skills">
          GitHub <span aria-hidden="true">↗</span>
        </a>
      </nav>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div>
        <a className="wordmark footer-wordmark" href="/">
          <span>deve</span>
          <strong>loop</strong>
        </a>
        <p>Development is a loop. Keep the evidence in it.</p>
      </div>
      <nav aria-label="Policy navigation">
        <a href="/support">Support</a>
        <a href="/releases">Releases</a>
        <a href="/privacy">Privacy</a>
        <a href="/terms">Terms</a>
      </nav>
      <p className="copyright">Created by Changkyun Kim · © 2026</p>
    </footer>
  );
}

export function PolicyPage({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <SiteHeader />
      <main className="policy-page">
        <div className="policy-intro">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <article className="policy-body">{children}</article>
      </main>
      <SiteFooter />
    </>
  );
}
