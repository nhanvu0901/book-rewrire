# BOOK-TO-VIDEO AI

> **Tài liệu tổng hợp ý tưởng, yêu cầu sản phẩm và thiết kế kỹ thuật — bản 0.1 (14/10/2026)**  
> **Ngôn ngữ:** Tiếng Việt. **Trạng thái:** Project concept / architecture / proposed implementation, **chưa xác nhận có code hoặc MVP hoạt động**.  
> **Phạm vi hiện tại:** Sách có văn bản trích xuất được từ PDF; mục tiêu sản phẩm dài hạn có thể hỗ trợ EPUB/DOCX. **Bỏ qua OCR** theo quyết định mới nhất.

---

## 0. Tóm tắt một trang — Project Executive Summary

### Dự án là gì?

Xây dựng một hệ thống AI có thể **tiếp nhận toàn bộ một cuốn sách, hiểu cấu trúc và nội dung ở nhiều cấp độ, rồi chuyển thể thành các video narration scripts được tạo lần lượt, từng phần một, cho đến hết sách**.

Sản phẩm **không chỉ là PDF chatbot** và **không chỉ tóm tắt sách một lần**. Nó là một **stateful, structure-aware narration engine**: biết chính xác nội dung nào đã xử lý, nội dung nào sẽ xử lý tiếp, phải giữ lại những điểm cốt lõi nào, và cách nối mạch chuyện/kiến thức giữa các tập.

### Ý tưởng cốt lõi

> **TOC / Book Map quyết định “đọc gì và đọc theo thứ tự nào”; source text quyết định “nội dung thật là gì”; summaries và embeddings quyết định “cần nhớ và tìm thêm ngữ cảnh gì”; narration engine quyết định “chuyển thành lời dẫn như thế nào”; progress state quyết định “đã làm đến đâu”.**

### Đầu vào / đầu ra

- **Input:** Một cuốn sách hoàn chỉnh, ưu tiên **PDF có text**; hỗ trợ EPUB/DOCX là mở rộng đã từng được đề cập, không phải phạm vi MVP bắt buộc.
- **Internal artifacts:** `book_map`, nội dung gốc được gắn vào từng node, ordered reading units, section/chapter/book summaries, chunk embeddings, trạng thái narration, metadata nhân vật/khái niệm/timeline khi cần.
- **Output mỗi lần người dùng yêu cầu:** một **video narration script** cho phần tiếp theo, có thể chuyển văn phong/cách kể, nhưng bám sát nội dung gốc và nối tiếp các tập trước.
- **Output cả hành trình:** Chuỗi episode bao phủ phần nội dung sách đã chọn, **đúng thứ tự, không bỏ sót, không lặp và không tự ý tạo thêm sự kiện/luận điểm quan trọng**.
- **Điểm đặc biệt mới:** hỗ trợ **chuyển ngôi kể / POV** (ví dụ ngôi thứ ba ↔ ngôi thứ nhất) ở **bước sinh narration**, không sửa sự kiện nền tảng của tác phẩm.

### Công thức kiến trúc

```text
BOOK FILE (text PDF)
      |
      v
Text Extraction + TOC Discovery
      |
      v
TOC Hierarchy -> CANONICAL BOOK MAP -> Source Span Alignment
      |                                    |
      |                                    v
      |                             Ordered Reading Units
      |                                    |
      v                                    v
Hierarchical Summaries             Original Content / Chunks
      |                                    |
      +----------------+-------------------+
                       |
                  Embeddings /
             Context Retrieval (RAG)
                       |
                 CONTEXT BUILDER
                       |
                Narration Planning
                       |
                POV / Style Engine
                       |
                Narration Writer
                       |
             Fidelity + POV Verifier
                       |
         DRAFT EPISODE + SOURCE TRACE
                       |
             REVIEW / REGENERATE
                       |
               APPROVE -> SAVE STATE
                       |
             NEXT -> next content
                       |
                 END OF BOOK
```

> **Bất biến quan trọng:** Vector search **không bao giờ** chọn section kế tiếp thay cho thứ tự trong `book_map`.

---

## 1. Vấn đề cần giải quyết

### 1.1. Nếu chỉ đưa cả sách vào một LLM

Một cách làm quá đơn giản là: tải PDF lên, đưa toàn bộ văn bản vào context, yêu cầu “viết script phần 1, sau đó phần 2”. Cách này có những rủi ro:

1. **Thứ tự không ổn định:** Mô hình có thể nhảy phần, trộn chương, hoặc quyết định thứ tự theo độ nổi bật về ngữ nghĩa.
2. **Bỏ sót thông tin:** Summary ngắn có thể bỏ ví dụ, nhân vật, biến cố, chứng cứ hoặc luận điểm quan trọng.
3. **Trùng lặp:** Các tập có thể kể lại nội dung đã hoàn thành.
4. **Mất continuity:** Thuật ngữ, nhân vật, timeline, cách gọi và giọng kể thay đổi giữa các episode.
5. **Không có trạng thái rõ ràng:** Không biết chính xác đã chuyển thể tới đoạn nào khi người dùng quay lại hôm sau.
6. **Khó xác minh:** Không truy ngược câu thoại về phần nội dung nguồn để kiểm tra độ trung thành.
7. **Đổi ngôi kể sai:** Khi chuyển ngôi thứ ba thành ngôi thứ nhất, mô hình có thể khiến nhân vật biết những thông tin mà nhân vật không thể biết ở thời điểm đó.
8. **Chi phí:** Lặp lại toàn bộ sách trong context của mọi request tốn token và không cần thiết.

### 1.2. Cách tiếp cận của dự án

Không dựa vào một prompt lớn hay trí nhớ tạm thời của một mô hình. Thay vào đó:

- **Lấy cấu trúc của tác phẩm làm nguồn sự thật về thứ tự.**
- **Lưu text gốc và source positions** làm nguồn sự thật về nội dung.
- **Tạo trí nhớ phân cấp** từ sections → chapters → toàn sách.
- **Sử dụng RAG có kiểm soát** để khôi phục ngữ cảnh liên quan, không thay thế nội dung hiện tại.
- **Sinh theo từng đơn vị có checkpoint**, chỉ chuyển tiếp khi được duyệt.
- **Tách event/fact representation khỏi narrator POV** để có thể kể lại dưới nhiều góc nhìn mà không làm sai sự kiện.

---

## 2. Mục tiêu sản phẩm và phạm vi

### 2.1. Product goals đã nêu

1. Đọc và hiểu **toàn bộ cuốn sách** ở cấp độ cấu trúc, chủ đề, diễn biến và các quan hệ xuyên chương.
2. Hỗ trợ **các sách có bố cục khác nhau**, căn cứ vào TOC thực tế thay vì giả định tất cả có cấu trúc giống nhau.
3. Tạo **một phần narration mỗi lần người dùng gọi**, rồi tiếp tục các phần kế tiếp theo thứ tự đến hết sách.
4. Nội dung được **chuyển thể để phù hợp với lời dẫn video**, không chỉ đọc nguyên văn; **giữ nguyên ý chính, sự kiện, luận điểm và mạch logic** trong phạm vi chuyển thể đã được chọn.
5. Có **memory và persistent state** qua nhiều lần tạo script.
6. Có khả năng **chuyển ngôi kể / điểm nhìn** (third-person ↔ POV), giữ đúng hiểu biết từng nhân vật.
7. Cho phép regenerate/rewrite mà không vô tình đánh dấu là đã hoàn thành hoặc phá thứ tự.
8. Đo lường được coverage và độ trung thành với nội dung nguồn.

### 2.2. Những gì không phải mục tiêu hiện tại

- **OCR / DeepSeek-OCR:** được **loại khỏi workflow thiết kế hiện tại**. Nếu đầu vào không có text extractable, MVP có thể từ chối hoặc yêu cầu bản có text; không cần xây OCR module.
- **Video rendering / TTS / hình ảnh / dựng cảnh:** không phải phần cốt lõi đã được xác định ở thời điểm này. Output trọng tâm là **narration script**, không mặc định hệ thống tạo video MP4 hoàn chỉnh.
- **Chat với tài liệu tự do:** không phải chức năng chính; có thể bổ sung sau.
- **Dùng semantic search quyết định “chương tiếp theo”:** bị loại bỏ vì dễ gây bỏ sót/trộn thứ tự.
- **Tóm tắt toàn sách trong một lần rồi coi summary là nguồn duy nhất:** bị loại bỏ.

### 2.3. Các quyết định đã thống nhất và đề xuất chưa chốt

