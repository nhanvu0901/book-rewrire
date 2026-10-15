# pov-retell: nạp sách (phase A) và base ingest vào Neo4j

Đây là bản **tối giản, dễ học** của dự án POV Story Retelling. Nó có hai phần:

1. **Phase A, trích xuất**: đọc một cuốn sách (HTML, EPUB hoặc TXT), tìm cấu trúc chương, cắt thành
   **units** và **paragraphs** có ID cố định, rồi ghi ra **file thường** (JSON + text).
2. **Base ingest** (branch `clean/ingest-base`): một **LangGraph** nhỏ, không dùng LLM, đọc các file đó
   và ghi vào **Neo4j**. Bạn viết các bước phân tích (B1, B2, ...) lên trên base này. Xem
   [`docs/INGEST_BASE.md`](docs/INGEST_BASE.md).

Chỉ có LangGraph và Neo4j. **Không có**: Postgres, SQLAlchemy, Alembic, phân tích nhân vật (B*),
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
| **A2b** | code (mặc định) hoặc LLM (tùy chọn) | Dựng **structure map**: mỗi candidate là `front`, `toc`, `license`, `body_unit`, `part_heading` hay `back`. LLM chỉ trả **ID + role + title**, không bao giờ trả vị trí | `heuristic_map.py`, `llm_map.py`, `llm.py` |
| **A2c** | code | **Cắt** canonical text theo vị trí của các candidate được chọn, rồi **validate**: liền nhau, đúng thứ tự, không rỗng, phủ trọn thân truyện, mỗi part có chapter. Front matter, back matter và license **nằm ngoài** mọi unit | `cut.py` |
| **A3** | code | Chia mỗi unit thành **paragraphs** có ID cố định (`u04_p041` = unit 4, đoạn 41) và gắn **flag** cho đoạn bất thường (`too_short`, `too_long`, `suspicious_header`, `license_leak`) | `paragraphs.py` |

Nguyên tắc xuyên suốt: **code giữ sự thật, LLM chỉ đề xuất**. Một structure map cắt ra units không
hợp lệ (hở, chồng, rỗng, part không có chapter...) bị **từ chối kèm lỗi rõ ràng**, không bị sửa
ngầm: cắt sai chương thì mọi bước sau đều lệch theo. Điều đáng ngờ nhưng chưa chắc sai (một unit
không có paragraph nào, một chapter đứng sau part mà không khai báo part cha) thành `warnings` trong
`book.json`.

## 2. Bắt đầu đọc từ đâu

Đọc theo thứ tự này (mỗi file có docstring giải thích *vì sao*, không chỉ *cái gì*):

| # | File | Nội dung |
|---|---|---|
| 1 | `src/pov_retell/models.py` | Mọi data shape của phase A (Book, Candidate, MapItem, Unit, Paragraph, ExtractedBook) |
| 2 | `src/pov_retell/pipeline.py` | Hàm `extract_book()`: A1 → A3 trong 40 dòng, đọc cái này để thấy bức tranh tổng |
| 3 | `src/pov_retell/load.py` | A1 |
| 4 | `src/pov_retell/candidates.py` (+ `html_text.py`) | A2a, phần dài nhất vì mỗi định dạng một kiểu |
| 5 | `src/pov_retell/heuristic_map.py` | A2b mặc định (luật chung, **không có luật riêng cho cuốn nào**) |
| 6 | `src/pov_retell/cut.py` | A2c: cắt và validate |
| 7 | `src/pov_retell/paragraphs.py` | A3 |
| 8 | `src/pov_retell/llm.py`, `llm_map.py` | A2b tùy chọn: client DeepSeek tối thiểu và prompt |
| 9 | `src/pov_retell/output.py`, `cli.py` | Ghi file, lệnh `pov` |
| 10 | `src/pov_retell/ingest_graph.py` | **Ingest**: `IngestState`, các node LangGraph, edge, stream sự kiện |
| 11 | `src/pov_retell/neo4j_store.py` | **Ingest**: driver, healthcheck, schema, ghi MERGE/UNWIND |
| - | `src/pov_retell/text.py`, `config.py` | Helper nhỏ; settings (gồm `NEO4J_*`) |
| - | `docker/compose.yml`, `Makefile` | Neo4j 5 community (project `book-clone-dev`), `neo4j-up/down/shell`, `ingest` |
| - | `docs/INGEST_BASE.md` | LangGraph + mô hình Neo4j + 10 câu Cypher + cách thêm node mới |
| - | `tests/` | Mỗi bước có test riêng, đọc test để thấy ví dụ vào/ra |

## 3. Cài đặt và chạy

