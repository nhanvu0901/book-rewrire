# pov-retell: trích xuất sách và kết nối Neo4j

AI onboarding and operating instructions: [AI-work/README.md](AI-work/README.md).
Current project knowledge: [AI-work/PROJECT_CONTEXT.md](AI-work/PROJECT_CONTEXT.md).

Đây là bản **tối giản, dễ học** của dự án POV Story Retelling. Trạng thái hiện tại:

1. **Phase A, trích xuất**: đọc một cuốn sách (HTML, EPUB hoặc TXT), tìm cấu trúc chương, cắt thành
   **units** và **paragraphs** có ID cố định, rồi ghi ra **file thường** (JSON + text).
2. **Character Extraction**: summarize chapters, then use a general LLM to extract and update
   complete character profiles chapter by chapter. Each extraction receives the original chapter,
   the `WHO IS WHO` after chapter N-1 plus chapter summaries 1..N-1, and accumulated profiles. The
   application assigns IDs, applies explicit merges, and saves selected Character properties to Neo4j
   after completion.
   Xem [`docs/INGEST_BASE.md`](docs/INGEST_BASE.md) và [`doc_ai/NEXT_STEPS.md`](doc_ai/NEXT_STEPS.md).

LangGraph điều phối vòng lặp chương, không dùng checkpoint.
**Không có**: Postgres, SQLAlchemy, Alembic, phân tích beat/tri thức,
retell, FastAPI/UI, eval, Phoenix/OTel, cache, tính chi phí. Bản đầy đủ (khoảng 2000 test, nhiều
lớp) vẫn nằm ở branch `integration`; xem `docs/NEXT_STEPS.md`.

## 1. Phase A làm gì, từng bước

```text
file / URL ──A1──▶ Book ──A2a──▶ canonical text + candidates ──A2b──▶ structure map
                                                                          │
   book.json  ◀──A3── paragraphs ◀────────────── units (đã validate) ◀──A2c
```

| Bước | Ai làm | Việc | File |
|---|---|---|---|
| **A1** | code | Đọc file hoặc tải URL, **nhận dạng định dạng từ nội dung** (không tin đuôi file), tính **sha256**, đọc title/author | `load.py` |
| **A2a** | code | Tạo **canonical text** (văn bản sạch, mọi vị trí về sau đều trỏ vào nó) và gom **candidates**: chỗ *có thể* bắt đầu một unit (heading, link mục lục, anchor, dòng giống tiêu đề, spine/nav của EPUB) | `html_text.py`, `candidates.py` |
| **A2b** | LLM | Dựng **structure map**: mỗi candidate là `front`, `toc`, `license`, `body_unit`, `part_heading` hay `back`. LLM chỉ trả **ID + role + title**, không bao giờ trả vị trí | `llm_map.py`, `llm.py` |
| **A2c** | code | **Cắt** canonical text theo vị trí của các candidate được chọn, rồi **validate**: liền nhau, đúng thứ tự, không rỗng, phủ trọn thân truyện, mỗi part có chapter. Front matter, back matter và license **nằm ngoài** mọi unit | `cut.py` |
| **A3** | code | Chia mỗi unit thành **paragraphs** có ID cố định (`u04_p041` = unit 4, đoạn 41) và gắn **flag** cho đoạn bất thường (`too_short`, `too_long`, `suspicious_header`, `license_leak`) | `paragraphs.py` |

Nguyên tắc xuyên suốt: **code giữ sự thật, LLM chỉ đề xuất**. Một structure map cắt ra units không
hợp lệ (hở, chồng, rỗng, part không có chapter...) bị **từ chối kèm lỗi rõ ràng**, không bị sửa
ngầm: cắt sai chương thì mọi bước sau đều lệch theo. Điều đáng ngờ nhưng chưa chắc sai (một unit
không có paragraph nào, một chapter đứng sau part mà không khai báo part cha) thành `warnings` trong
`book.json`.

## 2. Bắt đầu đọc từ đâu

Mã được chia theo trách nhiệm, nhưng vẫn là cùng một chương trình dòng lệnh:

```text
src/pov_retell/
├── cli.py                  lệnh `pov` mà bạn gõ
├── config.py               cấu hình và đường dẫn dữ liệu
├── book/                   đọc, tách và lưu sách thành file
├── ingest/                 LangGraph, xử lý chương và models nhân vật
└── infrastructure/         kết nối OpenRouter và Neo4j
```

