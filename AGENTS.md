## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).


## Custome Branch Rules

This is a personal fork. Follow these rules strictly:
- Never create pull requests to the upstream (harry0703/MoneyPrinterTurbo) unless explicitly asked.
- main must always stay identical to upstream — no custom commits.
- Upstream URL: https://github.com/harry0703/MoneyPrinterTurbo (remote name: upstream)
- Fork URL: https://github.com/BinhTHB/MoneyPrinterTurbo (remote name: origin)

## Language

Always respond in Vietnamese (tiếng Việt) unless the user explicitly requests another language.


## Update rule
Lấy thay đổi từ upstream (repo gốc):
git fetch upstream

Chuyển về nhánh chính (main/master):
git checkout main

Merge thay đổi từ upstream/main vào local main:
git merge upstream/main

Push lên fork của bạn (origin):
git push origin main