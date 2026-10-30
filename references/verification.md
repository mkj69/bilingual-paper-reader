# Verification checklist

## Source fidelity

- Record the exact source version and reading scope. Use the PDF to resolve two-column order, hyphenation, captions and formula placement.
- Map every in-scope source sentence to a translated unit. Check omissions, duplication, merged paragraphs and sentences spanning equations.
- Compare numbers, signs, indices, units, acronyms, citations, figure and table labels, and equation numbering against source.
- Check negation, modality, uncertainty, comparative claims and limitations. Distinguish author claims from translator explanations.
- Count source figures, tables, displayed equations and appendix sections. Compare actual assets and data, not only counts.
- Preserve author metadata and references. Declare incomplete extraction or unresolved glyphs before delivery.

## Vocabulary

- Check meanings in the exact passage, especially common words with technical senses.
- Test phrase overlap, inflections and terms immediately after citations or mathematics.
- Ensure annotations do not modify copied English or break mathematical expressions.
- Read at least one full translated unit in each section; for full-translation requests verify all units, not just samples.

## Interface

- Open the generated HTML in a modern browser at desktop and 390-pixel mobile widths.
- Confirm no horizontal page overflow. Wide tables and equations should scroll within their containers.
- Check every image loaded, formulas are legible, and no browser errors occurred.
- Click an annotated term, close it with X and Escape, and use keyboard focus.
- Open the glossary, search both English and Chinese, close with X and Escape, and test backdrop dismissal.
- Test all three reading modes. Confirm shared figures, equations and numeric data remain visible.
- Toggle annotations off and verify vocabulary buttons leave the tab order.
- Check the browser makes no network requests on load. Explicit source links may navigate when clicked.
- Inspect the print view if printing is part of the request. Do not promise PDF pagination without rendering it.

## Updates and delivery

Preserve an existing artifact before changing it. Compare figures, table values and displayed equations with the previous output. Report actual coverage, validation results and any remaining gap. Keep private input, complete paper text and local conversation archives out of a public tools repository. Reader publication needs its own authorization and appropriate source rights.

The included unit tests cover renderer behavior and input rejection. They cannot judge translation quality. `tests/browser_check.cjs` is an optional Playwright smoke test for the original demo; install Playwright separately and set `BROWSER_PATH` if using a system browser.
