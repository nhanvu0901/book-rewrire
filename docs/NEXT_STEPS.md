# Bước tiếp theo

Branch này (`clean/ingest-base`) có hai phần đã xong: **phase A** (sách thành `book.json`) và **base
ingest** (`book.json` thành graph trong Neo4j, bằng LangGraph, không LLM). Tài liệu này chỉ nói **việc
kế tiếp là gì và nhìn vào đâu**, không cài đặt gì cả. Những chỗ cần bạn quyết được viết thành **lựa
chọn kèm đánh đổi**, không phải kết luận.

Tài liệu tham chiếu (nằm ngoài repo này, trong thư mục artifact của AO):

- Thiết kế v2: `/Users/nhanvu/.ao/data/artifacts/book-clone-1/pov_retelling_system_design_v2.md`
  (mục 5 mô hình dữ liệu, mục 6 Neo4j, mục 7 luồng A/B/C, mục 8 engine tri thức).
- Giải thích từng bước: `/Users/nhanvu/.ao/data/artifacts/book-clone-1/flow_walkthrough_step_by_step.md`.

> Nên chép hai file này vào `docs/` của repo khi bạn bắt đầu, để chúng đi cùng code.

## 1. Việc kế tiếp: các bước phân tích B1+ là node mới của graph

Mỗi bước B là **một node tính** (gọi LLM, thuần túy) cộng **một node ghi** (MERGE vào Neo4j). Cách thêm
một node đã được viết từng bước, và chạy thử, ở `docs/INGEST_BASE.md` mục 6. Gợi ý: bắt đầu bằng B1 vì
nó nhỏ nhất và chưa cần gộp hay phụ thuộc bước nào khác.

| Bước (spec mục 7B) | Đầu vào | Có thể trở thành trong Neo4j |
|---|---|---|
| B1 tên gọi nhân vật | `Paragraph.text` | `(:Mention)` gắn vào `Paragraph` |
| B2 gộp nhân vật | các `Mention` | `(:Character)` và `(:Mention)-[:REFERS_TO]->(:Character)` |
| B3 beats | `Paragraph` theo unit | `(:Unit)-[:CONTAINS]->(:Beat)-[:NEXT]->(:Beat)` (spec mục 6) |
| B4 có mặt và giác quan | `Beat`, `Character` | `(:Character)-[:PRESENT_AT {modality}]->(:Beat)` |
| B4b lời thoại | đoạn có thoại | `(:Utterance)` |
| B5 tri thức | `Beat` và thoại | `(:KnowledgeEvent)`; `LEARNED`, `ABOUT`, `FROM` |
| B5c, B5b | | quan hệ giữa nhân vật; thuật ngữ |
| B6 kiểm tra, B7 bạn rà, B8 engine tri thức | | spec mục 7B và 8 |

Spec mục 6 đã vẽ sẵn lược đồ Neo4j cho các bước này.

- Dùng lại `src/pov_retell/llm.py`: JSON mode, validate Pydantic, thử lại tối đa 2 lần kèm lỗi, thinking
  luôn tắt. Bạn sẽ cần thêm: `max_tokens`/`temperature` theo bước, ghi log gọi LLM, phiên bản prompt, và
  (nếu muốn) cache; những thứ này **cố ý chưa có** ở đây.
- Nguyên tắc 2 của spec ("LLM đề xuất, code neo và kiểm"): LLM trả ID hoặc **chuỗi trích nguyên văn**,
  code tìm chuỗi trong văn bản gốc để tính vị trí. Mẫu tham chiếu: `analysis/anchoring.py` (xem mục 3).
- Tham chiếu theo bước trên `integration`: `analysis/mentions.py` (B1), `roster.py` (B2), `beats.py` (B3),
  `presence.py` (B4), `utterances.py` (B4b), `knowledge_events.py` (B5), `relationships.py` (B5c),
  `terms.py` (B5b), `validate.py` (B6), `runner.py` (nối các bước), và engine tri thức ở `domain/`.

## 2. Những điều bạn cần quyết vì chỉ dùng Neo4j

Thiết kế v2 coi **Postgres là nguồn sự thật** và Neo4j là bản chiếu dựng lại được. Base này đi đường
khác theo yêu cầu (chỉ LangGraph + Neo4j), nên vài thứ mà Postgres vốn gánh cần một chỗ ở mới:

1. **Snapshot phân tích bất biến** (nguyên tắc 7: mỗi lần chạy là một snapshot, chỉ ghi thêm).
   Lựa chọn: (a) thêm `run_id` vào khóa của mọi node phân tích (`Mention {book_id, run_id, id}`);
   (b) một node `(:AnalysisRun)` và cạnh `PRODUCED` tới các kết quả; (c) giữ mỗi run là file JSON và chỉ
   chiếu run đang dùng vào Neo4j. (a) đơn giản nhất; (c) giữ được tính bất biến thật.