| Chủ đề | Trạng thái | Nội dung |
|---|---|---|
| Tạo narration cho toàn sách qua nhiều lần gọi | **Yêu cầu đã nêu** | Từng phần, đến hết sách |
| Dùng TOC để xác định hierarchy | **Hướng đã chọn** | Không hard-code cấu trúc một kiểu sách |
| Canonical `book_map` có thứ tự | **Hướng đã chọn** | Làm nguồn sự thật cho tiến trình |
| Full source text của phần hiện tại | **Hướng đã chọn** | Không thay thế bằng vector/top-k chunks |
| Book/chapter/section summaries | **Hướng đã chọn** | Hierarchical memory |
| Embeddings / RAG cho ngữ cảnh | **Hướng đã chọn** | Chỉ dùng bổ trợ, có thể tối giản MVP |
| Stateful NEXT / APPROVE / REGENERATE | **Hướng đã chọn** | Tiến trình chỉ cập nhật khi được chấp thuận |
| Chuyển ngôi kể/POV | **Yêu cầu bổ sung** | Áp dụng lúc generation, giữ canonical facts |
| OCR | **Loại khỏi phạm vi hiện tại** | Không thiết kế OCR pipeline |
| LangGraph, LlamaIndex, pgvector | **Đề xuất công nghệ** | Chưa được xác nhận là stack triển khai cuối cùng |
| Số phút/words mỗi tập | **Chưa quyết** | Cần test theo thể loại và output |
| Model LLM, model embedding | **Chưa quyết** | Cần đánh giá fidelity, giá thành, context |
| EPUB/DOCX | **Ý tưởng mở rộng** | Đã từng nằm trong mục tiêu chung |
| Character graph, timeline nâng cao | **Đề xuất mở rộng** | Ưu tiên mạnh hơn với fiction/POV |

---

## 3. Khái niệm nền tảng: 5 lớp phải tách rời

### 3.1. Book Map — sách được tổ chức như thế nào?

Trả lời: có những Part/Chapter/Section/Scene nào, cha-con ra sao, chúng xuất hiện theo thứ tự nào, nằm ở đâu trong nguồn.

### 3.2. Source Store — nội dung gốc thực sự là gì?

Trả lời: toàn văn nằm trong mỗi section/reading unit, text span nằm ở những trang và offset nào; có thể truy ngược về tài liệu gốc.

### 3.3. Knowledge Store — sách nói gì và các phần liên quan ra sao?

Trả lời: section summaries, chapter summaries, book summary, concepts, nhân vật, timeline, chunk embeddings, cross-references, diễn biến luận điểm.

### 3.4. Narration Generator — chuyển nội dung thành kịch bản như thế nào?

Trả lời: lập kế hoạch coverage, chọn tone/POV, viết lời dẫn có mở/đóng và chuyển mạch, kiểm tra factual fidelity, consistency, POV restrictions.

### 3.5. Narration State — đã đi đến đâu?

Trả lời: episode hiện tại, đoạn nguồn đã được duyệt, coverage interval, script versions, summaries của tập trước, phần kế tiếp, completion status.

> **Không nhầm lẫn:** “Section đã được tóm tắt” ≠ “Section đã được narrate”. Summarization diễn ra từ giai đoạn chuẩn bị; Narration State là tiến độ xuất bản/chuyển thể độc lập.

---

## 4. Workflow A — Đọc Table of Contents và phát hiện cấu trúc

### 4.1. Vì sao TOC quan trọng?

TOC là bản đồ điều hướng tự nhiên của sách. Các cuốn khác nhau có thể là:

```text
Book
 ├─ Chapter 1
 ├─ Chapter 2
 └─ Chapter 3
```

hoặc:

```text
Book
 ├─ Part I
 │   ├─ Chapter 1
 │   │   ├─ Section 1.1
 │   │   └─ Section 1.2
 │   └─ Chapter 2
 └─ Part II
     └─ Chapter 3
```

hoặc fiction:

```text
Book
 ├─ Prologue
 ├─ Part One
 │   ├─ Chapter 1
 │   │   ├─ Scene A (nếu phát hiện/định nghĩa được)
 │   │   └─ Scene B
 │   └─ Chapter 2
 └─ Epilogue
```

hoặc reference/thematic book:

```text
Book
 ├─ Topic A
 │   ├─ Subtopic A1
 │   └─ Subtopic A2
 └─ Topic B
```

**Kết luận:** Không áp một schema cứng bắt buộc mọi sách phải có Part → Chapter → Section. Dùng **generic hierarchical nodes**.

### 4.2. Input giai đoạn hiện tại

- PDF **có văn bản**, không scan/OCR.
- Metadata cơ bản: tên sách, tác giả nếu lấy được, số trang, filename/checksum, phiên bản parser.
- Text extraction theo thứ tự đọc hợp lý (không trộn header/footer, cột hoặc footnote nếu bố cục phức tạp).

### 4.3. Phát hiện TOC bằng hai đường

**A. PDF có embedded outline/bookmarks**

Sử dụng PyMuPDF:

```python
import pymupdf

with pymupdf.open("book.pdf") as doc:
    outline = doc.get_toc()  # mỗi mục: [level, title, page]
    for level, title, page in outline:
        print(level, title, page)
```

Ưu điểm: có level rõ và thường có page anchor. Cần kiểm tra mức độ đầy đủ/chính xác của outline.

**B. TOC chỉ nằm trong nội dung text PDF**

Ví dụ:

```text
CONTENTS
PART I — FOUNDATIONS ....................... 1
    CHAPTER 1 — INTRODUCTION .............. 5
        1.1 Core Idea ...................... 7
        1.2 History ....................... 12
    CHAPTER 2 — PRINCIPLES ............... 21
PART II — APPLICATIONS ................... 60
```

Pipeline:

1. Tìm các trang `Contents` / `Table of Contents` hoặc tín hiệu tương đương.
2. Trích xuất lines và layout (font size, x-position, indentation, page-number markers, numbering).
3. Parse rule-based cho `Part`, `Chapter`, `1.1`, `1.2.1`, ...
4. Với sách không có đánh số/format rõ, dùng LLM để suy luận hierarchy có kiểm soát.
5. Chuẩn hóa thành structured JSON được kiểm tra bằng schema.
6. Đối chiếu title và vị trí với heading thật trong nội dung.
7. Các mục mơ hồ/có khả năng sai được gắn `needs_review`, không tự mặc định đúng.

### 4.4. Các vấn đề khó trong TOC

- PDF page index ≠ số trang in trên sách (ví dụ trang sách 1 nằm ở PDF page 13).
- Một heading trùng tên nhiều lần (`Introduction`, `Summary`).
- Một số chapter có tên nhưng không có numbering.
- Nội dung trong Part/Chapter xuất hiện **trước section đầu tiên**.
- Prologue, foreword, notes, appendix, footnotes có thể nằm ngoài TOC.
- Mục lục có cấp bị thiếu hoặc outline bị lỗi.
- Một heading bắt đầu giữa trang; page-only split dễ bỏ sót/lặp text.
- Có headings chỉ là tiêu đề trang/chạy đầu trang, không phải section thật.
- TOC đôi lúc có các sections không hiển thị trong nội dung hoặc tên được viết khác.

### 4.5. Output: normalized TOC tree

Mỗi node có tối thiểu:

```text
id
parent_id
type
raw_title
normalized_title
order_index
depth
children
source_anchor (nếu tìm được)
confidence
status
```

Các `type` khả dụng: `part`, `chapter`, `section`, `subsection`, `scene`, `topic`, `prologue`, `epilogue`, `introduction`, `appendix`, `front_matter`, `other`. Đây là taxonomy linh hoạt, không buộc mọi node phải thuộc mọi cấp.

---

## 5. Workflow B — Canonical Book Map và chính xác hóa source spans

### 5.1. TOC tree chưa đủ

Có TOC và page numbers chưa đồng nghĩa đã biết ranh giới chính xác của nội dung. Cần **align heading** với vị trí thực trong source text, sau đó gắn khoảng nội dung cho từng node/reading unit.

Ví dụ:

```text
Chapter 1 starts at PDF page 10
Section 1.1 starts at PDF page 11, block 3
Section 1.2 starts at PDF page 15, block 1
Chapter 2 starts at PDF page 24
```

Nội dung Section 1.1 là khoảng từ heading Section 1.1 đến ngay trước heading Section 1.2, **không nhất thiết trọn 4 trang**.

### 5.2. Dữ liệu địa chỉ nguồn

Ưu tiên anchor đủ chính xác:

```json
{
  "pdf_page_index": 10,
  "block_index": 3,
  "char_offset": 52
}
```

Trong hệ thống vững hơn có thể dùng **global text offsets** trên chuỗi văn bản chuẩn hóa và mapping ngược về page/block. Source interval dùng dạng **`[start, end)`**: bao gồm start, không bao gồm end.

Lưu ý: thứ tự block trả về từ parser và offsets có thể thay đổi khi đổi parser/version; nên có `source_version` và test tính ổn định.

### 5.3. Thuật toán mapping

