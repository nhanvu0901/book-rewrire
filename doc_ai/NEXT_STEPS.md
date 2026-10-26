# Kế hoạch ingest mới: Character Discovery & Resolution

Ngày cập nhật: 19/10/2026.
Nguồn yêu cầu: ý tưởng mới của người dùng trong phiên này.
Tài liệu này thay thế nội dung kế hoạch trước đó.
B1–B2 đã được triển khai ngày 20/10/2026 theo luồng node/edge người dùng chốt.

## Current implementation (2026-10-21)

- `ingest_book` runs only the `character_discovery` LangGraph.
- The graph runs load_chapters → extract_characters → validate_characters → save_json
  until every chapter finishes. Its extraction logic, models, and prompt are unchanged.
- After discovery, the pipeline writes selected Character properties to Neo4j.
- Relationship verification, its graph, models, prompt, and edge writer have been removed.
- Character relationship maps remain discovery proposals in JSON; no `RELATES_TO` edges
  are created by the current pipeline.
- Output contains cumulative characters.json and chapter snapshots under a unique run
  directory. Existing outputs are retained. There are no checkpoints or resume.
- See [INGEST_BASE.md](INGEST_BASE.md) for the current workflow and limitations.
- The sections below preserve the original design discussion and are historical.

## 1. Phạm vi đã được người dùng mô tả

Trong `ingest_book(book_id)`, luồng sẽ được chia thành các bước có tên rõ ràng.
Bước đầu tiên là **B1–B2 — Character Discovery & Resolution**.

Bước này:
- Đọc lần lượt các file chương trong `book/extracted/<book_id>/units/`.
- Gửi nội dung từng chương cho LLM để tìm và phân giải nhân vật.
- Duy trì một danh sách JSON nhân vật tích lũy qua các chương.
- Cập nhật tên, bí danh, thuộc tính và các lần xuất hiện khi đọc tiếp.
- Lưu vào Neo4j một tập trường được chọn theo mẫu người dùng đưa ra.

Các bước sau Character Discovery & Resolution chưa được thiết kế.
Chưa khôi phục workflow, schema hoặc writer cũ.

## 2. Luồng trong ingest_book

```text
ingest_book(book_id)
    │
    └── B1–B2: Character Discovery & Resolution
          │
          ├── Đọc danh sách chương theo thứ tự
          ├── Khởi tạo danh sách nhân vật rỗng
          │
          ├── Chương 1 + danh sách hiện tại → LLM → danh sách cập nhật
          ├── Chương 2 + danh sách hiện tại → LLM → danh sách cập nhật
          ├── ...
          ├── Chương cuối + danh sách hiện tại → LLM → danh sách cuối
          │
          └── Lưu các trường Character được chọn vào Neo4j
```

Danh sách sau chương trước là đầu vào của chương sau.
Các chương chạy tuần tự vì cần kế thừa kết quả đã có.

### Đầu vào mỗi lượt gọi LLM

- Nội dung một file chương, giữ các ID như `[u01_p001]`.
- Danh sách JSON nhân vật đã tích lũy.
- Yêu cầu tìm nhân vật mới, nhận ra nhân vật cũ và cập nhật thông tin từ chương hiện tại.

Cách trả kết quả được đề xuất: LLM trả **toàn bộ danh sách nhân vật tích lũy đã cập nhật**.
Nhân vật không xuất hiện trong chương hiện tại vẫn được giữ lại với thông tin đã có.
Đây là cách diễn giải đề xuất cho “maintain the JSON list”, có thể điều chỉnh theo người dùng.

### Thứ tự đọc chương

Nguồn văn bản để gửi LLM là các file trong `units/`, đúng theo yêu cầu.
Thứ tự dựa vào số thứ tự đầu tên file, theo số nguyên: 1, 2, ... 10.
Không phụ thuộc thứ tự liệt kê file của hệ điều hành.
Có thể đối chiếu với `book.json` để kiểm tra chương/ID đoạn; không thay nguồn văn bản bằng file khác.

## 3. JSON nhân vật theo mẫu người dùng

Ví dụ dưới đây là **mẫu cấu trúc**, chưa phải dữ liệu trích xuất đã kiểm tra:

