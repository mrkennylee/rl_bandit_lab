// Pre-seed gate: render every LaTeX string with KaTeX (throwOnError) so a broken
// formula fails the build at the YAML link, not in the student's browser.
// Reads JSON [{id, latex}, ...] on stdin; writes {errors:[{id,error}]} to stdout;
// exit 0 if all render, 1 if any fail, 2 on bad input.
import katex from "katex";

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  let items;
  try {
    items = JSON.parse(input);
  } catch (e) {
    process.stderr.write("invalid JSON input: " + e.message + "\n");
    process.exit(2);
  }
  const errors = [];
  for (const it of items) {
    try {
      katex.renderToString(it.latex, { throwOnError: true, displayMode: true });
    } catch (e) {
      errors.push({ id: it.id, error: String(e.message || e) });
    }
  }
  process.stdout.write(JSON.stringify({ errors }));
  process.exit(errors.length ? 1 : 0);
});
