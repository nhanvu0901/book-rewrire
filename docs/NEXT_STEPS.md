# Bước tiếp theo (CHƯA làm trong branch này)

Branch `clean/a-extract` dừng ở **cuối phase A**: sách đã thành file `book.json` + `canonical.txt` +
`units/*.txt`. Tài liệu này chỉ nói **việc kế tiếp là gì và nhìn vào đâu**, không cài đặt gì cả.
Những chỗ cần bạn quyết được viết thành **lựa chọn kèm đánh đổi**, không phải kết luận.

Tài liệu tham chiếu (nằm ngoài repo này, trong thư mục artifact của AO):

- Thiết kế v2: `/Users/nhanvu/.ao/data/artifacts/book-clone-1/pov_retelling_system_design_v2.md`
  (mục 5 mô hình dữ liệu, mục 6 Neo4j, mục 7 luồng A/B/C, mục 8 engine tri thức).
- Giải thích từng bước: `/Users/nhanvu/.ao/data/artifacts/book-clone-1/flow_walkthrough_step_by_step.md`.

> Nên chép hai file này vào `docs/` của repo khi bạn bắt đầu, để chúng đi cùng code.

## 1. Việc kế tiếp: nạp `book.json` vào Postgres (spec mục 5.1)

Đích: một lệnh kiểu `pov ingest <book_id>` đọc `extracted/<book_id>/book.json`, kiểm tra bằng
`ExtractedBook.model_validate_json` (đây chính là hợp đồng của file) rồi ghi vào Postgres.
`docker/compose.yml` và `make db-up` đã sẵn sàng (project `book-clone-dev`, Postgres `:5433`).

**`book.json` ứng với bảng nào:**

| `book.json` | Bảng (spec 5.1) | Ghi chú |
|---|---|---|
| `book` | `books(id, title, author, format, sha256, created_at)` | `created_at` do DB đặt; `source` là thông tin thêm |
| `candidates` | `structure_candidates(book_id, cand_id, kind, text, char_pos, preview)` | gắn với sách, không gắn với một map |
| `map_method`, `map_items` | `structure_maps(book_id, version, status, created_by)` | `book.json` **không có** `version`/`status`: bước ingest tự đặt (`proposed`) |
| `units` | `units(id, map_version, kind, title, parent_id, char_start, char_end, order)` | `map_version` do bước ingest gán |
| `paragraphs` | `paragraphs(id, unit_id, order, text, char_start, char_end)` | thêm cột `flags` nếu muốn giữ cờ `too_short`... |
| `warnings` | (chưa có bảng) | có thể bỏ, hoặc lưu cùng `structure_maps` |

**Những điểm bạn cần chọn:**

1. **`canonical.txt` lưu ở đâu?** Mọi `char_start/char_end` chỉ có nghĩa khi có nó. Lựa chọn: (a) giữ
   file trên đĩa, lưu đường dẫn; (b) cột `text` trong `books`; (c) không lưu vì paragraph đã có `text`
   và offset chỉ dùng để debug. (b) đơn giản nhất để toàn vẹn; (c) nhẹ nhất.
2. **Nạp lại cùng một file?** Lựa chọn: bỏ qua, hoặc tạo `structure_maps.version` mới. Bản tham chiếu
   chọn: cùng `sha256` thì dùng lại `books`, mỗi lần nạp tạo một version map mới và không bao giờ sửa
   version cũ; cùng `id` nhưng khác `sha256` thì báo lỗi (giống `BookIdConflictError` trong `output.py`).
3. **Migration:** Alembic (bản tham chiếu dùng) hoặc `create_all` / SQL thuần khi còn thử nghiệm.
4. **Lớp truy cập dữ liệu:** SQLAlchemy 2 + psycopg 3 (bản tham chiếu) hoặc psycopg thuần cho ít
   thứ phải học hơn.
5. **A2d, bạn xác nhận bản đồ cấu trúc (`proposed` → `confirmed`)** chưa có ở phase A. Chỉ cần quyết
   khi có UI hoặc lệnh xác nhận; trước đó có thể nạp thẳng với status `proposed`.
6. **Đoạn có flag** (`too_short` do số trang như `0033m` hay `{6}`): giữ cả để phân tích sau hay lọc
   lúc ingest. Phân tích B1+ nên không nhìn thấy số trang.

**Gợi ý thứ tự làm nhỏ:** schema + migration → hàm `ingest(book.json)` trong **một transaction** →
test với Postgres thật bằng compose → đọc ngược từ DB rồi so với `book.json` (round trip).

## 2. Sau đó: phân tích B1+ (spec mục 7B, mô hình dữ liệu 5.2)

B1 tên gọi nhân vật → B2 gộp nhân vật → B3 beats → B4 có mặt và giác quan → B4b lời thoại → B5 sự kiện
tri thức → B5c quan hệ → B5b thuật ngữ → B6 kiểm tra → B7 bạn rà → B8 engine tri thức (spec mục 8).
Mỗi bước là một việc nhỏ cho DeepSeek, kết quả là snapshot **bất biến**.

