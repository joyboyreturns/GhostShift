import type { SourceDocument } from "../../lib/api";
export function SourcePanel({
  document,
  refs,
}: {
  document: SourceDocument;
  refs: string[];
}) {
  return (
    <div
      className="source-content"
      tabIndex={0}
      role="region"
      aria-label="Source text"
    >
      {document.source_type === "pdf" && (
        <div className="pdf-extraction-note">
          <span className="badge">
            Extracted PDF text · {document.page_count} pages
          </span>
          <p>
            Reading order may differ from the original PDF. Check the original
            before approving rules. The file is not retained; its hash and
            extracted text are preserved.
          </p>
          {(document.empty_pages?.length ?? 0) > 0 && (
            <p className="action-error">
              No extractable text on page(s) {document.empty_pages?.join(", ")}.
              Review those pages separately; OCR is not included.
            </p>
          )}
          <p className="hash-value">
            Original PDF SHA-256: {document.original_file_hash}
          </p>
        </div>
      )}

      {document.segments.map((segment) => (
        <article
          key={segment.id}
          data-testid={`segment-${segment.ordinal}`}
          data-highlighted={refs.includes(segment.id)}
          className={`source-segment ${refs.includes(segment.id) ? "highlighted" : ""}`}
        >
          <span className="segment-number">
            §{String(segment.ordinal).padStart(2, "0")}
          </span>
          {segment.page_number != null && (
            <span className="source-page-number">
              PDF page {segment.page_number}
            </span>
          )}
          <p>{segment.text}</p>
          {refs.includes(segment.id) && (
            <span className="source-tag">Cited by selected rule</span>
          )}
        </article>
      ))}
    </div>
  );
}