```json
{
  "candidate_name": "Edmund Pevensie",
  "aliases": ["Edmund"],
  "attributes": {
    "gender": "male",
    "species": "human",
    "age_description": "young boy",
    "physical_description": null,
    "personality_traits": []
  },
  "mentions": [
    {
      "text": "Edmund",
      "paragraph_id": "u01_p003"
    },
    {
      "text": "Edmund Pevensie",
      "paragraph_id": "u01_p010"
    }
  ],
  "resolution_status": "candidate"
}
```

Các tên và ID trong mẫu không được xem là bằng chứng thật.
Với Narnia hiện tại, `u01_p003` là lời Peter; “Edmund” đã xuất hiện ở `u01_p001`.
Kết quả chạy thật phải kiểm tra văn bản của từng mention trong đúng đoạn.
Tên đầy đủ chỉ được bổ sung khi nội dung đã đọc hỗ trợ; không lấy kiến thức ngoài sách để điền tên.

### Duy trì thông tin qua các chương

- Nhân vật mới: thêm vào danh sách.
- Nhân vật cũ: cập nhật đúng nhân vật đó.
- `aliases`: bổ sung cách gọi mới, giữ các cách gọi đã được xác nhận.
- `mentions`: tích lũy các bằng chứng đã tìm được, không làm mất kết quả chương trước.
- Thuộc tính chưa được sách đề cập: dùng `null` hoặc danh sách rỗng.
- Giá trị đã biết không bị thay bằng `null` chỉ vì chương sau không nhắc lại.
- Khi mô tả hoặc tính cách thay đổi, cập nhật dựa vào ngữ cảnh mới; tránh làm mất diễn tiến trước đó.
- Mâu thuẫn hoặc cách gọi mơ hồ cần được ghi nhận để xử lý, không tự gộp chỉ vì tên giống nhau.

Schema mention hiện tại chỉ định vị tới đoạn và chuỗi văn bản.
Nó chưa phân biệt được nhiều lần xuất hiện của cùng một chuỗi trong cùng một đoạn.
Nếu cần đếm hoặc neo từng lần riêng biệt, phải bổ sung thiết kế sau.

## 4. Character ID để cập nhật đúng nhân vật

Neo4j cần `character_id` ổn định, ví dụ `char_001`.
Trường này chưa có trong ví dụ JSON của LLM.

**Đề xuất:** code cấp `character_id` cho nhân vật mới và giữ trong bản JSON lưu trữ.
Danh sách gửi lại LLM kèm các ID này; cập nhật nhân vật cũ phải chỉ đúng ID.
Tên đổi từ một cách gọi ngắn sang tên đầy đủ vẫn giữ nguyên `character_id`.

Việc phân giải cùng người do LLM dựa trên ngữ cảnh.
Code kiểm tra ID hợp lệ, giữ danh sách cũ và ngăn mất/nhân đôi bản ghi do lỗi kết quả.
Không dùng tên hoặc bí danh làm khóa duy nhất.

## 5. Cập nhật tính cách và xuất trường personality

Người dùng yêu cầu thuộc tính như tính cách được cập nhật khi đọc qua các chương.

Ví dụ kết quả mong muốn cuối sách:

```text
Initially jealous and insecure, later brave and loyal.
```

JSON mẫu có `attributes.personality_traits` dạng danh sách;
Neo4j cần `personality` dạng chuỗi tóm tắt.

**Đề xuất cần chốt:** thêm `attributes.personality_summary` vào kết quả LLM.
LLM cập nhật tóm tắt này cùng danh sách traits sau mỗi chương; ánh xạ nó sang `c.personality`.
Không tự suy ra “initially/later” từ một danh sách traits không có thông tin diễn tiến.

Đề xuất giữ bản JSON sau từng chương để xem tính cách đã được cập nhật như thế nào.
Bản cuối là hồ sơ sau khi đọc toàn sách; nó có thể chứa thông tin của các chương cuối.
Nếu một bước tương lai cần hồ sơ ở một chương cụ thể, dùng bản ở chương đó.

## 6. Tách dữ liệu JSON đầy đủ và node Neo4j

JSON giữ kết quả đầy đủ: thuộc tính, traits, mentions và các cập nhật.
Neo4j chỉ nhận các trường người dùng chỉ định:

