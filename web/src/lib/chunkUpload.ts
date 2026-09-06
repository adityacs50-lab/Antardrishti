/**
 * Vercel's serverless functions hard-cap a request body at 4.5 MB
 * (FUNCTION_PAYLOAD_TOO_LARGE / 413) — not configurable via vercel.json, not
 * something the backend can raise. A real CSV/JSONL export of a few hundred
 * reports can easily cross that. Rather than surface a bare "413" and make
 * the person split the file by hand, split it here and send it as several
 * requests to POST /api/reports/bulk, each safely under the limit.
 */

/** Leaves generous headroom under Vercel's 4.5 MB body cap for multipart overhead. */
const MAX_CHUNK_BYTES = 3_000_000;

/**
 * Split CSV text into rows, respecting quoted fields that contain a literal
 * newline. Not a full RFC 4180 parser, but the only thing that matters here
 * is not breaking a row mid-quote: toggling on every `"` correctly tracks
 * in-quote state even through a doubled `""` escape, since two toggles
 * cancel out.
 */
function splitCsvRows(text: string): string[] {
  const rows: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') inQuotes = !inQuotes;
    if (ch === "\n" && !inQuotes) {
      rows.push(current);
      current = "";
    } else if (ch !== "\r") {
      current += ch;
    }
  }
  if (current.trim()) rows.push(current);
  return rows;
}

function bytesOf(s: string): number {
  return new Blob([s]).size;
}

/**
 * Break one file into a list of Blobs, each under MAX_CHUNK_BYTES, each a
 * complete, independently-parseable CSV or JSONL document. A CSV chunk
 * repeats the header row (parse_upload's csv.DictReader needs it in every
 * upload); JSONL chunks need no such repetition — every line already stands
 * alone. A file already under the limit comes back as a single chunk, so
 * the common case still makes exactly one request.
 */
export async function chunkUploadFile(file: File): Promise<{ blob: Blob; name: string }[]> {
  if (file.size <= MAX_CHUNK_BYTES) {
    return [{ blob: file, name: file.name }];
  }

  const text = await file.text();
  const isCsv = file.name.toLowerCase().endsWith(".csv");
  const ext = isCsv ? "csv" : "jsonl";

  const rows = isCsv ? splitCsvRows(text) : text.split("\n").filter((l) => l.trim());
  if (rows.length === 0) return [{ blob: file, name: file.name }];

  const header = isCsv ? rows[0] : null;
  const dataRows = isCsv ? rows.slice(1) : rows;

  const chunks: string[][] = [];
  let current: string[] = [];
  let currentBytes = header ? bytesOf(header) : 0;

  for (const row of dataRows) {
    const rowBytes = bytesOf(row) + 1; // +1 for the newline that joins it back
    if (current.length > 0 && currentBytes + rowBytes > MAX_CHUNK_BYTES) {
      chunks.push(current);
      current = [];
      currentBytes = header ? bytesOf(header) : 0;
    }
    current.push(row);
    currentBytes += rowBytes;
  }
  if (current.length > 0) chunks.push(current);

  return chunks.map((rowsInChunk, i) => {
    const body = header
      ? [header, ...rowsInChunk].join("\n")
      : rowsInChunk.join("\n");
    return {
      blob: new Blob([body], { type: isCsv ? "text/csv" : "application/json" }),
      name: file.name.replace(/(\.[^.]+)?$/, `.part${i + 1}.${ext}`),
    };
  });
}
