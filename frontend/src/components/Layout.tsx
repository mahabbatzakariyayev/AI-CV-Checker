import { PropsWithChildren } from "react";
import { Link } from "react-router-dom";

type Props = PropsWithChildren<{ title: string; jobId?: string }>;

export default function Layout({ title, jobId, children }: Props) {
  return (
    <div className="container">
      <header className="header">
        <h1>{title}</h1>
        <nav className="nav">
          <Link to="/">Jobs</Link>
          {jobId && (
            <>
              <Link to={`/jobs/${jobId}/setup`}>Setup</Link>
              <Link to={`/jobs/${jobId}/status`}>Status</Link>
              <Link to={`/jobs/${jobId}/ranking`}>Ranking</Link>
            </>
          )}
        </nav>
      </header>
      {children}
      <footer className="footer">
        This system provides decision support. Final hiring decisions should be made by humans.
      </footer>
    </div>
  );
}
