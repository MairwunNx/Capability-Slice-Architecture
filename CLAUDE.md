# Capability Slice Architecture: notes for AI agents

🍰 Capability Slice Architecture (CSA) is an architecture for screens with declarative UI. A screen is a set of small capabilities, each owning one slice of state. This repository holds the specification: principles, vocabulary, rules, and the guarantees every implementation owes. There is no library code here. README.md is the shop window, README.RU.md its Russian copy. The principles live in the GitHub wiki (https://github.com/MairwunNx/Capability-Slice-Architecture/wiki).

## CSA and Capsa

Capsa (https://github.com/MairwunNx/Capsa) implements CSA on Kotlin Multiplatform for Android, iOS, and the JVM. Capsa follows every rule of CSA and holds more: the API, the hosts, the test harness, the tools. When the two disagree, CSA wins and Capsa gets fixed. Facts about Capsa’s API belong in Capsa, and this repository links to them.

CSA draws on Feature-Action Architecture (https://github.com/MairwunNx/Feature-Action-Architecture), which slices a backend by domain. CSA brings the same instinct to client apps with declarative UI.

## Vocabulary

| Term | Meaning |
|---|---|
| **Intent** | The user did something. Only the UI sends it. |
| **Signal** | The world did something: a work finished, another screen returned a result, the lifecycle moved. |
| **Fact** | An intent or a signal, the only thing that enters the runtime. |
| **Capability** | A pure function `decide(slice, fact) -> Decision` for one user scenario. |
| **Slice** | The state of one capability, the memory of the screen. |
| **Work** | A description of async work with a key and a cancellation policy. The runtime runs it. |
| **Effect** | A request to the outside world as data: navigate, show a snackbar, share. |
| **Slot** | Renders exactly one slice and sends intents. |
| **Host** | Assembles slices, intents, and effects. It holds no product logic. |

## Five rules

1. **Slice by scenario**, never by layout block.
2. **The host assembles, it doesn’t think**: no product conditions in the UI entry point.
3. **The runtime is the only bus**: a capability never imports or calls another one.
4. **Effects are the only impurity**: router and snackbars live at the edge, never in the logic.
5. **Keep the decider small**: about 150 lines or 12 facts. Past that, split the capability.

## How to write here

- **Platform-neutral.** The spec describes behaviour any implementation can give, on any UI toolkit. Examples are Kotlin or pseudocode, and they never depend on Capsa internals.
- **Examples** use domains anyone knows: a counter, a search, a like, a timer, a form. They name no employer, no internal project, no ticket numbers, no local paths.
- **Languages.** The repository, the wiki, and commit messages are in English. The README comes in two languages: README.md and README.RU.md, kept in sync.
- **Typography.** English uses curly quotes “ ” and ’, and an en dash with spaces ( – ), never an em dash. Russian uses «ёлочки», nested „лапки“, and an em dash with spaces ( — ). No semicolons between clauses in either language. Active voice: name who acts, the runtime, the host, the capability.
- **Style.** Markdown, YAML, and JSON use 2 spaces, Python and Kotlin 4. Lines stay within 186 columns, Markdown prose may run longer. `.editorconfig` holds the rest.
- **Pictures.** Diagrams are SVG in a light and a dark variant (`docs/images/*-light.svg`, `*-dark.svg`), shown through `<picture>` with `prefers-color-scheme`. `tools/diagrams.py` draws them.
- **Commits** follow `type(scope): short summary`: English, lower case, up to 72 characters. Types are `feat`, `fix`, `docs`, `test`, `build`, `ci`, `chore`, `refactor`. The body is one or two short lines or nothing, without trailers. One logical change per commit.

## Talking to the owner

- Reply in Russian and address the owner as «вы». Quotes «ёлочки», nested „лапки“, an em dash with spaces « — ».
- Before publishing anywhere, ask the owner.
