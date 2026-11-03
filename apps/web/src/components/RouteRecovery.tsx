import { Component, useEffect, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "./ui/button";

class PageBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed)
      return (
        <section className="message" role="alert">
          <h1>This page could not open.</h1>
          <p>
            Reload to try again. Saved sources and rehearsals remain in your
            workspace; unsaved edits may need to be entered again.
          </p>
          <div className="session-actions">
            <Button onClick={() => window.location.reload()}>
              Reload page
            </Button>
            <a href="/">Return home</a>
          </div>
        </section>
      );
    return this.props.children;
  }
}

export function RouteRecovery({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  useEffect(() => {
    document.title = "GhostShift · Operational rehearsal";
    const main = document.getElementById("main");
    if (!main) return;
    let focused = false;
    const update = () => {
      const heading = main.querySelector("h1");
      if (!heading) return;
      document.title = `${heading.innerText.replace(/\s+/g, " ").trim()} · GhostShift`;
      if (focused) return;
      const anchor = window.location.hash
        ? document.getElementById(window.location.hash.slice(1))
        : null;
      const target = anchor ?? heading;
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
      if (anchor) anchor.scrollIntoView();
      else window.scrollTo(0, 0);
      focused = true;
    };
    const observer = new MutationObserver(update);
    observer.observe(main, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    update();
    return () => observer.disconnect();
  }, [pathname]);
  return <PageBoundary key={pathname}>{children}</PageBoundary>;
}