1. Lấy các TOC headings có thứ tự.
2. Tìm candidate heading trong full text theo title/normalization/layout.
3. Rerank candidates bằng vị trí gần page đã biết, thứ tự trước-sau, typography và context.
4. Chọn anchors đáng tin cậy; nếu không rõ thì flag review.
5. Sắp xếp anchors theo thứ tự đọc thực tế.
6. Gắn đoạn nguồn từ một anchor đến anchor tiếp theo, không tạo gap/overlap.
7. Xử lý đoạn **intro** của chapter trước section đầu tiên như một unit riêng nếu có text.
8. Parent nodes có span tổng hợp của descendants; không copy text parent và child rồi narrate hai lần.
9. Kiểm tra completeness trên **narratable body**, đồng thời phân loại phần bị chủ động loại (copyright notice, index, bibliography, notes...) theo policy.

### 5.4. `book_map` mẫu

> Mẫu dữ liệu minh họa — không lấy từ cuốn sách thật.

```json
{
  "book_id": "book_001",
  "title": "Example Book",
  "source_format": "pdf",
  "source_version": "sha256:...",
  "structure_version": 1,
  "nodes": [
    {
      "id": "part_01",
      "parent_id": null,
      "type": "part",
      "title": "Foundations",
      "order_index": 0,
      "depth": 1,
      "children": ["ch_01"]
    },
    {
      "id": "ch_01",
      "parent_id": "part_01",
      "type": "chapter",
      "title": "Introduction",
      "order_index": 1,
      "depth": 2,
      "source_span": {
        "start": {"pdf_page_index": 9, "char_offset": 0},
        "end": {"pdf_page_index": 23, "char_offset": 0}
      },
      "children": ["ch_01_intro", "sec_01", "sec_02"]
    },
    {
      "id": "sec_01",
      "parent_id": "ch_01",
      "type": "section",
      "title": "The Core Idea",
      "order_index": 3,
      "depth": 3,
      "source_span": {
        "start": {"pdf_page_index": 10, "char_offset": 150},
        "end": {"pdf_page_index": 14, "char_offset": 800}
      },
      "content_ref": "content/sec_01.txt",
      "summary_ref": "summaries/sec_01.json",
      "children": [],
      "alignment_status": "verified"
    }
  ]
}
```

**`order_index`** là thứ tự toàn cục của nodes, không phải số chapter trong sách. **`parent_id`** xác định đúng hierarchy, kể cả khi sách có số cấp khác nhau. Các ID nên bền vững trong cùng một phiên bản `book_map`.

### 5.5. Tree view vs. flat reading queue

Cần **hai representation**:

**A. Hierarchical tree** phục vụ hiểu ngữ cảnh:

```text
Book
 └─ Part I
    └─ Chapter 1
       ├─ Chapter introduction
       ├─ Section 1.1
       └─ Section 1.2
```

**B. Ordered reading units** phục vụ xử lý tuyến tính:

```text
unit_001 -> Chapter introduction
unit_002 -> Section 1.1
unit_003 -> Section 1.2
unit_004 -> Chapter 2 introduction
unit_005 -> Section 2.1
...
```

**Reading unit** là **đơn vị nguồn có thể được consume**. **Episode** là **đơn vị nội dung video được tạo**. Không nhất thiết 1:1:

- Một section ngắn có thể đi chung với section kế tiếp.
- Một section dài có thể chia thành 2–5 episode.
- Một chapter có introductory paragraphs cần được cover trước Section 1.
- Chia episode phải tuân thủ coverage interval, không được tự nhảy phần.

### 5.6. Các invariants bắt buộc

- Graph của `book_map` hợp lệ: không cycle, không orphan, parent-child nhất quán.
- Source anchors phải có thứ tự, không vượt bounds.
- Các reading units tạo ra một **phân hoạch không trùng lặp** trên vùng nội dung được chọn để narrate.
- Không có gap không giải thích được (trừ phạm vi đã chủ động excluded và có log).
- Có chính sách rõ với footnotes, tables, illustrations, appendices, bibliographies, foreword.
- Nếu parser có uncertainty đáng kể, dừng để review thay vì tiếp tục sinh sai thứ tự.

---

## 6. Workflow C — Knowledge Preparation: summaries phân cấp

### 6.1. Vì sao cần summary khi đã lưu text gốc?

Text gốc dùng để viết script trung thành với nguồn, nhưng không nên nhét **toàn bộ sách** vào mỗi request. Summaries giúp giữ bức tranh toàn cảnh và mối liên hệ giữa các phần với chi phí thấp hơn.

Hierarchy:

```text
              BOOK SUMMARY
             /             \
       CHAPTER SUMMARY   CHAPTER SUMMARY
        /       \             /      \
    SECTION   SECTION      SECTION  SECTION
      |          |            |        |
   Full Text  Full Text     Full Text Full Text
```

Summary phải tạo theo hướng **bottom-up**:

1. Extract/lưu **full section content**.
2. Sinh **section summary** từ full content.
3. Sinh **chapter summary** từ tất cả section summaries và source bổ sung khi cần.
4. Sinh **book summary** từ chapter summaries, outline, và source evidence quan trọng.
5. Lưu traceability summary → source chunk/span, để kiểm tra những ý được tóm tắt có căn cứ.

### 6.2. Section summary nên có cấu trúc

Không chỉ dùng một đoạn `summary_text`. Ví dụ:

```json
{
  "section_id": "sec_01",
  "short_summary": "Tổng quan nội dung chính của section.",
  "key_concepts": [
    {
      "name": "Concept A",
      "definition": "Định nghĩa của concept A",
      "source_chunk_ids": ["chunk_001"]
    }
  ],
  "main_arguments": [
    {"claim": "Luận điểm 1", "source_span_ids": ["span_007"]}
  ],
  "events": [],
  "characters": [],
  "important_examples": [
    {"description": "Ví dụ trong phần này", "source_span_ids": ["span_008"]}
  ],
  "cross_references": ["sec_07"],
  "open_questions": [],
  "summary_model_version": "to_be_selected"
}
```

Schema có thể được điều chỉnh cho **fiction vs. non-fiction**:

- **Fiction:** nhân vật, biến cố, động cơ, quyết định, bối cảnh, thời gian, quan hệ, bí mật, foreshadowing.
- **Non-fiction:** luận điểm, khái niệm, ví dụ, bằng chứng, giả định, định nghĩa, mối liên hệ nhân-quả.
- **Reference/thematic books:** chủ đề, các mục con, trích dẫn/citation, cross-topic relationships.

### 6.3. Chapter summary

Từ các sections:

- Chapter objective/central idea.
- Những luận điểm hoặc cốt truyện chính.
- Progression của chapter (điểm đầu → phát triển → điểm kết).
- Những concepts và entities xuất hiện/phát triển.
- Những ví dụ/sự kiện then chốt.
- Quan hệ với chapters trước/sau.
- Các fact cần giữ nhất quán khi chuyển thể.

Không nên nối máy móc các section summaries; chapter summary phải **tổng hợp mạch logic** và có thể xem lại source gốc để tránh lỗi do tóm tắt tầng dưới.

### 6.4. Book summary

Tạo từ toàn bộ outline, chapter summaries và evidence khi cần:

- Central premise / central thesis.
- High-level narrative arc hoặc argument progression.
- Main themes.
- Main entities / characters / concepts.
- Terminology/glossary.
- Long-range relationships giữa chapters.
- Voice/tone observations của tác phẩm (để định hướng chuyển thể, không bắt chước nguyên văn).
- Kết cấu prologue → body → epilogue, nếu có.
- Những fact bất biến toàn sách.

**Giới hạn:** Summary là metadata/context **có thể sai**, không phải chân lý. Nếu có bất đồng, **source text ưu tiên**.

### 6.5. Chất lượng summary

Kiểm tra:

- Grounded: assertions quan trọng có `source_span_ids`.
- Coverage: không bỏ các ý/sự kiện quan trọng.
- Hallucination: không thêm chi tiết không có trong sách.
- Temporal order: đặc biệt với fiction, timeline không bị đảo.
- Consistency: cùng concept/nhân vật có cùng identity.
- Versioning: khi thay source/book_map phải invalidate summaries liên quan.

---

## 7. Workflow D — Chunking, embeddings và retrieval

### 7.1. Embeddings làm gì?

Embedding biến đoạn văn thành vector để tìm ngữ cảnh **theo ý nghĩa**, ví dụ:

- Section hiện tại nhắc một thuật ngữ đã định nghĩa ở Chapter 2.
- Nhân vật xuất hiện lại sau 100 trang.
- Một lập luận sau liên hệ tới ví dụ trước.
- Cần tìm chính xác passages liên quan trước khi narrator viết.

