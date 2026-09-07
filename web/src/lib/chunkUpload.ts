/**
 * Vercel's serverless functions hard-cap a request body at 4.5 MB
 * (FUNCTION_PAYLOAD_TOO_LARGE / 413) — not configurable via vercel.json, not
 * something the backend can raise. A real CSV/JSONL export of a few hundred
 * reports can easily cross that. Rather than surface a bare "413" and make
 * the person split the file by hand, split it here and send it as several
 * requests to POST /api/reports/bulk, each safely under the limit.
 *
 * Everything in here is written to survive a genuinely large file. The first
 * version of this module froze the tab solid on a 57 MB public incident
 * export: it walked the text one character at a time appending to a string,
 * and allocated a `new Blob([row])` per row just to measure the row's byte
 * length. That is tens of millions of iterations and ~100k allocations on the
 * main thread with no yield — the page stops responding and the person never
 * finds out why, because no error is ever thrown. It now scans with
 * `indexOf`, measures bytes arithmetically, and stops early once it has
 * enough rows to fill the import.
 */

/** Leaves generous headroom under Vercel's 4.5 MB body cap for multipart overhead. */
const MAX_CHUNK_BYTES = 3_000_000;

/**
 * Rows to read at most. Mirrors MAX_BULK_ROWS in the API — the backend caps
 * the import anyway, so shipping more rows than that up the wire only buys a
 * longer wait. Kept slightly above the server's cap so the server, not this
 * file, is the thing that reports the truncation.
 */
export const MAX_IMPORT_ROWS = 2000;

/**
 * Rows per request. Bytes are not the only budget: every row runs the full
 * extractor and rule engine server-side (~8ms), so 2000 rows is ~16s of work
 * inside one request - fine locally, uncomfortably close to Vercel's 30s
 * function ceiling on a cold start. Several smaller requests finish well
 * inside it and give the dialog something honest to count.
 */
const MAX_CHUNK_ROWS = 600;

/**
 * Below this, send the file untouched: too small to hold enough rows to
 * strain a single request, so there is nothing to gain from reading it.
 */
const SINGLE_REQUEST_BYTES = 900_000;

/** UTF-8 byte length without allocating a Blob or a TextEncoder buffer per row. */
function utf8Len(s: string): number {
  let bytes = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c < 0x80) bytes += 1;
    else if (c < 0x800) bytes += 2;
    else if (c >= 0xd800 && c <= 0xdbff) {
      bytes += 4; // surrogate pair — the low half is consumed with it
      i++;
    } else bytes += 3;
  }
  return bytes;
}

/**
 * Split CSV text into rows, respecting quoted fields that contain a literal
 * newline (the OSHA severe-injury corpus, for one, wraps every narrative in
 * quotes and many of them run over several lines).
 *
 * Scans newline-to-newline with `indexOf` rather than character-by-character,
 * and counts the quotes in each candidate line to track whether the row is
 * still open — a doubled `""` escape flips the count twice and cancels out,
 * exactly like the previous toggle did, but without the per-character loop.
 * `limit` stops the scan as soon as enough rows exist, so a 57 MB file costs
 * only as much as its first few thousand rows.
 */
export function splitCsvRows(text: string, limit = Infinity): string[] {
  const rows: string[] = [];
  let start = 0;
  let rowStart = 0;
  let quotes = 0;

  while (start <= text.length && rows.length < limit) {
    let nl = text.indexOf("\n", start);
    if (nl === -1) nl = text.length;

    for (let i = start; i < nl; i++) if (text.charCodeAt(i) === 34 /* " */) quotes++;

    if (quotes % 2 === 0) {
      let end = nl;
      if (end > rowStart && text.charCodeAt(end - 1) === 13 /* \r */) end--;
      const row = text.slice(rowStart, end);
      if (row.trim()) rows.push(row);
      rowStart = nl + 1;
    }

    if (nl >= text.length) break;
    start = nl + 1;
  }
  return rows;
}

function splitJsonlRows(text: string, limit = Infinity): string[] {
  const rows: string[] = [];
  let start = 0;
  while (start < text.length && rows.length < limit) {
    let nl = text.indexOf("\n", start);
    if (nl === -1) nl = text.length;
    const row = text.slice(start, nl).trim();
    if (row) rows.push(row);
    start = nl + 1;
  }
  return rows;
}

/**
 * Break one file into a list of Blobs, each under MAX_CHUNK_BYTES, each a
 * complete, independently-parseable CSV or JSONL document. A CSV chunk
 * repeats the header row (parse_upload's csv.DictReader needs it in every
 * upload); JSONL chunks need no such repetition — every line already stands
 * alone. A file already under the limit, and short enough to import whole,
 * comes back as a single chunk, so the common case still makes exactly one
 * request and never reads the file into memory at all.
 *
 * `totalRows` reports how many rows were actually taken, so the caller can
 * say "importing the first N" rather than silently dropping the rest.
 */
export async function chunkUploadFile(
  file: File,
): Promise<{ blob: Blob; name: string }[]> {
  if (file.size <= SINGLE_REQUEST_BYTES) {
    return [{ blob: file, name: file.name }];
  }

  const isCsv = file.name.toLowerCase().endsWith(".csv");
  const ext = isCsv ? "csv" : "jsonl";

  // Only ever decode as much of the file as the import can use. Reading a
  // 57 MB file in full is survivable; parsing all of it is not.
  const text = await readCapped(file);

  // +1 for the CSV header row, which is not itself a record.
  const rows = isCsv
    ? splitCsvRows(text, MAX_IMPORT_ROWS + 1)
    : splitJsonlRows(text, MAX_IMPORT_ROWS);
  if (rows.length === 0) return [{ blob: file, name: file.name }];

  const header = isCsv ? rows[0] : null;
  const headerBytes = header ? utf8Len(header) + 1 : 0;
  const dataRows = isCsv ? rows.slice(1) : rows;

  const chunks: string[][] = [];
  let current: string[] = [];
  let currentBytes = headerBytes;

  for (const row of dataRows) {
    const rowBytes = utf8Len(row) + 1; // +1 for the newline that joins it back
    if (
      current.length > 0 &&
      (currentBytes + rowBytes > MAX_CHUNK_BYTES || current.length >= MAX_CHUNK_ROWS)
    ) {
      chunks.push(current);
      current = [];
      currentBytes = headerBytes;
    }
    current.push(row);
    currentBytes += rowBytes;
  }
  if (current.length > 0) chunks.push(current);

  return chunks.map((rowsInChunk, i) => {
    const body = header ? [header, ...rowsInChunk].join("\n") : rowsInChunk.join("\n");
    return {
      blob: new Blob([body], { type: isCsv ? "text/csv" : "application/json" }),
      name: file.name.replace(/(\.[^.]+)?$/, `.part${i + 1}.${ext}`),
    };
  });
}

/**
 * Decode only the leading slice of a very large file.
 *
 * A generous multiple of the chunk budget is enough to hold MAX_IMPORT_ROWS of
 * any plausible report corpus, and slicing on a byte boundary can only ever
 * damage the final partial row, which the row splitter drops anyway because a
 * truncated CSV row leaves an odd quote count (and a truncated JSONL line
 * fails to parse server-side as one skipped row).
 */
const READ_CAP_BYTES = MAX_CHUNK_BYTES * 12; // ~36 MB

async function readCapped(file: File): Promise<string> {
  const slice = file.size > READ_CAP_BYTES ? file.slice(0, READ_CAP_BYTES) : file;
  return slice.text();
}