Cần Python 3.12 và [uv](https://docs.astral.sh/uv/).

```bash
make install                      # uv sync --extra dev

uv run pov extract <file|url>                  # heuristic map (mặc định, miễn phí, offline)
uv run pov extract <file|url> --map llm        # LLM map (cần DEEPSEEK_API_KEY)
uv run pov extract <file> --id my-book         # đặt book id (mặc định: slug của title)
uv run pov extract <file> --out ./out          # thư mục ra (mặc định: DATA_DIR/extracted)

uv run pov show <book_id>                      # bảng units, flag, cảnh báo
uv run pov show <book_id> u04                  # in các paragraph của unit u04
```

Ví dụ với 3 cuốn đặt trong `~/.local/share/book-clone/books/`:

```bash
uv run pov extract ~/.local/share/book-clone/books/lww.html
uv run pov extract ~/.local/share/book-clone/books/treasure_island.html
uv run pov extract ~/.local/share/book-clone/books/treasure_island.epub --id treasure-island-epub
```

> **Một cuốn, nhiều định dạng:** html, epub và txt của cùng một cuốn đều có title
> `Treasure Island` nên cùng book id. Trích xuất file thứ hai sẽ bị **từ chối** (khác `sha256`) để
> không ghi đè lên file đầu. Dùng `--id` để đặt tên riêng. Chạy lại **đúng file cũ** thì được ghi
> đè (kết quả như nhau). ID của paragraph chỉ ổn định **trong một file**: html, epub, txt của cùng
> một cuốn có số đoạn hơi khác nhau, đừng trộn.

**Cấu hình** (`pydantic-settings`, đọc `~/.config/book-clone/secrets.env`, rồi `.env`, rồi biến môi
trường). Xem `.env.example` (chỉ có tên biến). Không bao giờ in hoặc commit secret.

| Biến | Mặc định | Dùng cho |
|---|---|---|
| `BOOK_CLONE_DATA_DIR` | `~/.local/share/book-clone` | sách nguồn ở `books/`, output ở `extracted/` |
| `DEEPSEEK_API_KEY` | (trống) | chỉ cho `--map llm` |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | |
| `NEO4J_PASSWORD` | (trống, **bắt buộc** cho Neo4j) | `make neo4j-up`, `pov ingest`; không bao giờ bị in ra |
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
Map:        heuristic, 11 candidates
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
  "map_method": "heuristic",
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

## 5. Kết quả thật trên 3 cuốn sách

Heuristic map, không LLM, cùng một code cho cả 7 file (số liệu do `uv run pov extract` in ra):

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

## 6. LLM map (tùy chọn)

`uv run pov extract <file> --map llm` gửi danh sách candidate (ID, kind, text, vài chữ đầu) cho
DeepSeek và nhận lại ID + role + title. Code vẫn là bên cắt và validate. `llm.py` chỉ ~90 dòng:

- model và `base_url` lấy từ config (`deepseek-v4-pro`, `https://api.deepseek.com`);
- **thinking luôn bị tắt** (client không có công tắc bật nó);
- `json_object` rồi validate bằng Pydantic; câu trả lời sai thì thử lại **tối đa 2 lần**, mỗi lần
  kèm đúng lỗi vừa gặp;
- câu trả lời bỏ sót, lặp hoặc bịa `cand_id` bị từ chối trước khi tới bước cắt.

Mặc định vẫn là heuristic và chạy được cho cả 3 cuốn. Test **không gọi API thật**: dùng fake
(`tests/fakes.py`, `tests/test_llm.py`). Số dư DeepSeek hiện đang bằng 0 nên `--map llm` chưa chạy
thật được; code chỉ được kiểm bằng fake.

## 7. Kiểm tra chất lượng

```bash
make test         # ~90 test, không cần mạng, không cần sách thật, không cần Neo4j
make lint         # ruff check + ruff format --check
make typecheck    # mypy --strict trên src và tests
make test-books   # OPT-IN: chạy 3 cuốn thật trong BOOK_CLONE_DATA_DIR/books và kiểm số đếm
make test-neo4j   # OPT-IN: ghi một sách tạm vào Neo4j thật (cần make neo4j-up), rồi xóa nó
```

Test chỉ dùng **truyện tự bịa** (`tests/samples.py`, vẽ ra HTML, EPUB và TXT) cùng vài đoạn ngắn
tự viết. **Không commit văn bản sách** (LWW còn bản quyền); sách thật chỉ nằm ngoài git.
`make test-books` kiểm: LWW 17 chapter, Treasure Island 34 chapter (6 part), Pride and Prejudice 61
chapter, đủ 7 file.

## 8. Ingest vào Neo4j (LangGraph)

```bash
echo 'NEO4J_PASSWORD=<mật-khẩu, >= 8 ký tự>' >> ~/.config/book-clone/secrets.env   # không commit, không in
make neo4j-up                                  # Neo4j 5 community, chờ healthcheck xanh
uv run pov extract ~/.local/share/book-clone/books/lww.html
uv run pov ingest the-lion-the-witch-and-the-wardrobe      # hoặc: make ingest BOOK=<book_id>
uv run pov neo4j-status                        # kết nối và các sách đã nạp
uv run pov graph                               # sơ đồ Mermaid của LangGraph
make neo4j-shell                               # cypher-shell;  make neo4j-down để tắt
```

Graph (deterministic, không LLM): `load_extracted → validate → ensure_schema → write_book →
write_units → write_paragraphs → verify`, cộng một node `analysis_placeholder` (mặc định tắt) làm chỗ cắm
cho các bước phân tích của bạn. Mô hình dữ liệu:
`(:Book)-[:HAS_UNIT]->(:Unit)-[:HAS_PARAGRAPH]->(:Paragraph)` cùng các chuỗi `NEXT`, và
`(Part)-[:CONTAINS]->(Chapter)` khi sách có part. Ghi bằng `MERGE` nên chạy lại không sinh trùng.
Cờ: `--checkpoint sqlite` và `--resume` (chạy tiếp sau crash), `--replace` (ghi lại từ đầu).
Chi tiết, 10 câu Cypher và cách thêm node: [`docs/INGEST_BASE.md`](docs/INGEST_BASE.md).

`docker/compose.yml` chỉ có Neo4j và đặt project name `book-clone-dev` (không phải `book-clone`), nên
container, network và **volume khác hẳn** stack `book-clone` đang chạy. Cổng host cũng khác để không
đụng nhau: stack kia dùng `7474`/`7687`, ở đây là Neo4j Browser **`7475`** và Bolt **`7688`** (đổi bằng
`NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, đã có trong `config.py`). APOC là tùy chọn, tắt mặc định.

## 9. Tiếp theo

Xem [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md): các bước phân tích B1+ như những node mới của graph, kèm
con trỏ tới spec và tới code tham chiếu ở branch `integration`.
