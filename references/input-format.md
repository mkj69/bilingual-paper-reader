# Reader input contract

The builder accepts UTF-8 JSON with `schema_version: 1`. Python 3.10 or newer is required. Run it from any directory. Asset paths resolve relative to the input JSON, not the current working directory. Output is one offline HTML file.

## Top level

| Field | Meaning |
| --- | --- |
| `title_en`, `title_zh` | Plain-text document titles |
| `source` | Object with `coverage` and optional `authors`, `identifier`, `version`, `url` |
| `annotation_limit` | Optional integer from 0 to 100; defaults to 12 unique annotations per English block |
| `glossary` | Optional list of vocabulary objects |
| `sections` | Nonempty list of sections |

`source.coverage` must state the actual translated range, missing material and whether content is an original demonstration. It is not an automatically verified completeness claim. Keep a separate source inventory for substantive papers. `source.url` must be an absolute HTTP(S) URL if present.

Each section has `id`, `title_en`, `title_zh`, `blocks`. All section and block IDs must be unique, start with a letter and contain only letters, digits, underscores or hyphens. The renderer prefixes them to avoid UI ID collisions.

## Reading blocks

All blocks have an `id` and optional `kind` (defaults to `pair`).

- `pair`: required `en`, `zh`; optional `source_locator`, `glossary_ids`.
- `note`: same fields as `pair`, but visibly identified as a translator note. Use only for additions, not source prose.
- `equation`: required `mathml` with a `<math>...</math>` root; optional `number`. Shared by both language modes. Use native MathML, not raw LaTeX.
- `figure`: required `file`, `alt`, `en`, `zh`; optional `source_locator`, `glossary_ids`. `en` and `zh` are captions. `file` points to a local PNG, JPEG, GIF or WebP inside the JSON directory, including its subdirectories. SVG and remote URLs are not accepted. Retain source figure credit in the caption or locator.
- `table`: required `headers`, `rows`, `en`, `zh`; optional `source_locator`, `glossary_ids`. Headers are `[English, Chinese]` pairs. Rows are arrays of plain cell values with equal length. Captions are bilingual. Values shared across modes are appropriate for numerical tables. For prose-heavy or structurally complex tables, adapt the renderer without discarding information.

For algorithms, use `pair` blocks with `<pre><code>...</code></pre>`, preserving indentation and numbering. For reference entries, use `pair` blocks, retaining the same bibliographic metadata. Neither has a separate block kind.

## Rich text

`en`, `zh` and `mathml` accept a strict HTML/MathML subset. Escape literal `<`, `>` and `&` as entities when they are not markup. The renderer validates nesting and rejects unsupported tags or attributes rather than silently deleting source content.

Text tags: `p br em strong b i sup sub span a cite code pre ul ol li blockquote`.

Math tags: `math mrow mi mn mo mtext mspace mfrac msqrt mroot msup msub msubsup mover munder munderover mfenced mtable mtr mtd mstyle mpadded mphantom menclose semantics`.

Math attributes: `display mathvariant stretchy fence separator accent accentunder columnalign rowalign columnspacing rowspacing linethickness lspace rspace width height depth notation open close separators`. `math` also accepts its standard MathML `xmlns`. Remove nonvisual `annotation` and `annotation-xml` from source MathML after verifying that the presentation branch is complete. Otherwise, convert or repair it first.

Links accept only `href` with an absolute HTTP(S) URL. No scripts, inline styles, event handlers, imported IDs, external images or frames are allowed. Raster images enter through `figure`, not rich text. The builder does not fetch URLs.

## Glossary

```json
{
  "id": "estimate-noun",
  "term": "estimate",
  "forms": ["estimates"],
  "meaning": "估计值",
  "detail": "这里是名词，指根据样本计算出的近似数值。"
}
```

All fields except `forms` are required. `forms` contains explicit aliases; the headword is always included. Matching is case-insensitive, longest first, with word boundaries. Each term is annotated once per block, up to the configured limit. Matching stays within a text node: a phrase broken by formatting should be normalized in the input without changing visible wording, or annotated through a shorter appropriate entry.

By default all glossary entries apply to a block. Use `glossary_ids: ["estimate-noun"]` to choose contextual meanings, or `[]` to disable annotations for that block. If active entries assign the same alias to different IDs, the build fails. Scope all affected blocks when using ambiguous aliases. The glossary dialog lists all entries, including contextual variants.

Glossary text is plain text. It is escaped in embedded JSON and inserted with `textContent`. Annotations skip mathematics, citations, links and code; text after those elements is still eligible.

See `examples/demo.json` for a complete original example containing every block kind.