**Embeddings không lưu trọn “ký ức hiểu sách” theo cách LLM tự động hiểu hết mọi quan hệ.** Chúng là chỉ mục truy tìm; text, summaries, facts và state vẫn phải được lưu riêng.

### 7.2. Semantic chunks

Chunk theo cấu trúc tài liệu, không chỉ cắt mỗi N tokens:

```text
Book
  └─ Chapter
      └─ Section
          ├─ Paragraph group / Chunk 1
          ├─ Paragraph group / Chunk 2
          └─ Paragraph group / Chunk 3
```

Starting configuration **để thử nghiệm, chưa chốt**:

- Khoảng **500–1.000 tokens/chunk**.
- Có thể overlap **50–100 tokens** nếu phù hợp.
- Giữ `book_id`, `chapter_id`, `section_id`, `reading_unit_id`, `chunk_index`, `source_span`.
- Không cắt đứt nguyên nhân–kết quả, dialogue hoặc câu/paragraph một cách vô tội vạ.
- Với đoạn dài, lưu cả text gốc và địa chỉ nguồn đủ chính xác để tái tạo toàn đoạn.

Ví dụ record:

```json
{
  "chunk_id": "chunk_00239",
  "book_id": "book_001",
  "chapter_id": "ch_03",
  "section_id": "sec_03_02",
  "reading_unit_id": "unit_017",
  "chunk_index": 2,
  "text": "Original source passage...",
  "source_start_offset": 14420,
  "source_end_offset": 15180,
  "embedding_model": "to_be_selected"
}
```

### 7.3. Nên embedding cái gì?

**Nhóm 1: raw text chunks** — phục vụ tìm chứng cứ, định nghĩa, ví dụ, tình tiết.

**Nhóm 2: section/chapter summaries (tùy chọn)** — phục vụ tìm vùng nội dung liên quan ở cấp cao, rồi drill-down vào raw passages.

Cho MVP: raw chunk embeddings **có thể là đủ**. Summary embeddings có thể thêm sau khi benchmark chứng minh lợi ích.

### 7.4. Quy tắc retrieval

**Không làm thế này:**

```text
User clicks NEXT -> vector similarity search
                 -> choose most similar section
                 -> generate narration
```

Vì section giống về nghĩa không nhất thiết là section tiếp theo.

**Làm thế này:**

```text
User clicks NEXT
   -> Progress Manager finds next unconsumed source interval
   -> Load ALL required raw content for that interval
   -> Load book + chapter summaries + previous episode memory
   -> Retrieve only relevant historical/related evidence via vectors
   -> Compose context for Writer
```

Nguồn truy xuất theo RAG cần có **metadata filters**, tối thiểu theo `book_id`. Nên ưu tiên passages trước phần hiện tại nếu script không được phép tiết lộ các nội dung về sau.

### 7.5. RAG + long context: mô hình lai

Thiết kế tổng quát đã chọn là **hybrid long-context + hierarchical RAG + persistent state**.

- **Long context:** đưa **đầy đủ nội dung phần đang xử lý** vào writer khi khả thi.
- **Hierarchical summaries:** cung cấp kiến thức tổng thể.
- **RAG:** lôi lại passages liên quan, tránh quên yếu tố cũ.
- **State:** lưu những phần đã narrate và continuity của tập trước.

Nếu reading unit quá dài để đưa hết vào một lần, chia nó thành **deterministic contiguous sub-ranges** và xử lý theo thứ tự; không dùng top-k retrieval để đại diện toàn bộ nội dung phần đó.

---

## 8. Workflow E — Context Builder

### 8.1. Nhiệm vụ

Context Builder ghép **đúng dữ liệu cần thiết** cho narration request hiện tại; không phải lấy toàn bộ sách.

Ví dụ khi cần tạo script của Section 3.2:

```text
REQUIRED / deterministic:
  1. Current source text: Section 3.2 (hoặc next sub-range)
  2. Book identity + book map path
  3. Chapter 3 summary
  4. Global book summary
  5. Previous approved episode summary + covered ranges

RETRIEVED / supplemental:
  6. Prior definition of relevant concepts
  7. Relevant earlier character/event facts
  8. Other supporting source passages

CONSTRAINTS:
  9. Narration style, language, target length
 10. POV / narrator identity / character knowledge state
 11. Source fidelity, spoiler boundary, coverage contract
```

### 8.2. Gợi ý `NarrationContext` schema

```json
{
  "book_id": "book_001",
  "episode_number": 7,
  "target_source": {
    "reading_unit_id": "unit_017",
    "start_offset": 0,
    "end_offset": 5200,
    "full_text_ref": "content/unit_017.txt"
  },
  "book_summary_ref": "summaries/book.json",
  "chapter_summary_ref": "summaries/ch_03.json",
  "previous_episode_summary_ref": "episodes/6/summary.json",
  "retrieved_evidence": [
    {"chunk_id": "chunk_0008", "reason": "earlier_definition"}
  ],
  "narration": {
    "language": "vi",
    "target_word_count": null,
    "tone": "educational_or_storytelling",
    "pov": "third_person_or_character_pov"
  }
}
```

> Nếu user chọn giọng kể nhân vật, cần thêm `pov_character_id`, `knowledge_cutoff`, và rules về điều nhân vật biết/không biết.

### 8.3. Context budget policy

Thứ tự ưu tiên dùng tokens:

1. Nội dung nguồn cần xử lý — **bắt buộc**.
2. Constraints/coverage instruction — **bắt buộc**.
3. Relevant chapter summary và continuity state.
4. Global summary nếu còn hữu ích.
5. Trích đoạn RAG liên quan, giới hạn top-k/tokens.

Không truncate source content một cách im lặng. Nếu vượt budget, chia source thành các sub-ranges liên tiếp rồi dùng state để tiếp tục.

---

## 9. Workflow F — Narration generation theo từng tập

### 9.1. Pipeline logic

```text
REQUEST: GENERATE NEXT
        |
        v
Progress Manager selects next source interval
        |
        v
Context Builder loads source + summaries + continuity + retrieval
        |
        v
Reader / Planner creates source-grounded coverage brief
        |
        v
Narrative Perspective Engine applies POV / voice constraints
        |
        v
Narrator / Writer produces video narration script
        |
        v
Verifier checks factual fidelity + coverage + continuity + POV
        |
        +-- fail -> revision (bounded attempts) -> reverify
        |
        v
Draft Episode (versioned, with citations/coverage)
        |
      User
    /      \
REGENERATE  APPROVE
                |
                v
        Commit progress atomically
                |
                v
        Next source interval / END
```

Đây là **logical pipeline**. Không bắt buộc mỗi hộp là một agent độc lập; có thể gom nhiều bước thành một hoặc nhiều LLM calls tùy benchmark.

### 9.2. Reader / Planner

Trước khi viết lời dẫn, Planner cần rút ra một **content brief**:

- Source range phải được cover.
- Ý chính/sự kiện bắt buộc phải giữ.
- Các ví dụ/đối thoại phù hợp để chuyển thể.
- Những mối quan hệ nhân-quả hoặc timeline.
- Các câu/chi tiết không nên thêm.
- Kết nối với tập trước.
- Kế hoạch phân đoạn để đạt target length.

Planner **không được biến việc tóm tắt thành bỏ qua một phần nguồn**. Nếu không thể cover hết trong episode hiện tại, phải xác định sub-range còn lại cho episode sau.

### 9.3. Narrator / Writer

Sinh output hướng tới **voiceover/video narration**:

- Lời nói tự nhiên, mạch lạc, phù hợp nghe thay vì đọc học thuật.
- Có cách mở và nối tập khi cần.
- Không làm lệch central meaning/events/arguments.
- Dùng cách kể và từ ngữ mới phù hợp mục đích chuyển thể.
- Không chèn fact ngoài nguồn như fact trong sách.
- Có thể đưa lời giải thích bổ sung, nhưng phải phân biệt với nội dung tác giả nếu yêu cầu.
- Có thể dùng các biến thể tone/POV/language có kiểm soát.

**Định dạng script cuối cùng chưa chốt:** raw text, Markdown, hoặc structured JSON có sections và source references.

### 9.4. Verifier

Kiểm tra:

1. **Fidelity:** không thêm sự kiện, kết luận, phát ngôn sai hoặc thông tin thiếu căn cứ.
2. **Coverage:** các ý/sự kiện trọng yếu của source range xuất hiện đủ.
3. **No duplication:** không tái kể source intervals đã approved.
4. **Continuity:** nhất quán terminology, nhân vật, các dữ kiện xuyên tập.
5. **Temporal order:** không đảo timeline ngoài ý đồ đã cấu hình.
6. **POV correctness:** nhân vật kể chuyện chỉ nói/biết những điều hợp lệ.
7. **Spoiler policy:** không tiết lộ sự kiện từ các phần sau khi chưa cho phép.
8. **Narration quality:** nghe tự nhiên, độ dài phù hợp.
9. **Traceability:** có thể map script/claims về `source_span_ids`.

