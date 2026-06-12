// The model sometimes wraps emphasis in markdown (**bold**, *italic*); the panels
// render plain text, so strip the markers rather than show them literally. The
// final pass removes any orphan marker left when an emphasis span straddles a
// citation marker, so a stray asterisk never reaches the screen.
export function stripEmphasis(s: string): string {
  return s
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "$1")
    .replace(/\*+/g, "");
}

// The lesson model occasionally echoes the prompt's "state ONE principle"
// instruction as a literal "ONE principle that applies ... is:" preamble. Trim
// that scaffolding so the principle reads as a statement, not a prompt echo.
export function tidyLesson(s: string): string {
  const stripped = stripEmphasis(s).trim();
  return stripped
    .replace(/^(the\s+)?one\s+principle\s+that\s+applies\s+to\s+the\s+proposed\s+action\b[^:]*:\s*/i, "")
    .replace(/^(the\s+)?principle\s+(that\s+applies|here)\b[^:]*:\s*/i, "")
    .replace(/\s*this principle is supported by the following ref_ids?:?\s*[\d,\s]*\.?\s*$/i, "")
    .trim();
}
