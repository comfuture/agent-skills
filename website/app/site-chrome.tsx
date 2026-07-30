import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="wordmark" href="/" aria-label="Develoop home">
        <span>deve</span>
        <strong>loop</strong>
      </Link>
      <nav aria-label="Primary navigation">
        <Link href="/#skills">Skills</Link>
        <Link href="/#install">Install</Link>
        <Link href="/support">Support</Link>
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
        <Link className="wordmark footer-wordmark" href="/">
          <span>deve</span>
          <strong>loop</strong>
        </Link>
        <p>Development is a loop. Keep the evidence in it.</p>
      </div>
      <nav aria-label="Policy navigation">
        <Link href="/support">Support</Link>
        <Link href="/releases">Releases</Link>
        <Link href="/privacy">Privacy</Link>
        <Link href="/terms">Terms</Link>
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