Không chỉ dựa vào một LLM tự chấm. Các kiểm tra định lượng/định tính cần kết hợp: range coverage bằng code, structured claim/source checking, test trên sách mẫu, và human review.

### 9.5. State transitions

Đề xuất:

```text
NOT_STARTED
   |
   v
DRAFT_GENERATED -> REVIEW_REQUIRED
                       | \
                       |  +--> REGENERATE -> REVIEW_REQUIRED
                       |
                       v
                    APPROVED
                       |
                       v
                SOURCE_RANGE_COMMITTED
                       |
               NEXT or BOOK_COMPLETE
```

- **GENERATE** tạo draft nhưng **chưa thay đổi committed progress**.
- **REGENERATE/REWRITE** tạo version mới, vẫn chưa advance.
- **APPROVE** là bước commit vùng nguồn đã cover, update state và continuity summary.
- Tập đã approved nên có version immutable; thay đổi sau đó cần revision mới và định nghĩa lại quan hệ state.
- Nếu fail giữa chừng cần retry idempotent, không ghi duplicate episode.

---

## 10. POV / Narrative Perspective Engine — bổ sung quan trọng

### 10.1. Vì sao cần một lớp POV riêng?

Một cuốn sách có thể được viết ngôi thứ ba, nhưng video narration có thể muốn dùng **ngôi thứ nhất** từ một nhân vật: “Tôi bước vào căn phòng…” thay vì “Anh ấy bước vào căn phòng…”. Ngược lại, truyện ngôi thứ nhất có thể chuyển thành ngôi thứ ba.

Đổi các đại từ bằng string replace **không đủ** vì góc nhìn ảnh hưởng tới:

- **Ai đang kể?**
- **Người kể có mặt ở đâu?**
- **Người kể biết điều gì ở thời điểm câu chuyện đang diễn ra?**
- **Người kể có thể quan sát sự kiện nào?**
- **Các suy nghĩ nội tâm của nhân vật khác có trực tiếp khả dụng không?**
- **Tác phẩm có xen kẽ narrator/chapter POV không?**

### 10.2. Nguyên tắc kiến trúc

> **Book Map + Source Facts + Events + Timeline + Character Knowledge** là tầng **canonical**, độc lập với POV. **Narrator/POV** chỉ được áp dụng ở tầng **generation**.

```text
ORIGINAL BOOK TEXT
       |
       v
SOURCE FACTS / EVENTS / CHARACTERS / TIMELINE
       |
       +----> POV POLICY / SELECT NARRATOR
                        |
                        v
             POV-CONSTRAINED NARRATION
                        |
                        v
               KNOWLEDGE VERIFICATION
```

Nếu đổi POV, **không sửa hoặc overwrite source events**. Cùng một nội dung có thể được render thành nhiều phiên bản narrator, nhưng các sự kiện bất biến.

### 10.3. Canonical event representation (đề xuất)

```json
{
  "event_id": "event_0042",
  "source_span_ids": ["span_0181"],
  "time_order": 42,
  "participants": ["char_alex", "char_mina"],
  "location_id": "loc_03",
  "neutral_description": "Alex discovers the letter in the room.",
  "witnesses": ["char_alex"],
  "known_by": {
    "char_alex": {"from_event_order": 42, "basis": "direct_observation"},
    "char_mina": null
  }
}
```

Mẫu này chỉ mang tính minh họa. Có thể đơn giản hóa cho MVP.

### 10.4. `POVPolicy` đề xuất

```json
{
  "mode": "first_person_character",
  "narrator_character_id": "char_alex",
  "narration_tense": "past",
  "knowledge_cutoff": {
    "max_event_order": 42
  },
  "allow_future_spoilers": false,
  "allow_other_character_inner_thoughts": false,
  "uncertain_event_handling": "describe_as_inference_or_omit"
}
```

Cho **third-person omniscient**, policies có thể khác. Cho **limited third-person**, knowledge vẫn bị hạn chế theo focal character.

### 10.5. Ví dụ dễ hiểu

**Source fact:** Một nhân vật giấu chìa khóa trong ngăn kéo. Nhân vật kể chuyện chưa nhìn thấy sự việc.

- **Narrator toàn tri:** Có thể nói trực tiếp nhân vật kia giấu chìa khóa, nếu source tiết lộ.
- **Narrator ngôi thứ nhất, chưa biết:** **Không được** kể “Tôi biết cô ấy đã giấu chìa khóa”, trừ khi có nguồn chứng minh nhân vật đã biết ở thời điểm đó.
- **Narrator ngôi thứ nhất, sau này mới biết:** Có thể dùng framing “Mãi sau này tôi mới biết…” **chỉ khi** style và spoiler policy cho phép.

### 10.6. Sách đổi POV theo chapter

Một số truyện có narrator khác nhau theo chapters. `book_map` cần lưu metadata narrator/POV **theo từng node hoặc range** nếu nguồn có chuyển đổi:

```json
{
  "reading_unit_id": "unit_018",
  "source_narrator": "char_A",
  "target_pov": "preserve_source"
}
```

Không giả định cả sách có một narrator duy nhất. Với mục tiêu chuyển sang một POV cố định, cần có rule xử lý các cảnh ngoài hiểu biết nhân vật (omit/reframe/third-person interlude) và phải đánh giá đánh đổi với yêu cầu **không bỏ sót**.

### 10.7. Đánh đổi lớn cần quyết định

**Whole-book coverage** và **strict single-character POV** đôi khi **mâu thuẫn**: những cảnh nhân vật không chứng kiến không thể kể trực tiếp mà vẫn trung thực với ngôi kể. Giải pháp phải được định nghĩa rõ:

1. Chấp nhận narrator hồi tưởng có kiến thức được tiết lộ sau này, **nếu văn bản cho phép**.
2. Dùng đoạn third-person interlude có đánh dấu.
3. Chuyển sang multiple POV.
4. Không dùng strict POV cho các cảnh không thể biết, hoặc loại một số scene theo policy (điều này cần đồng ý vì ảnh hưởng coverage).

**Chưa chốt phương án sản phẩm**. Engine cần đủ linh hoạt để phát hiện conflict và báo rõ, không âm thầm hallucinate.

---

## 11. Progress Manager — thứ tự, coverage, resume

### 11.1. Khái niệm cốt lõi

Progress không chỉ là `current_chapter=3`. Vì 1 section có thể sinh nhiều tập, state nên lưu **content cursor**:

```json
{
  "book_id": "book_001",
  "project_id": "narration_001",
  "last_approved_episode_number": 6,
  "next_reading_unit_id": "unit_017",
  "next_source_offset": 5200,
  "approved_source_ranges": [
    {"reading_unit_id": "unit_016", "start": 0, "end": 4100},
    {"reading_unit_id": "unit_017", "start": 0, "end": 5200}
  ],
  "status": "in_progress"
}
```

**Invariant:** `next_*` luôn chỉ tới đoạn nguồn đầu tiên chưa được approved, theo thứ tự canon.

### 11.2. NEXT algorithm

```python
def generate_next(project_id):
    state = load_narration_state(project_id)
    target_range = first_unapproved_source_range(state)
    if target_range is None:
        return {"status": "book_complete"}

    context = build_context(target_range, state)
    brief = plan_narration(context)
    draft = generate_narration(brief, context)
    report = verify_narration(draft, context)

    return save_draft_without_advancing(
        project_id, draft, target_range, report
    )


def approve_draft(project_id, draft_id):
    draft = load_draft(draft_id)
    assert draft.project_id == project_id
    assert draft.verification_status == "passed"
    assert source_range_is_next(draft.source_range, project_id)

    # transaction: commit episode, mark covered source, advance cursor
    return commit_approved_episode_and_cursor(draft)
```

Pseudocode, không phải API đã triển khai.

### 11.3. Idempotency và versioning

- `generate_next()` gọi lại không được commit một source range hai lần.
- Có thể giữ nhiều draft versions cho cùng episode.
- `APPROVE` phải atomic: lưu episode + coverage + progress trong cùng transaction.
- Nếu người dùng đổi target POV/tone trong các tập giữa chừng, cần ghi configuration version.
- Nếu book file được cập nhật hoặc sửa book_map, phải re-align spans và invalidate artifacts có thể bị ảnh hưởng.

### 11.4. Episode output schema (đề xuất)

```json
{
  "episode_id": "ep_007",
  "episode_number": 7,
  "status": "draft",
  "title": "Episode 7 - ...",
  "target_pov": "first_person_character",
  "target_language": "vi",
  "covered_source_ranges": [
    {"reading_unit_id": "unit_017", "start": 5200, "end": 9000}
  ],
  "script": "... narration text ...",
  "script_sections": [
    {"kind": "body", "text": "...", "source_span_ids": ["span_091"]}
  ],
  "episode_summary": "...",
  "verification_report_ref": "reports/ep_007.json",
  "previous_episode_id": "ep_006",
  "version": 1
}
```

