import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, policyApi } from "../lib/api";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { SourcePanel } from "../features/documents/SourcePanel";
export function Import() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"paste" | "pdf">("paste");
  const [file, setFile] = useState<File>();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceType, setSourceType] = useState<"text" | "markdown">("markdown");
  const mutation = useMutation({
    mutationFn: () => {
      if (mode === "pdf") {
        if (!file) throw new Error("Choose a PDF first.");
        return api.importPdf(title, file);
      }
      return api.import(title, content, sourceType);
    },
  });
  const draft = useMutation({
    mutationFn: () => policyApi.draft(mutation.data!.id, mutation.data!.title),
    onSuccess: (result) => navigate(`/review/${result.id}?edit=1`),
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    mutation.mutate();
  }
  return (
    <section className="import-page">
      <span className="eyebrow">Source Studio / Import</span>
      <h1>Start with the source.</h1>
      <p className="muted">
        Paste a text or Markdown procedure. Blank lines create stable source
        sections. Then model decision rules and review their source evidence.
      </p>
      <div className="import-modes" role="group" aria-label="Import method">
        <Button
          variant="outline"
          aria-pressed={mode === "paste"}
          onClick={() => {
            setMode("paste");
            mutation.reset();
          }}
        >
          Paste text or Markdown
        </Button>
        <Button
          variant="outline"
          aria-pressed={mode === "pdf"}
          onClick={() => {
            setMode("pdf");
            mutation.reset();
          }}
        >
          Upload PDF
        </Button>
      </div>
      <form onSubmit={submit}>
        <label htmlFor="title">Document title</label>
        <input
          id="title"
          required
          maxLength={200}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        {mode === "pdf" ? (
          <>
            <label htmlFor="pdf-file">Text-based PDF</label>
            <input
              id="pdf-file"
              type="file"
              accept="application/pdf,.pdf"
              required
              onChange={(event) => {
                setFile(event.target.files?.[0]);
                mutation.reset();
              }}
            />
            <p className="muted">
              Up to 256 KiB and 20 pages. Encrypted or scanned-only PDFs are
              unsupported. Review extraction before modeling rules.
            </p>
          </>
        ) : (
          <>
            <label htmlFor="type">Source format</label>
            <select
              id="type"
              value={sourceType}
              onChange={(e) =>
                setSourceType(e.target.value as "text" | "markdown")
              }
            >
              <option value="markdown">Markdown</option>
              <option value="text">Plain text</option>
            </select>
            <label htmlFor="content">Procedure text</label>
            <textarea
              id="content"
              required
              maxLength={100000}
              rows={12}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </>
        )}
        <div className="form-footer">
          <span>
            {mode === "pdf"
              ? file
                ? `${(file.size / 1024).toFixed(1)} KiB selected`
                : "Choose a PDF"
              : `${content.length.toLocaleString()} / 100,000 characters`}
          </span>
          <Button
            disabled={
              mutation.isPending ||
              !title.trim() ||
              (mode === "pdf"
                ? !file || file.size > 256 * 1024
                : !content.trim())
            }
          >
            {mutation.isPending ? "Importing…" : "Import document"}
          </Button>
        </div>
      </form>
      {mutation.error && (
        <p role="alert">
          Import failed: {mutation.error.message}. Your text has been preserved.
        </p>
      )}
      {mutation.data && (
        <section aria-label="Imported source" aria-live="polite">
          <h2>Imported {mutation.data.segments.length} source sections</h2>
          <p className="muted">
            Saved as {mutation.data.id}. This document has no modeled graph yet.
          </p>
          <Button disabled={draft.isPending} onClick={() => draft.mutate()}>
            {draft.isPending ? "Creating…" : "Model decision rules"}
          </Button>
          {draft.error && <p role="alert">{draft.error.message}</p>}
          <p>
            <Link to={`/sources/${mutation.data.id}`}>Open saved source ↗</Link>
          </p>
          <SourcePanel document={mutation.data} refs={[]} />
        </section>
      )}
    </section>
  );
}