- Dùng lại `src/pov_retell/llm.py`: nó đã có JSON mode, validate Pydantic, thử lại tối đa 2 lần kèm
  lỗi, thinking luôn tắt. Bạn sẽ cần thêm: bản có `max_tokens`/`temperature` theo bước, ghi log gọi
  LLM (`llm_calls`), phiên bản prompt, và (nếu muốn) cache; những thứ này **cố ý chưa có** ở đây.
- Nguyên tắc 2 của spec ("LLM đề xuất, code neo và kiểm"): LLM trả ID hoặc **chuỗi trích nguyên văn**,
  code tìm chuỗi trong văn bản gốc để tính vị trí. Đã có mẫu ở bản tham chiếu: `analysis/anchoring.py`.
- Phiên bản tham chiếu theo bước: `analysis/mentions.py` (B1), `roster.py` (B2), `beats.py` (B3),
  `presence.py` (B4), `utterances.py` (B4b), `knowledge_events.py` (B5), `relationships.py` (B5c),
  `terms.py` (B5b), `validate.py` (B6), `runner.py` (nối các bước), và engine tri thức ở `domain/`.

## 3. Rồi Neo4j (spec mục 6, bước B9)

Đồ thị là **bản chiếu** dựng lại từ Postgres, không phải nguồn sự thật. `docker/compose.yml` đã có
Neo4j 5 community (Bolt `:7688`). Bản tham chiếu còn bật APOC trong compose (`NEO4J_PLUGINS`); bản này
bỏ để tối giản, thêm lại nếu truy vấn cần. Xem `infrastructure/graph/` (`projection.py`, `sync.py`,
`queries.py`) và `docs/neo4j_explore.md` (cách mở Browser, schema, các truy vấn Cypher đã thử).

## 4. Code đầy đủ nằm ở đâu

Branch **`integration`** (khoảng 2000 test, nhiều lớp). Đọc mà không đổi branch:

```bash
git ls-tree -r --name-only integration | less
git show integration:src/pov_retell/analysis/beats.py
git show integration:docs/ingestion.md          # phần ingest đầy đủ
git show integration:docs/data_model.md         # 31 bảng, vì sao thiết kế như vậy
```

Hoặc mở worktree `/Users/nhanvu/.ao/data/worktrees/book-clone/book-clone-27` (đang ở `integration`;
có thể bị xóa sau này, `git show integration:...` luôn dùng được).

| Cần | Vị trí trên `integration` |
|---|---|
| Ingest đầy đủ (A1-A3 + persist) | `src/pov_retell/ingest/`, `docs/ingestion.md` |
| Bảng, repository, migration | `src/pov_retell/infrastructure/db/`, `alembic/versions/`, `docs/data_model.md` |
| Phân tích B1-B6 | `src/pov_retell/analysis/`, `docs/analysis_pipeline.md` |
| Engine tri thức B8 | `src/pov_retell/domain/engine.py`, `knowledge.py`, `docs/knowledge_engine.md` |
| LLM gateway (cache, chi phí, log) | `src/pov_retell/infrastructure/llm/`, `docs/llm_gateway.md` |
| Neo4j | `src/pov_retell/infrastructure/graph/`, `docs/neo4j_explore.md` |
| Chạy cả cuốn từ đầu đến cuối | `src/pov_retell/pipeline.py`, `docs/smoke_test.md` |

## 5. Cố ý KHÔNG mang sang từ bản tham chiếu (nhìn lại nếu cần)

- `ingest/numbering.py`: cảnh báo khi số chương lặp hoặc nhảy. Nó sẽ bắt được lỗi `XXVII` trong
  `treasure_island.txt`. Phase A hiện chỉ cắt theo vị trí tiêu đề nên không cần, nhưng đây là một
  kiểm tra rẻ nếu bạn muốn thêm.
- Sửa ngầm bản đồ của LLM (gộp unit chỉ có tiêu đề, bỏ part không có chương): bản này **từ chối kèm
  lỗi** thay vì sửa. Nếu `--map llm` hay bị từ chối ở thực tế, đó là chỗ để cân nhắc lại.
- Hỏi lại LLM kèm lý do khi bản đồ không cắt được, tự quay về heuristic, cache phản hồi, đếm chi phí,
  prompt có phiên bản.
- `ingest/persist.py` và toàn bộ database.

## 6. Giới hạn đã biết của phase A

- **PDF** chưa hỗ trợ (spec: để sau). HTML, EPUB, TXT thôi.
- **`--map llm` chưa chạy thật** (số dư DeepSeek đang bằng 0). Mới được kiểm bằng fake. Lần chạy thật
  đầu tiên nên so với heuristic trên LWW (17 chapter) và để ý chi phí.
- Heuristic dựa vào cách **gõ tiêu đề** (`CHAPTER IV`, `PART ONE`, số La Mã viết hoa, `Prologue`).
  Sách đặt tiêu đề kiểu khác (ví dụ chỉ có tên chương, không số) có thể cần `--map llm`.
- ID đoạn chỉ ổn định trong **một file** (html, epub, txt của cùng cuốn có số đoạn khác nhau).
- `source` trong `book.json` là đường dẫn tuyệt đối trên máy bạn; đừng coi nó là định danh (dùng
  `sha256`).