### 11.5. When is the book complete?

Sách hoàn thành khi:

- Không còn unapproved source intervals trong phạm vi nội dung đã chọn.
- Tất cả episodes trong chuỗi cuối cùng đã approved.
- Coverage ledger không có gap và không có overlap không được cho phép.
- Các exceptions/excluded contents được liệt kê rõ.

Không nên kết thúc chỉ vì LLM nói “The End”.

---

## 12. Data model / Database đề xuất

### 12.1. Core tables

| Table | Dữ liệu cần lưu | Ghi chú |
|---|---|---|
| `books` | metadata, file checksum, source version, processing status | 1 sách |
| `book_nodes` | TOC tree, parent, depth, order, anchors | canonical map |
| `source_spans` | text intervals và page/block mapping | provenance |
| `reading_units` | linear, narratable partitions, source range | order/cursor |
| `text_chunks` | semantic chunks + metadata | full text references |
| `embeddings` | vectors + model/version + chunk ref | semantic retrieval |
| `section_summaries` | structured content, concepts/events | lower-level memory |
| `chapter_summaries` | synthesis and continuity | mid-level memory |
| `book_summaries` | book-level thesis/arc/glossary | global memory |
| `entities` | nhân vật/concepts/locations (optional) | normalized references |
| `events` | canonical events + timeline/knowledge (optional) | POV-safe memory |
| `narration_projects` | per-book narration configurations | multiple outputs/book |
| `episodes` | episode number, status, approved version | progression |
| `episode_versions` | generated drafts, scripts, verifier results | regenerate |
| `coverage_ranges` | approved intervals with episode link | no gaps/overlaps |
| `progress_state` | next unit/offset, last approved | resume |
| `processing_jobs` | pipeline stage, errors, retries, timestamps | operational |

**Tối giản MVP:** có thể gộp một số tables và dùng JSONB. Quan trọng nhất là logic integrity của `book_nodes`, `reading_units`, `coverage_ranges`, `episodes`, `progress_state`.

### 12.2. Source-of-truth hierarchy

1. Original file / normalized source text + stable spans.
2. Canonical `book_map` + `reading_units`.
3. Approved coverage ledger + immutable episode versions.
4. Derived summaries, embeddings, event graphs (có thể regenerate).
5. Generated drafts (không dùng làm source truth cho sách).

### 12.3. Invalidation / dependency graph

```text
Changed original text
    -> invalidate affected spans/map alignments
    -> rebuild affected reading units
    -> rebuild chunks/embeddings
    -> rebuild affected summaries
    -> recheck downstream episode evidence/coverage
```

Nếu chỉ đổi narration tone/POV mà không sửa source, không cần rebuild toàn bộ summaries/embeddings.

---

## 13. API và giao diện tương tác đề xuất

### 13.1. Minimal API

| Method | Endpoint (proposal) | Tác dụng |
|---|---|---|
| `POST` | `/books` | Upload text-based book |
| `POST` | `/books/{id}/process` | Parse TOC, align, build knowledge |
| `GET` | `/books/{id}/map` | Xem hierarchy + status |
| `GET` | `/books/{id}/reading-units` | Xem reading order |
| `GET` | `/books/{id}/summaries` | Xem section/chapter/book summaries |
| `POST` | `/narration-projects` | Tạo project với style/POV/target length |
| `POST` | `/projects/{id}/episodes/next` | Generate draft kế tiếp |
| `POST` | `/projects/{id}/episodes/{episode_id}/regenerate` | Viết lại draft |
| `POST` | `/projects/{id}/episodes/{episode_id}/approve` | Commit coverage + advance |
| `GET` | `/projects/{id}/progress` | Current unit/offset, coverage |
| `GET` | `/projects/{id}/episodes` | Danh sách script đã tạo |

Các endpoint trên là **đề xuất API**, chưa phải API đã tồn tại.

### 13.2. Giao diện tối thiểu

**Book View:** upload, processing status, tree/TOC, số section, warnings, coverage map.

**Narration View:** target POV/voice/language/length, current source range, Generate Next, Regenerate, Approve, script preview, source references.

**Progress View:** approved episodes, phần đã cover, phần còn lại, resume, book complete, lỗi/needs_review.

---

## 14. Đề xuất stack kỹ thuật

| Layer | Lựa chọn đề xuất | Vì sao |
|---|---|---|
| Language | Python | Phù hợp PDF parser, LLM pipelines |
| API | FastAPI | Schema, async API, dễ tích hợp |
| Native PDF parsing | PyMuPDF | Outline + text + layout |
| TOC normalization | Python rules + LLM structured output + Pydantic | Cân bằng deterministic/inference |
| Canonical book tree | Custom code / relational DB | Kiểm soát thứ tự và hierarchy |
| Knowledge indexing | LlamaIndex (optional) | Chunking, indexing, retrieval |
| Embeddings | Chưa chọn model | Benchmark nhiều lựa chọn |
| Main LLM | Chưa chọn model | Chọn theo chất lượng, context/cost |
| DB | PostgreSQL | State, integrity, transactions |
| Vector DB | pgvector trên PostgreSQL | Không cần thêm DB riêng cho MVP |
| Orchestration | LangGraph (optional) | Stateful transitions / verification loop |
| Queue/job runner | Optional future | Book processing có thể dài |
| Tests/observability | pytest + structured logs/tracing | Correctness và debugging |

**Không nên dùng framework phức tạp chỉ vì có sẵn.** Module Tree Builder, Span Alignment và Progress Cursor là deterministic core. Các bước LLM nên có structured outputs, bounded retries, schema validation và logging.

---

## 15. Source repository layout đề xuất

```text
book-to-video-ai/
├── app/
│   ├── api/
│   │   ├── books.py
│   │   ├── book_map.py
│   │   ├── narration_projects.py
│   │   └── episodes.py
│   │
│   ├── ingestion/
│   │   ├── pdf_text_extractor.py     # text PDF ONLY
│   │   ├── toc_discovery.py
│   │   ├── toc_parser.py
│   │   └── heading_alignment.py
│   │
│   ├── book_structure/
│   │   ├── schemas.py
│   │   ├── book_map_builder.py
│   │   ├── source_span_mapper.py
│   │   ├── reading_unit_builder.py
│   │   └── validators.py
│   │
│   ├── knowledge/
│   │   ├── section_summarizer.py
│   │   ├── chapter_summarizer.py
│   │   ├── book_summarizer.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── retriever.py
│   │   └── entity_event_index.py    # optional
│   │
│   ├── narration/
│   │   ├── context_builder.py
│   │   ├── coverage_planner.py
│   │   ├── pov_engine.py
│   │   ├── narrator.py
│   │   ├── verifier.py
│   │   ├── script_formatter.py
│   │   └── progress_manager.py
│   │
│   ├── workflows/
│   │   ├── book_processing.py
│   │   └── episode_generation.py
│   │
│   ├── db/
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── session.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── llm_client.py
│   │   └── logging.py
│   │
│   └── main.py
│
├── data/
│   ├── books/
│   ├── normalized_text/
│   ├── book_maps/
│   ├── summaries/
│   ├── scripts/
│   └── evals/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── evals/
│
├── docs/
│   ├── architecture.md
│   ├── book_map_schema.md
│   ├── progress_and_coverage.md
│   └── pov_policy.md
│
├── pyproject.toml
├── .env.example
└── README.md
```

**Chú ý:** Đây là **bản đề xuất cấu trúc source**, không phải mô tả một repo đã tạo.

---

## 16. End-to-end pseudocode

### 16.1. Book preparation — chạy một lần trên mỗi phiên bản sách

```python
def process_book(source_file):
    # Current scope: native/extractable text, NOT OCR.
    raw_pages = extract_text_and_layout(source_file)
    toc = discover_and_parse_toc(source_file, raw_pages)

    tree = build_canonical_hierarchy(toc)
    tree = align_heading_anchors(tree, raw_pages)
    tree = assign_source_spans(tree, raw_pages)
    validate_tree_and_source_coverage(tree, raw_pages)

    units = flatten_narratable_reading_units(tree)
    validate_order_and_non_overlap(units)

    chunks = chunk_units(units)
    embedding_records = embed_chunks(chunks)

    section_summaries = summarize_sections(units)
    chapter_summaries = summarize_chapters(tree, section_summaries)
    book_summary = summarize_whole_book(tree, chapter_summaries)

    persist_all(
        book_map=tree,
        reading_units=units,
        chunks=chunks,
        embeddings=embedding_records,
        section_summaries=section_summaries,
        chapter_summaries=chapter_summaries,
        book_summary=book_summary,
    )
    return tree
```