2. **Sửa tay (`corrections`, chỉ ghi thêm)**: node `(:Correction)` trỏ tới thứ nó sửa, hoặc file.
3. **Nhật ký gọi LLM và chi phí (`llm_calls`)**: file JSONL, một file SQLite nhỏ (đã có sẵn trong
   dependency vì checkpointer), hoặc node `(:LlmCall)`.
4. **Checkpointer**: `InMemorySaver` hoặc SQLite (đã có). Postgres bị loại theo yêu cầu.
5. **A2d, bạn xác nhận bản đồ cấu trúc** chưa có. Chỗ tự nhiên là một node `confirm` dùng `interrupt`
   (ví dụ chạy được ở `docs/INGEST_BASE.md` mục 3) hoặc cờ `status` trên `Book`/`Unit`.
6. **Project, draft, bản duyệt (spec mục 7C và D)**: chưa bàn tới.

## 3. Code đầy đủ nằm ở đâu

Branch **`integration`** (khoảng 2000 test, nhiều lớp, dùng Postgres + SQLAlchemy). Đọc mà không đổi
branch:

```bash
git ls-tree -r --name-only integration | less
git show integration:src/pov_retell/analysis/beats.py
git show integration:docs/ingestion.md          # phần ingest đầy đủ
git show integration:docs/neo4j_explore.md      # Neo4j: schema, câu Cypher đã thử
```

Hoặc mở worktree `/Users/nhanvu/.ao/data/worktrees/book-clone/book-clone-27` (đang ở `integration`; có
thể bị xóa sau này, `git show integration:...` luôn dùng được).

| Cần | Vị trí trên `integration` |
|---|---|
| Phân tích B1-B6 | `src/pov_retell/analysis/`, `docs/analysis_pipeline.md` |
| Engine tri thức B8 | `src/pov_retell/domain/engine.py`, `knowledge.py`, `docs/knowledge_engine.md` |
| LLM gateway (cache, chi phí, log) | `src/pov_retell/infrastructure/llm/`, `docs/llm_gateway.md` |
| Chiếu sang Neo4j (B9) | `src/pov_retell/infrastructure/graph/` (`projection.py`, `queries.py`), `docs/neo4j_explore.md` |
| Chạy cả cuốn từ đầu đến cuối | `src/pov_retell/pipeline.py`, `docs/smoke_test.md` |
| Postgres (không dùng ở đây) | `src/pov_retell/infrastructure/db/`, `alembic/`, `docs/data_model.md` |

## 4. Cố ý KHÔNG mang sang từ bản tham chiếu (nhìn lại nếu cần)

- `ingest/numbering.py`: cảnh báo khi số chương lặp hoặc nhảy. Nó sẽ bắt được lỗi `XXVII` trong
  `treasure_island.txt`. Phase A cắt theo vị trí tiêu đề nên không cần, nhưng đây là một kiểm tra rẻ.
- Sửa ngầm bản đồ của LLM (gộp unit chỉ có tiêu đề, bỏ part không có chương): bản này **từ chối kèm
  lỗi** thay vì sửa. Nếu `--map llm` hay bị từ chối ở thực tế, đó là chỗ để cân nhắc lại.
- Hỏi lại LLM kèm lý do khi bản đồ không cắt được, tự quay về heuristic, cache phản hồi, đếm chi phí,
  prompt có phiên bản.
- Toàn bộ Postgres, SQLAlchemy, Alembic.

## 5. Giới hạn đã biết

- **PDF** chưa hỗ trợ (spec: để sau). HTML, EPUB, TXT thôi.
- **`--map llm` chưa chạy thật** (số dư DeepSeek đang bằng 0). Mới được kiểm bằng fake.
- Heuristic dựa vào cách **gõ tiêu đề** (`CHAPTER IV`, `PART ONE`, số La Mã viết hoa, `Prologue`). Sách
  đặt tiêu đề kiểu khác có thể cần `--map llm`.
- ID đoạn chỉ ổn định trong **một file** (html, epub, txt của cùng cuốn có số đoạn khác nhau).
- **`--replace` chỉ xóa `Unit` và `Paragraph`** của sách. Khi bạn thêm node phân tích (`Mention`, ...),
  cũng thêm việc xóa chúng vào `Neo4jWriter.delete_book`, nếu không chúng thành node mồ côi.
- State của graph giữ cả `book.json` nên file checkpoint SQLite nặng (khoảng 4 MB cho Treasure Island).
- Chưa có kiểm soát chạy đồng thời: đừng chạy hai `pov ingest` cho cùng một cuốn cùng lúc.
- `source` trong `book.json` là đường dẫn tuyệt đối trên máy bạn; đừng coi nó là định danh (dùng `sha256`).