Đọc theo thứ tự này (mỗi file có docstring giải thích *vì sao*, không chỉ *cái gì*):

| # | File | Nội dung |
|---|---|---|
| 1 | `src/pov_retell/book/models.py` | Mọi data shape của phase A (Book, Candidate, MapItem, Unit, Paragraph, ExtractedBook) |
| 2 | `src/pov_retell/book/pipeline.py` | Hàm `extract_book()`: A1 → A3 trong 40 dòng, đọc cái này để thấy bức tranh tổng |
| 3 | `src/pov_retell/book/load.py` | A1 |
| 4 | `src/pov_retell/book/candidates.py` (+ `html_text.py`) | A2a, phần dài nhất vì mỗi định dạng một kiểu |
| 5 | `src/pov_retell/infrastructure/llm.py`, `book/llm_map.py` | A2b: client OpenRouter và prompt |
| 6 | `src/pov_retell/book/cut.py` | A2c: cắt và validate |
| 7 | `src/pov_retell/book/paragraphs.py` | A3 |
| 9 | `src/pov_retell/book/output.py`, `cli.py` | Ghi file, lệnh `pov` |
| 10 | `src/pov_retell/ingest/pipeline.py` | Hàm `ingest_book`, gọi các graph theo bước |
| 10a | `src/pov_retell/ingest/graph/extract_character/graph.py` | Character, relationship, location and scene-map extraction nodes, edges and recursion limit helper |
| 10b | `src/pov_retell/ingest/graph/extract_character/model.py` | Character, relationship, location, scene-map, response and graph state models |
| 11 | `src/pov_retell/ingest/graph/extract_character/logic.py`, `identity.py`, `relationship.py`, `location.py`, `scene_map.py` | Full-profile, relationship, location and scene-map LLM calls, merges, history and JSON persistence |
| 11a | `src/pov_retell/ingest/model.py`, `source.py` | Shared chapter input, pipeline result and source validation |
| 11b | `src/pov_retell/ingest/graph/summarize_chapter/graph.py` | Sequential chapter summary nodes, edges and recursion limit helper |
| 11c | `src/pov_retell/ingest/graph/summarize_chapter/model.py`, `logic.py` | Summary models, LLM calls and JSON persistence |
| 12 | `src/pov_retell/infrastructure/neo4j_store.py` | Kết nối và ghi Character vào Neo4j |
| 13 | `src/pov_retell/ingest/graph/summarize_chapter/prompt/` (`summarize_chapter.py`, `update_who_is_who.py`, `update_where_is_where.py`, `summarize_book.py`), `src/pov_retell/ingest/graph/extract_character/prompt/` (`extract_character.py`, `extract_relationship.py`, `extract_location.py`, `extract_scene_map.py`) | Chapter summaries, WHO IS WHO, WHERE IS WHERE, book core memory, character, relationship, location and scene-map extraction prompts |
| - | `src/pov_retell/book/text.py`, `config.py` | Helper nhỏ; settings (gồm `NEO4J_*`) |
| - | `docker/compose.yml`, `Makefile` | Neo4j 5 community (project `book-clone-dev`), `neo4j-up/down/shell`, `ingest` |
| - | `docs/INGEST_BASE.md` | Cách chạy ingest, vị trí kết quả và giới hạn hiện tại |
| - | `tests/` | Mỗi bước có test riêng, đọc test để thấy ví dụ vào/ra |

## 3. Cài đặt và chạy