### 16.2. Per-episode generation — chạy mỗi lần được yêu cầu

```python
def draft_next_episode(project_id):
    state = get_state(project_id)
    next_range = get_first_unapproved_range(state)
    if not next_range:
        return end_of_book_response()

    source_text = get_entire_target_range(next_range)
    memory = get_book_chapter_and_previous_episode_summaries(state)
    context_passages = retrieve_related_passages(
        state.book_id,
        source_text,
        spoiler_cutoff=next_range,
    )
    context = assemble_context(source_text, memory, context_passages, state)

    content_plan = build_source_grounded_coverage_plan(context)
    viewpoint_plan = apply_pov_policy(content_plan, state.pov_policy)
    script = write_narration(viewpoint_plan, context)
    report = verify_fidelity_coverage_continuity_pov(script, context)

    return save_draft(script, report, next_range)  # NO cursor advance


def approve_episode(project_id, draft_id):
    draft = get_draft(draft_id)
    validate_approval(draft, project_id)
    with db_transaction():
        save_approved_version(draft)
        record_approved_coverage(draft.covered_source_ranges)
        update_continuity_summary(draft)
        advance_progress_to_first_unapproved_range(project_id)
```

### 16.3. Quy trình người dùng

```text
1. Upload Book
2. Process Book
3. Inspect TOC / Book Map / any alignment warnings
4. Create Narration Project (language, POV, tone, size)
5. Click Generate Next
6. Read the generated narration + source/coverage report
7. Regenerate if needed OR Approve
8. Repeat Step 5 until all selected source intervals are covered
9. Export episode scripts / project manifest
```

---

## 17. Ví dụ minh họa dễ hiểu

Giả sử một sách có:

```text
Part I
  Chapter 1
    Section 1.1 (short)
    Section 1.2 (long)
  Chapter 2
    Section 2.1
```

Sau ingestion:

```text
Book Map:
  part_1 -> ch_1 -> sec_1_1, sec_1_2
         -> ch_2 -> sec_2_1

Reading units:
  unit_001 = Section 1.1, source [0, 2000)
  unit_002 = Section 1.2, source [0, 12000)
  unit_003 = Section 2.1, source [0, 4000)

Summaries:
  sec_1_1 -> one JSON summary
  sec_1_2 -> one JSON summary
  sec_2_1 -> one JSON summary
  ch_1 -> synthesized chapter summary
  ch_2 -> synthesized chapter summary
  book -> global summary

Embeddings:
  chunks from unit_001/unit_002/unit_003 with source offsets
```

Narration:

```text
EPISODE 1 -> unit_001 [0, 2000) -> APPROVED
EPISODE 2 -> unit_002 [0, 5000) -> APPROVED
EPISODE 3 -> unit_002 [5000, 9000) -> APPROVED
EPISODE 4 -> unit_002 [9000, 12000) -> APPROVED
EPISODE 5 -> unit_003 [0, 4000) -> APPROVED
BOOK COMPLETE
```

Episode 2 dùng:

```text
- Unit 002 exact source [0,5000)
- Summary of Chapter 1
- Global book summary
- Episode 1 continuity summary
- Retrieved definition from unit 001, if relevant
- Narration/POV rules
```

**Vì sao tốt hơn “summary → script” đơn thuần?** Vì engine có một coverage ledger rõ ràng: dù section dài tới đâu, mọi khoảng nguồn đã chọn đều được xử lý; summary chỉ giữ continuity chứ không tự ý quyết định bỏ những phần còn lại.

---

## 18. Testing / Evaluation strategy

### 18.1. Sách thử nghiệm đã từng được thảo luận

- **The Chronicles of Narnia — The Lion, the Witch and the Wardrobe**: gợi ý để kiểm thử fiction chapter sequence và chuyển ngôi kể từ third-person omniscient. Có khoảng **17 chapters** theo đề xuất trước; cần chọn edition để đối chiếu thực tế.
- **Treasure Island** của Robert Louis Stevenson: gợi ý kiểm tra **nhiều Part/Chapter và narrator thay đổi**. Bố cục thường có **6 parts, 34 chapters**; Chapters 16–18 có điểm nhìn/kể chuyện của Dr. Livesey, ngoài phần lớn góc kể của Jim. Cần xác minh edition đang dùng.
- **The Quotable Jung**: đã được nêu như sách tham khảo cấu trúc theo chủ đề; chỉ nên coi là một **candidate/illustration**, không mặc định có bản PDF quyền sử dụng.

> **Quyền sử dụng:** Ưu tiên sách public-domain trong phạm vi pháp lý liên quan, sách tự sở hữu bản quyền, sách có phép chuyển thể, hoặc bộ dữ liệu thử nghiệm tự tạo. Được quyền đọc/sở hữu một bản PDF không đồng nghĩa tự động có quyền công khai bản chuyển thể dài hoặc dựng video thương mại. Đặc biệt, không mặc định mọi edition/translation đều public domain.

### 18.2. Test TOC / book map

- Embedded outline đúng level.
- TOC text có numbering rõ.
- TOC text không numbering, dựa layout.
- Không có Part, chỉ có Chapters.
- Có Part/Chapter/Section lồng nhau.
- Heading trùng tên.
- Có chapter intro.
- PDF physical page khác printed page.
- Một trang có nhiều headings.
- Missing/misleading TOC entries.
- Appendix/footnotes/front matter.

### 18.3. Test coverage / progress

- Episode 1 approved → cursor tới interval sau.
- Draft chưa approved → cursor giữ nguyên.
- Regenerate 10 lần → không tăng coverage.
- Retry approval → không duplicate.
- Long section split → các sub-ranges liền mạch.
- Hoàn thành tất cả units → book complete.
- Các lần tạo script cách nhau nhiều phiên → continuity persisted.
- Update source/book_map → detect stale summaries/scripts.

### 18.4. Test POV

- Third-person → first-person: không thêm suy nghĩ nhân vật khác.
- Character chưa biết một sự kiện: không tiết lộ trong lời kể của nhân vật.
- Multi-POV chapter: preserve source POV hoặc apply selected policy có kiểm soát.
- Timeline/knowledge cutoff được tôn trọng.
- Chi tiết future được RAG retrieval tìm thấy nhưng **không** được spoiler trong script.
- Nếu source đoạn đó không thể kể strict POV, verifier phải flag thay vì hallucinate.

### 18.5. Evaluation metrics đề xuất

| Metric | Ý nghĩa | Cách kiểm tra |
|---|---|---|
| Structural accuracy | Tree/TOC khớp với sách | Gold map + spot review |
| Span alignment accuracy | Vị trí headings đúng | Gold anchors |
| Coverage completeness | Tỉ lệ nội dung đã chosen được cover | Interval arithmetic + semantic review |
| Duplicate coverage | Bao nhiêu source bị narrate lại | Coverage interval overlap |
| Source-grounded claim rate | Assertions có thể truy về source | Source-supported claim eval |
| Hallucination rate | Nội dung không có căn cứ | Claim checking + human review |
| POV leakage | Nhân vật biết điều không thể biết | Character knowledge tests |
| Continuity errors | Mâu thuẫn các tập | Rule + eval set |
| Narration quality | Tự nhiên, dễ nghe, mạch lạc | Human/rubric scoring |
| Cost per book/episode | Token, embedding, model costs | Usage logs |
| Latency per episode | Thời gian sinh và verify | Timing instrumentation |

**Quan trọng:** “100% coverage intervals” về code **không tự chứng minh** rằng narration giữ đủ mọi ý quan trọng. Cần semantic coverage evaluation riêng.

---

## 19. MVP roadmap đề xuất theo thứ tự thực hiện

### Phase 1 — Book Structure MVP (**ưu tiên số 1**)

- [ ] Input một **text PDF**.
- [ ] Extract pages + layout metadata.
- [ ] Parse embedded TOC hoặc textual TOC.
- [ ] Build generic hierarchy tree.
- [ ] Align headings với source text.
- [ ] Generate normalized `book_map.json`.
- [ ] Flatten ordered `reading_units`.
- [ ] Coverage/overlap/order validations.
- [ ] Xuất một manifest dễ đọc để kiểm tra thủ công.

**Acceptance:** Sách thử nghiệm có full ordered reading units đúng, không trùng, không mất intro/body đã chọn.

### Phase 2 — Knowledge Preparation

- [ ] Lưu text/source spans.
- [ ] Tạo section summaries dạng structured JSON.
- [ ] Tạo chapter summaries.
- [ ] Tạo book summary.
- [ ] Chunking boundary-aware.
- [ ] Embed raw chunks + lưu metadata.
- [ ] Thiết lập retrieval theo `book_id` và source provenance.
- [ ] Đánh giá summary grounding.