| Trường Neo4j | Nguồn/ý nghĩa |
|---|---|
| `book_id` | ID cuốn đang xử lý |
| `run_id` | ID phiên xử lý |
| `character_id` | ID ổn định của nhân vật |
| `canonical_name` | `candidate_name` sau phân giải |
| `aliases` | Danh sách bí danh tích lũy |
| `gender` | `attributes.gender` |
| `species` | `attributes.species` |
| `age_description` | `attributes.age_description` |
| `physical_description` | `attributes.physical_description` |
| `personality` | Chuỗi tóm tắt tính cách; cách tạo cần chốt ở mục 5 |
| `first_mention_id` | ID đoạn của mention sớm nhất theo thứ tự đọc |
| `resolution_status` | Trạng thái phân giải; điều kiện chuyển verified cần chốt |

`first_mention_id` theo mẫu là **ID đoạn**, chưa phải ID của một node Mention.
Tính bằng thứ tự chương và thứ tự đoạn, không dựa vào thứ tự mảng LLM trả.
Không đưa toàn bộ `mentions` hoặc `personality_traits` lên node Character.

Mẫu Cypher người dùng yêu cầu, là hợp đồng dữ liệu chứ chưa được triển khai:

```cypher
MERGE (c:Character {
    book_id: "book_01",
    run_id: "run_01",
    character_id: "char_001"
})
SET
    c.canonical_name = "Edmund Pevensie",
    c.aliases = ["Edmund"],
    c.gender = "male",
    c.species = "human",
    c.age_description = "young boy",
    c.physical_description = "Dark-haired boy",
    c.personality = "Initially jealous and insecure, later brave and loyal.",
    c.first_mention_id = "u01_p003",
    c.resolution_status = "verified"
RETURN c;
```

Các giá trị trong ví dụ sẽ được thay bằng dữ liệu đã kiểm tra.
Tính duy nhất của bộ `(book_id, run_id, character_id)` cần được bảo đảm khi triển khai.
Chưa tạo node hoặc quan hệ khác ngoài Character trong bước này.

## 7. Kiểm tra trước khi tiếp nhận kết quả LLM

Đề xuất các kiểm tra gắn trực tiếp với dữ liệu trên:

- JSON đúng schema.
- ID đoạn tồn tại; `mentions.text` có trong đúng đoạn.
- ID nhân vật cập nhật phải tồn tại, nhân vật mới được cấp ID riêng.
- Kết quả không làm mất nhân vật/bằng chứng đã tích lũy.
- Bí danh chung không tự động đồng nghĩa là cùng một người.
- Không tự chuyển `candidate` thành `verified` chỉ vì JSON parse thành công.

Cần chốt ý nghĩa `verified`: người dùng duyệt hay một quy trình tự động.
Kiểm tra schema và trích dẫn xác nhận hình dạng/bằng chứng, chưa chứng minh mọi quyết định gộp là đúng.
Trong khi chưa chốt, không mặc định ghi `verified` như một hằng số.

## 8. Lưu file và hoàn tất — đề xuất

Thư mục dự kiến:

```text
book/ingest/<book_id>/<run_id>/
    characters.json                  danh sách tích lũy mới nhất
    chapters/<unit_id>.characters.json
                                     bản kết quả sau từng chương
```

- Lưu kết quả mỗi chương sau khi kiểm tra thành công.
- Khi lỗi một chương, giữ kết quả chương đã hoàn thành; không lưu danh sách lỗi như kết quả hợp lệ.
- Sau chương cuối, hoàn tất phân giải/trạng thái rồi ghi các trường Character vào Neo4j.
- Việc ghi dùng cùng bộ khóa để chạy lại cùng phiên không tạo nhân vật trùng.

Vị trí file và thời điểm ghi Neo4j ở cuối bước đã được triển khai.

## 9. Những lựa chọn cho lần phát triển tiếp theo

1. Quy trình xác nhận verified. Hiện ghi candidate vào Neo4j và chưa có bước tự xác minh.
2. Có chuyển từ toàn bộ danh sách sang chỉ phần cập nhật khi danh sách tích lũy quá dài không?
3. Có thêm attributes.personality_summary để thay cách nối traits hiện tại không?

Các bước ingest tiếp theo sẽ được bổ sung từ ý tưởng mới của người dùng.