Cần Python 3.12 và [uv](https://docs.astral.sh/uv/).

```bash
make install                      # uv sync --extra dev

uv run pov extract <file|url>                  # LLM map (cần OPENROUTER_API_KEY)
uv run pov extract <file> --id my-book         # đặt book id (mặc định: slug của title)
uv run pov extract <file> --out ./out          # thư mục ra (mặc định: DATA_DIR/extracted)

uv run pov show <book_id>                      # bảng units, flag, cảnh báo
uv run pov show <book_id> u04                  # in các paragraph của unit u04
```

Ví dụ với 3 cuốn đặt trong `book/books/` của project:

```bash
uv run pov extract book/books/lww.html
uv run pov extract book/books/treasure_island.html
uv run pov extract book/books/treasure_island.epub --id treasure-island-epub
```

> **Một cuốn, nhiều định dạng:** html, epub và txt của cùng một cuốn đều có title
> `Treasure Island` nên cùng book id. Trích xuất file thứ hai sẽ bị **từ chối** (khác `sha256`) để
> không ghi đè lên file đầu. Dùng `--id` để đặt tên riêng. Chạy lại **đúng file cũ** thì được ghi
> đè (kết quả như nhau). ID của paragraph chỉ ổn định **trong một file**: html, epub, txt của cùng
> một cuốn có số đoạn hơi khác nhau, đừng trộn.

**Cấu hình** (`pydantic-settings` đọc `.env` ở gốc repo; biến môi trường có thể ghi đè).
Sao chép `.env.example` thành `.env` rồi điền đủ giá trị. `.env` không được commit.

| Biến | Giá trị trong `.env` hiện tại | Dùng cho |
|---|---|---|
| `BOOK_CLONE_DATA_DIR` | `<project>/book` | sách nguồn ở `book/books/`, output ở `book/extracted/` |
| `OPENROUTER_API_KEY` | cần điền | `pov extract`, `pov ingest` |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | |
| `OPENROUTER_MODEL` | set in `.env` | Book structure mapping (`pov extract`) |
| `OPENROUTER_SUMMARIZE_CHAPTER_MODEL` | set in `.env` | Chapter and cumulative book summaries |
| `OPENROUTER_SUMMARIZE_CHAPTER_REASONING` | `none`, `enabled`, `low`, `medium`, or `high` in `.env` | Summary reasoning; `none` omits the parameter and uses the provider default |
| `OPENROUTER_EXTRACT_CHARACTER_MODEL` | set in `.env` | Full character profiles, aliases and merges (`pov ingest`) |
| `OPENROUTER_MAX_TOKENS` | set in `.env` | Output-token limit for `OPENROUTER_MODEL` (`pov extract`) and diagnostics, including reasoning tokens |
| `OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS` | set in `.env` | Output-token limit for the summary model |
| `OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS` | set in `.env` | Output-token limit for the character model |
| `OPENROUTER_EXTRACT_CHARACTER_PROVIDER` | set in `.env` (e.g. `open-inference/fp4` or empty) | Comma-separated provider tags for the extract client; empty uses default routing |
| `OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS` | `true` or `false` in `.env` | Whether OpenRouter may fall back when `OPENROUTER_EXTRACT_CHARACTER_PROVIDER` is set |
| `OPENROUTER_EXTRACT_CHARACTER_REASONING` | `none`, `enabled`, `low`, `medium`, or `high` in `.env` | Reasoning configuration sent by the extract client |
| `OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS` | `true` or `false` in `.env` | `true` sends strict `json_schema` derived from the Pydantic response model; `false` sends `json_object` |
| `NEO4J_PASSWORD` | đặt trong `.env`, **bắt buộc** cho Neo4j | `make neo4j-up`, `pov ingest`; không bao giờ bị in ra |
| `NEO4J_USER` | `neo4j` | |
| `NEO4J_HTTP_PORT` / `NEO4J_BOLT_PORT` | `7475` / `7688` | khác `7474`/`7687` của stack `book-clone` |

## 4. Định dạng output

```text
<BOOK_CLONE_DATA_DIR>/extracted/<book_id>/
├── book.json            metadata + candidates + map + units + paragraphs (có schema_version)
├── canonical.txt        văn bản sạch; mọi char_start/char_end trỏ vào file này
└── units/NN_title.txt   một file đọc được cho mỗi chapter (NN = thứ tự unit)
```

`NN` là `order` của unit nên **khớp với ID**: `units/02_...txt` là unit `u02`. Part chỉ có tiêu
đề, không có paragraph, nên không có file riêng (vì thế danh sách file có thể bắt đầu từ `02`).

Ví dụ thật, chạy trên truyện tự bịa dùng trong test (`The Lantern Keeper`, không phải sách thật):

```text
$ uv run pov extract lantern.txt
Book:       the-lantern-keeper | The Lantern Keeper by Jane Doe
File:       txt, sha256 a40642bd86841b9d...
Map:        llm, 11 candidates
Units:      5 (2 part, 3 chapter)
Paragraphs: 7 (0 flagged)

$ uv run pov show the-lantern-keeper
ID    KIND     PARENT PARAS  WORDS  TITLE
u01   part     -          0      0  PART ONE: THE CLIFF
u02   chapter  u01        3     53  CHAPTER I: The Lamp
u03   chapter  u01        2     32  CHAPTER II: The Stranger
u04   part     -          0      0  PART TWO: THE STORM
u05   chapter  u04        2     38  CHAPTER III: The Light Goes Out
```

`units/02_chapter-i-the-lamp.txt`:

```text
CHAPTER I: The Lamp
===================

[u02_p001] One evening the keeper climbed the long stair to light the great lamp, as his father ...

[u02_p002] "The sea is quiet tonight," said the boy who followed him up the steps.
```

`book.json` (rút gọn; các mảng `candidates` và `map_items` bị lược):

```json
{
  "schema_version": 1,
  "book": {"id": "the-lantern-keeper", "title": "The Lantern Keeper", "author": "Jane Doe",
           "format": "txt", "sha256": "a40642bd...", "source": "/path/to/lantern.txt"},
  "map_method": "llm",
  "candidates": [{"cand_id": "cand_005", "kind": "caps_line", "text": "THE CLIFF",
                  "char_pos": 276, "preview": "THE CLIFF CHAPTER I. The Lamp One evening ..."}],
  "map_items":  [{"cand_id": "cand_005", "role": "front", "unit_kind": "front",
                  "title": "THE CLIFF", "parent_cand_id": null}],
  "units": [
    {"id": "u01", "order": 1, "kind": "part",    "title": "PART ONE: THE CLIFF",
     "parent_id": null, "char_start": 266, "char_end": 287},
    {"id": "u02", "order": 2, "kind": "chapter", "title": "CHAPTER I: The Lamp",
     "parent_id": "u01", "char_start": 287, "char_end": 520}
  ],
  "paragraphs": [
    {"id": "u02_p001", "unit_id": "u02", "order": 1, "text": "One evening the keeper ...",
     "char_start": 308, "char_end": 445, "flags": []}
  ],
  "warnings": []
}
```

Tên bảng và cột bám theo mục 5.1 của thiết kế (`books`, `structure_candidates`, `structure_maps`,
`units`, `paragraphs`), nên bước ingest sau không phải đổi tên gì.

## 5. Kết quả cũ trên 3 cuốn sách

Số liệu dưới đây thuộc lần trích xuất cũ trước khi chuyển sang LLM. Chúng không phải kết quả
đã kiểm chứng của pipeline hiện tại:

| File | Units | Paragraphs | Flagged |
|---|---|---|---|
| `lww.html` | 17 chapter | 822 | 1 |
| `treasure_island.html` | 6 part + 34 chapter | 1382 | 5 |
| `treasure_island.epub` | 6 part + 34 chapter | 1452 | 74 |
| `treasure_island.txt` | 6 part + 34 chapter | 1375 | 1 |
| `pride_and_prejudice.html` | 61 chapter | 2120 | 10 |
| `pride_and_prejudice.epub` | 61 chapter | 2113 | 3 |
| `pride_and_prejudice.txt` | 61 chapter | 2310 | 4 |

**Treasure Island: 34 chapter, 6 part được biểu diễn thế nào?** Mỗi part là **một unit
`kind: "part"`** chỉ chứa dòng tiêu đề (không có paragraph); mỗi chapter là unit
`kind: "chapter"` có `parent_id` trỏ tới part của nó (quan hệ Part → Chapter, quyết định R1 trong
thiết kế). Vì vậy `units` có 40 phần tử, nhưng **34 chapter** là các unit có paragraph và là các đơn
vị của nút NEXT. Muốn chỉ lấy chapter: `[u for u in units if u["kind"] == "chapter"]`.

**Vài điều thật trong dữ liệu (flag để người xem quyết định, không phải lỗi của code):**

- `treasure_island.epub` có 74 flag `too_short`: bản EPUB này chèn **số trang** như `0033m` thành
  một đoạn riêng (69 cái), cộng 5 dòng ngắn thật. `pride_and_prejudice.html` có 7 flag `too_short`
  cùng kiểu: số trang `{6}`, `{27}`... Flag đã bắt đúng chúng; bước sau nên bỏ các đoạn đó.
- Các flag `too_short` còn lại là dòng ngắn thật: `Ten feet.`, ký hiệu `J. T.`, `The End`.
- `too_long` (3 cái trong mỗi bản Pride and Prejudice): ba lá thư dài (ví dụ thư của Darcy) nằm
  trong **một** đoạn. Đó là đoạn dài thật, không phải thiếu chỗ ngắt.
- `treasure_island.txt`: bản Gutenberg này in chương 17 là `XXVII` (lỗi gõ trong **file nguồn**).
  Số lượng vẫn đúng 34 vì code cắt theo vị trí tiêu đề, không theo con số.
- Số đoạn của cùng một cuốn khác nhau giữa các định dạng (1382 / 1452 / 1375 cho Treasure Island)
  vì mỗi định dạng ngắt dòng và chèn số trang theo kiểu riêng. Đó là lý do ID chỉ ổn định
  trong **một file** (xem ghi chú ở mục 3).

## 6. LLM map

`uv run pov extract <file>` gửi danh sách candidate (ID, kind, text, vài chữ đầu) cho
OpenRouter và nhận lại ID + role + title. Code vẫn là bên cắt và validate. `llm.py` chỉ ~90 dòng:

- model và `base_url` lấy từ config (`openai/gpt-4o-mini`, `https://openrouter.ai/api/v1`);
- `json_object` rồi validate bằng Pydantic; câu trả lời sai thì thử lại **tối đa 2 lần**, mỗi lần
  kèm đúng lỗi vừa gặp;
- câu trả lời bỏ sót, lặp hoặc bịa `cand_id` bị từ chối trước khi tới bước cắt.

Unit test dùng fake
(`tests/fakes.py`, `tests/test_llm.py`) nên không gọi API. Test riêng
`tests/test_openrouter_integration.py` gửi một request thật khi chạy `make test-openrouter`;
cần key OpenRouter trong `.env` và model đang chọn phải sẵn sàng phục vụ.

## 7. Kiểm tra chất lượng

```bash
make test         # test offline, không cần sách thật hoặc Neo4j
make lint         # ruff check + ruff format --check
make typecheck    # mypy --strict trên src và tests
make test-neo4j   # Opt-in: connectivity and temporary Character writes
make test-openrouter # OPT-IN: gửi một request thật tới OpenRouter (cần key trong .env; có tính phí)
```

Test chỉ dùng **truyện tự bịa** (`tests/samples.py`, vẽ ra HTML, EPUB và TXT) cùng vài đoạn ngắn
tự viết. **Không commit văn bản sách** (LWW còn bản quyền); sách thật chỉ nằm ngoài git.

## 8. Ingest nhân vật vào Neo4j

```bash
 # Đặt NEO4J_PASSWORD (>= 8 ký tự) trong .env trước khi chạy; không commit file này.
make neo4j-up                                  # Neo4j 5 community, chờ healthcheck xanh
uv run pov neo4j-status                        # chỉ kiểm tra kết nối
uv run pov ingest narnia-debug
make neo4j-shell                               # cypher-shell;  make neo4j-down để tắt
```

Khi chỉ thử LLM, bỏ qua Neo4j hoàn toàn (không kết nối, không ghi; JSON vẫn được lưu):

```bash
uv run pov ingest narnia-debug --no-neo4j
```

`ingest_book` validates the extracted chapter files and creates one run directory.
It runs the `summarize_chapter` graph first, then the `extract_character` graph.
Each graph keeps its own models and logic in its graph folder.

```text
load_chapters -> summarize_chapter graph -> extract_character graph -> save_neo4j

summarize_chapter: initialize -> summarize_chapter -> validate_summary -> save_summary -> summarize_book
                                    ^                                    |
                                    +----------- next chapter -----------+

extract_character: initialize -> extract_characters -> validate_characters -> extract_relationships -> validate_relationships -> extract_locations -> validate_locations -> extract_scenes -> validate_scenes -> save_json
                                      ^                                                                                                                                                                            |
                                      +-------------------------------------------------------------------------- next chapter ------------------------------------------------------------------------------------+
```

For each chapter, the summary graph makes three plain-text calls:
1. `summarize_chapter`: writes `chapter_summary` for the current chapter using the previous
   `WHO IS WHO` and `WHERE IS WHERE` lists, all preceding chapter summaries in order, and the
   original chapter text.
2. `update_who_is_who`: updates the complete `WHO IS WHO` character list (`name | aliases or - | identity card`)
   from the previous `WHO IS WHO` (empty for chapter 1) and the original chapter text, without
   chapter summaries or the call-1 output. Python validates that each line has three `|` fields
   and that no earlier character name was dropped, retrying up to two times on violations.
3. `update_where_is_where`: updates the complete `WHERE IS WHERE` place list (`name | aliases or - | place card`)
   from the previous `WHERE IS WHERE` (empty for chapter 1) and the original chapter text, without
   chapter summaries, `WHO IS WHO`, or the call-1 output. Python validates that each line has three
   `|` fields and that no earlier place name was dropped, retrying up to two times on violations.

After the last chapter, `summarize_book` runs once on all chapter summaries in order to write
`core_memory` and saves `summaries/book_memory.json` (`{"who_is_who", "where_is_where", "core_memory"}`).

Character extraction uses one general-LLM JSON call per chapter, excluding repair retries.
Its input contains the original current chapter, complete accumulated profiles, and Python-assembled
context through the **previous** chapter (the `WHO IS WHO` and `WHERE IS WHERE` after chapter N-1
plus chapter summaries 1..N-1; empty for u01). It never receives the current or later chapter
summaries. Summaries are fallible context; the original chapter remains the evidence.

The response contains only changes: new characters, and existing characters who appear in
or gain information from the chapter, with only the new aliases, attributes and explicit
identity merges. Omitted characters and null or empty fields keep their stored values. Python
assigns permanent IDs to `new_N` proposals, keeps the earliest surviving ID on merges, retains
absent records, and preserves known facts on empty updates. Names do not need to occur
verbatim in the current chapter, and equal names alone do not merge people.

Personality traits must be explicitly described in the source. New trait wording must also
occur in the original chapter; existing traits survive later chapters that do not repeat them.
This source check cannot establish ownership or truth by itself.

The unused ScaleDown experiment was removed on 2026-10-26; historical run data is preserved.
Model settings stay in `.env`:
`OPENROUTER_SUMMARIZE_CHAPTER_MODEL` and `OPENROUTER_EXTRACT_CHARACTER_MODEL` select the
active models. The user can replace either model without changing the graph.

For N chapters, ingestion uses 3N+1 summary calls and 4N extraction calls (`N` character calls, `N` relationship calls, `N` location calls, and `N` scene-map calls) before retries.
Only after all chapters finish does it write selected Character properties to Neo4j.
It does not yet write `RELATES_TO` edges, `Location` nodes, or `Scene` nodes to Neo4j.

Output under `book/ingest/<book_id>/<run_id>/`:

- `summaries/u01.summary.json`, etc.: per-chapter `chapter_id`, `chapter_summary`, `who_is_who`, and `where_is_where`.
- `summaries/book_memory.json`: final `who_is_who`, `where_is_where`, and `core_memory`.
- `chapters/u01.proposed.json`, etc.: original full-profile LLM proposals.
- `chapters/u01.characters.json`, etc.: cumulative accepted character snapshots.
- `chapters/u01.relationships.proposed.json`, etc.: original relationship LLM proposals.
- `chapters/u01.relationships.json`, etc.: cumulative accepted relationship snapshots.
- `chapters/u01.locations.proposed.json`, etc.: original location LLM proposals.
- `chapters/u01.locations.json`, etc.: cumulative accepted location snapshots.
- `chapters/u01.scenes.proposed.json`, etc.: original scene-map LLM proposals.
- `chapters/u01.scenes.json`, etc.: validated per-chapter scene segments with `segment_id` (`u01_s1`, ...).
- `identity_redirects.json`: retired IDs mapped to surviving IDs.
- `characters.json`: the latest accepted character list.
- `relationships.json`: the latest accepted relationship list.
- `locations.json`: the latest accepted location list.

Model names are printed before each graph is built. Each invocation creates a new run;
there is no checkpoint or resume. A failed run retains completed files and does not reach
the final Neo4j write. See [`AI-work/handoffs/HANDOFF_2026-10-22.md`](AI-work/handoffs/HANDOFF_2026-10-22.md)
for the historical experiments that led to restoring this workflow.

`docker/compose.yml` chỉ có Neo4j và đặt project name `book-clone-dev` (không phải `book-clone`), nên
container, network và **volume khác hẳn** stack `book-clone` đang chạy. Cổng host cũng khác để không
đụng nhau: stack kia dùng `7474`/`7687`, ở đây là Neo4j Browser **`7475`** và Bolt **`7688`** (đổi bằng
`NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, đã có trong `config.py`). APOC là tùy chọn, tắt mặc định.

## 9. Tiếp theo

Xem [`doc_ai/NEXT_STEPS.md`](doc_ai/NEXT_STEPS.md): thiết kế Character Extraction & Resolution,
JSON nhân vật tích lũy theo chương và các trường được lưu vào Neo4j.
