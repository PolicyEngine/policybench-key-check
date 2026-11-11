# Second input maps, written blind to the first

Two Claude Opus 5.5 agents each wrote an input map from the board's 100 households to one engine
(Tax-Calculator 6.9.0 in `taxcalc/`, NBER's TAXSIM test build in `taxsim/`) without seeing
`keycheck/`, each other's work, PolicyEngine's code or any answers. Their sources were the
engine's own documentation and code, the households as the board states them, a glossary of the
stated inputs from PolicyEngine-US's variable metadata, the board's definitions of the four
outputs, the shared state and local tax file, and law they fetched themselves. The session that
ran the comparison checked each agent's transcript for reads outside those sources and found
none.

Each folder holds the map as its author left it (`map.py`, `inputs_2026.csv`, `answers_2026.csv`,
`notes.csv`, `README.md`, `PROGRESS.md`, `probes/`), with local paths replaced by `INPUT/` (the
input folder), `SECOND_MAP/` and `REPO/`, plus `compare.py`, which a further Opus 5.5 agent wrote
to diff the two maps. `sources/` keeps the text copies of the law each author saved; the HTML and
PDF originals stay out of the repo (each `PROGRESS.md` lists the URLs).

`docs/second-map-taxcalc.md` and `docs/second-map-taxsim.md` report where the maps differ and
rule on each difference; `results/second_map/` holds the input and answer diffs.

One caveat on blindness: the harness gives every agent the same standing instructions and a
short index of notes from earlier, unrelated work. That index holds one-line notes on some of
PolicyBench's conventions and none on these maps; the Tax-Calculator author disclosed the one it
noticed (`taxcalc/PROGRESS.md`).