**Acceptance:** Từ một section có thể lấy full text, ancestors, summaries và related evidence; provenance luôn tồn tại.

### Phase 3 — Sequential Narration MVP

- [ ] Persistent narration project + episode config.
- [ ] `Generate Next` chọn đúng source interval theo cursor.
- [ ] Context Builder ghép source + summaries + continuity + retrieval.
- [ ] Reader/Planner tạo coverage brief.
- [ ] Narrator tạo script.
- [ ] Verifier đánh giá nguồn, coverage, consistency.
- [ ] Draft versioning, Regenerate, Approve.
- [ ] Coverage ledger và state commit atomic.
- [ ] Xử lý sections dài bằng contiguous sub-ranges.

**Acceptance:** Có thể tạo nhiều scripts liên tiếp, resume sau khi restart, không nhảy/bỏ/trùng source do workflow.

### Phase 4 — POV and Story Intelligence

- [ ] Phân loại fiction vs non-fiction / multi-narrator.
- [ ] Extract canonical events, characters, timeline khi cần.
- [ ] Character knowledge tracking.
- [ ] POV policies: preserve-source, third-person, first-person-character, limited POV.
- [ ] POV-aware prompting và verification.
- [ ] Detect conflict giữa strict POV và full coverage.

**Acceptance:** Các scripts đổi POV mà không làm lộ thông tin nhân vật chưa biết hoặc sửa sự kiện bất biến.

### Phase 5 — Production-hardening / extensions

- [ ] Hỗ trợ EPUB/DOCX khi cần (không phải OCR).
- [ ] Thêm human-review dashboard.
- [ ] Retry/backoff/circuit breakers/observability.
- [ ] Chi phí/token budget, caching, jobs.
- [ ] Batch processing nhiều sách.
- [ ] Export episode packs và metadata cho video-production pipeline.
- [ ] A/B testing prompts/models/evaluation.

---

## 20. Những quyết định mở cần chốt trước khi sản phẩm ổn định

| Câu hỏi | Vì sao quan trọng | Trạng thái |
|---|---|---|
| Mỗi tập tính theo số từ, phút, hay scene? | Điều khiển length và source coverage | Open |
| “Giữ core content” nghiêm tới mức nào? | Tóm tắt linh hoạt hay gần như đầy đủ chi tiết | Open |
| Default narrator/POV là gì? | Ảnh hưởng cả pipeline và verifier | Open |
| Có được tiết lộ nội dung các chapter tương lai? | Spoiler control và book memory | Open |
| Cách xử lý cảnh ngoài hiểu biết của POV character? | Xung đột coverage–POV | Open |
| Giữ hay bỏ footnotes, index, references, foreword? | Xác định vùng narratable | Open |
| Model nào cho mapping, summary, narrator, verifier? | Chất lượng/chi phí/latency | Open |
| Embedding model + DB indexing strategy? | Retrieval precision và chi phí | Open |
| RAG chunks chỉ quá khứ hay có thể cả tương lai? | Spoiler & inference leakage | Open |
| Bao nhiêu regeneration/verification attempts? | Cost & reliability | Open |
| Có cần manual approval cho từng episode? | Progress contract | Hiện thiết kế mặc định là có |
| Output schema cuối là Markdown, JSON hay cả hai? | Integrations cho video workflow | Open |
| Hỗ trợ nội dung có bản quyền ra sao? | Quyền chuyển thể/phát hành | Cần policy & source rights |
| Frontend hay API-first MVP? | Scope triển khai | Open |

---

## 21. Kiến trúc quyết định: tóm lại thật ngắn

**Cốt lõi sản phẩm là một dây chuyền 2 vòng đời.**

### Vòng đời 1 — Chuẩn bị sách (một lần / source version)

```text
Extract native text
  -> Read Table of Contents
  -> Build hierarchical Book Map
  -> Align headings to exact source spans
  -> Flatten to ordered reading units
  -> Validate no gaps/duplicates
  -> Generate section summaries
  -> Generate chapter summaries
  -> Generate book summary
  -> Chunk + embed source text
  -> Persist structure, knowledge, provenance
```

### Vòng đời 2 — Tạo narration (mỗi lần người dùng gọi)

```text
NEXT
  -> Get next unapproved source interval from Book Map + State
  -> Load complete target source content
  -> Load global/chapter/previous episode summaries
  -> Retrieve relevant context from embeddings (optional)
  -> Plan mandatory coverage
  -> Apply POV/narration style with knowledge restrictions
  -> Write video narration script
  -> Verify coverage/fidelity/continuity/POV
  -> Save DRAFT
  -> User REGENERATE or APPROVE
  -> On APPROVE, commit source coverage and advance cursor
  -> Repeat until BOOK_COMPLETE
```

### 5 nguyên tắc không được phá

1. **Order is deterministic:** thứ tự đọc do Book Map + cursor quyết định.
2. **Source is authoritative:** narration dựa trên source text, không phải summary hoặc embeddings riêng lẻ.
3. **Coverage is explicit:** mỗi đoạn nguồn đã chuyển thể có chứng cứ/ledger.
4. **POV is a rendering policy:** đổi góc kể không được đổi canonical events hoặc gán nhầm knowledge.
5. **State is persistent and approved:** draft/regenerate không làm tiến độ chạy sai.

---

## 22. Gợi ý bước tiếp theo thực tế

**Bước có giá trị cao nhất hiện tại là triển khai một `book_map` prototype** trên một sách có text và TOC rõ, xuất các file:

```text
outputs/<book_id>/
├── book_metadata.json
├── toc_raw.json
├── book_map.json
├── reading_units.json
├── source_coverage_report.json
└── content/
    ├── unit_001.txt
    ├── unit_002.txt
    └── ...
```

Sau đó kiểm tra **thứ tự, toàn vẹn content spans, intro/section boundary, coverage không trùng**. Chỉ khi bước này đúng, mới triển khai summaries, embeddings, narration và POV. Nếu book map sai, những tầng LLM phía sau rất khó khôi phục phần nguồn đã bị mất hoặc gán nhầm.

---

## 23. Glossary — Thuật ngữ thống nhất

| Thuật ngữ | Nghĩa trong dự án |
|---|---|
| **TOC** | Table of Contents, mục lục dùng nhận diện structure |
| **Book Map** | Cây nội dung chuẩn có node hierarchy, order, source anchors |
| **Source Span** | Khoảng vị trí chính xác trong text của tài liệu gốc |
| **Reading Unit** | Đơn vị nguồn tối thiểu được đưa vào hàng đợi xử lý tuyến tính |
| **Episode** | Một phần narration output; có thể bao phủ một phần hoặc nhiều units |
| **Coverage Ledger** | Danh sách các đoạn nguồn đã approved và episode tương ứng |
| **Cursor** | Vị trí nguồn chưa hoàn thành kế tiếp |
| **Hierarchical Summary** | Bộ nhớ nhiều cấp section/chapter/book |
| **Embedding** | Vector biểu diễn nghĩa, dùng tìm ngữ cảnh liên quan |
| **RAG** | Retrieval-augmented generation: bổ sung passages liên quan vào context |
| **Context Builder** | Chọn và ghép source, summaries, retrieval, state, constraints |
| **Source Brief** | Kế hoạch nội dung phải cover trước khi viết lời dẫn |
| **POV** | Point of view: góc nhìn/nhân vật kể chuyện |
| **Canonical Event** | Sự kiện nền tảng độc lập với ngôi kể được chọn |
| **Knowledge State** | Những gì một nhân vật được phép biết tại một thời điểm |
| **Verifier** | Bước đánh giá fidelity, coverage, continuity, POV |
| **Approved Episode** | Bản script chính thức có committed source coverage |
| **Book Complete** | Không còn nội dung thuộc scope mà chưa được approved |

---

## 24. Provenance của tài liệu này

Tài liệu là bản **hợp nhất các ý tưởng và thiết kế đã trao đổi trong dự án tính đến 14/10/2026**, bao gồm:

- Mục tiêu tổng thể: chuyển sách đầy đủ thành những narration scripts tuần tự, mỗi lần gọi tạo một phần.
- Thiết kế TOC-aware hierarchy, `book_map`, exact source alignment, reading units.
- Hierarchical summaries và embedding/retrieval phục vụ cross-chapter context.
- Stateful generation, approval, regeneration, continuity, full coverage.
- Ý tưởng bổ sung về **third-person ↔ POV conversion**, narrator knowledge, event invariants.

Nhiều bảng, code blocks, field names và kiến trúc module trong file này là **đề xuất cụ thể hóa để có thể bắt đầu implementation**, **không phải chứng nhận chúng đã được triển khai hoặc được người dùng chốt 100%**. Các ví dụ sách chỉ là candidates, không có nghĩa sách đã được upload, parse hay cấp phép sử dụng trong dự án.
