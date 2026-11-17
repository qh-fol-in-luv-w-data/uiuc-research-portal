# UIUC Research Portal & LLM Assistant — Design Spec

- **Ngày:** 2026-11-16
- **Nguồn yêu cầu:** `AOLTask.pdf` (Academic Online — Technical Assessment)
- **Trạng thái:** Chờ review (rev 2, 2026-11-17: sửa thứ tự embed/link, cách cắt dữ liệu, chốt tham số khởi đầu, thêm LLM rerank và mục finetune)

## 1. Mục tiêu

Xây một **single-page research portal** cho University of Illinois Urbana-Champaign (UIUC) cùng một **trợ lý LLM** trả lời câu hỏi về nghiên cứu gần đây, bài báo nổi bật và chuyên môn giảng viên.

Hai câu hỏi bắt buộc phải trả lời đúng:

1. "What are the most recent UIUC papers on AI in war conflict?"
2. "Which faculty members work on Computer Vision in Healthcare?"

Tiêu chí chấm (theo thứ tự ưu tiên): Software Engineering & UI/UX (chính) → LLM tooling & retrieval → API exploration (OpenAlex) → Domain adaptation (authorship, topics, affiliation).

### Ràng buộc đã chốt

| Hạng mục | Quyết định |
|---|---|
| LLM | Ollama chạy **trên host**; chat model mặc định `qwen3:4b` (cấu hình qua `OLLAMA_CHAT_MODEL`, có thể đổi `qwen3:8b`); embedding `bge-m3` (1024 chiều) |
| Stack | Next.js 15 (App Router, TypeScript, Tailwind, shadcn/ui, Recharts) + FastAPI (Python 3.11) |
| Lưu trữ | PostgreSQL 16 + pgvector (một DB cho quan hệ, full-text, vector) |
| Bàn giao | Repo + `docker compose up` chạy local + README + ảnh/video demo; kèm DB dump dựng sẵn |
| Ngoài phạm vi | Auth, deploy online, refresh dữ liệu theo lịch, UI đa ngôn ngữ |

## 2. Dữ liệu đầu vào — hiện trạng đã khảo sát

### 2.1 OpenAlex
- UIUC = `I157725225` (ROR `047426m28`).
- Filter `institutions.id:I157725225,from_publication_date:<today-2y>` → ~26.962 works; riêng `type:article` ~14.445.
- Chi phí: list request $0.0001/request (200 bản ghi/trang). Không key: quota chung $0.10/ngày/IP; có key miễn phí: $1/ngày. Toàn bộ ingest ~150 request ≈ $0.015 → chạy được không cần key; vẫn hỗ trợ `OPENALEX_API_KEY` (tùy chọn).
- **Không** dùng `search` endpoint theo từng giảng viên (≈$0.001/request × 1000 = vượt quota miễn phí).
- Có dữ liệu nhiễu: work có citation cao nhất (8.198) là bài tâm lý học tiếng Nga — nghi gán affiliation sai → cần bước làm sạch. Kiểm tra 2026-11-17: bài này có UIUC trong `institutions` và raw affiliation chứa "University of Illinois" → chỉ điều kiện outlier (b) bắt được.

### 2.2 Faculty CSV (`illinois-researchers.csv`)
- 1.000 dòng, cột `email, name, photo_url, position, keywords`.
- `keywords` là mảng Postgres literal `{"a b",c,...}`; 23–574 keyword/người (median 101); nhiễu (vd. "simon fraser university", "real world", "siam international conference").
- `photo_url = NULL` ở 105 người; 2 người thiếu `position`.
- **Không có** department, OpenAlex ID → phải tự liên kết với tác giả OpenAlex.

### 2.3 Institutional metadata
File `data/institution.json` soạn tay: tên, năm thành lập, địa điểm + tọa độ, số liệu cơ bản, mô tả ngắn, danh sách ảnh campus từ Wikimedia Commons (lưu URL + tác giả + license để ghi credit). Không dùng logo chính thức.

## 3. Kiến trúc

```
┌──────────────┐   HTTP/SSE   ┌──────────────┐   SQL    ┌─────────────────────┐
│ web (Next.js)│ ───────────▶ │ api (FastAPI)│ ───────▶ │ db (Postgres+pgvec) │
└──────────────┘              └──────┬───────┘          └─────────▲───────────┘
                                     │ HTTP                       │ writes
                                     ▼                            │
                          ┌─────────────────────┐       ┌─────────┴─────────┐
                          │ Ollama (host)       │◀──────│ ingest (Python CLI)│──▶ OpenAlex API
                          │ qwen3:4b · bge-m3   │ embed └───────────────────┘
                          └─────────────────────┘
```

- `web` gọi `api` qua REST; chat dùng SSE.
- Container truy cập Ollama qua `http://host.docker.internal:11434` (Docker trên macOS không dùng GPU Metal → Ollama phải chạy trên host).
- `ingest` là CLI chạy một lần (idempotent, có cache), không phải service thường trực.

### 3.1 Cấu trúc repo

```
apps/web/        Next.js app
apps/api/        FastAPI app (routers, services, db, llm)
ingest/          pipeline CLI (fetch, clean, link, embed, aggregate)
data/            illinois-researchers.csv, institution.json, synonyms.yaml, stoplist
db/              migrations SQL (schema + indexes), dump/
eval/            eval set (YAML) + runner
docs/            spec, plan, ảnh chụp màn hình
docker-compose.yml, Makefile, README.md, .env.example
```

## 4. Mô hình dữ liệu (Postgres)

| Bảng | Trường chính |
|---|---|
| `works` | `id` (OpenAlex W…), `doi`, `title`, `abstract`, `publication_date`, `type`, `language`, `cited_by_count`, `is_oa`, `oa_url`, `venue_name`, `primary_topic_id`, `is_outlier`, `tsv tsvector`, `embedding vector(1024)` |
| `authors` | `id` (A…), `display_name`, `orcid`, `works_count_in_set` |
| `authorships` | `work_id`, `author_id`, `position` (first/middle/last), `is_uiuc`, `raw_affiliation` |
| `institutions` | `id`, `display_name`, `country_code`, `type` (cho tổ chức hợp tác) |
| `work_institutions` | `work_id`, `institution_id` |
| `topics` | `id`, `display_name`, `subfield`, `field`, `domain` |
| `work_topics` | `work_id`, `topic_id`, `score` |
| `faculty` | `id`, `email`, `name`, `photo_url`, `position`, `keywords_raw text[]`, `keywords text[]` (đã làm sạch), `primary_field` (field xuất hiện nhiều nhất trong bài đã link; null nếu chưa link), `tsv`, `embedding vector(1024)` |
| `faculty_author_link` | `faculty_id`, `author_id`, `confidence` (0–1), `method` (exact/initials/disambiguated) |
| `stats_cache` | `key`, `payload jsonb`, `computed_at` (số liệu tổng hợp cho portal) |

Index: GIN trên `tsv`; HNSW (`vector_cosine_ops`) trên `embedding`; B-tree trên `publication_date`, `cited_by_count`; index khóa ngoại trên các bảng nối.

## 5. Pipeline ingest

Mỗi bước là một subcommand (`python -m ingest <step>`), idempotent; `make ingest` chạy tuần tự. Response OpenAlex được cache ra `ingest/.cache/` (JSONL theo trang) để chạy lại không tốn quota.

1. **fetch-works** — `/works` filter UIUC + 2 năm, chia thành lát theo tháng (cursor paging nay bắt buộc API key; page paging giới hạn 10.000 kết quả/truy vấn), `page=1..n`, `per_page=200`, `select` chỉ các trường cần; retry exponential backoff, đọc header `x-ratelimit-*`, dừng an toàn khi gần hết quota và resume được.
2. **clean-works**
   - Giữ `type ∈ {article, preprint, review, book-chapter}` và conference paper (theo `primary_location.source.type = conference`).
   - Loại `is_retracted`, `is_paratext`, thiếu title.
   - Dựng `abstract` từ `abstract_inverted_index`.
   - Gắn `is_outlier` khi: (a) không có authorship nào mà institution UIUC xuất hiện trong `institutions` của tác giả *và* raw affiliation không chứa "Illinois"; hoặc (b) ngôn ngữ ≠ en *và* `cited_by_count` thuộc top 1% của toàn tập. Outlier không xóa, chỉ bị loại khỏi thống kê "notable" và bị nhân hệ số 0.5 vào điểm tìm kiếm. Ghi số bài bắt được theo từng điều kiện vào `docs/data-quality.md` (điều kiện (a) có thể gần như không kích hoạt vì filter fetch đã yêu cầu UIUC; cần kiểm trên dữ liệu thật).
   - **Không** cắt top N theo citation (cắt theo citation loại trước tiên các bài mới, mâu thuẫn với câu hỏi "most recent"). Chỉ khi sau lọc vẫn > 25.000 bài mới cắt, và cắt theo `publication_date` mới nhất.
3. **load-faculty** — parse mảng Postgres bằng CSV reader; chuẩn hóa (lowercase, trim, gộp trùng); lọc nhiễu bằng `data/keyword_stoplist.txt` + heuristic (khớp tên tổ chức/hội nghị, cụm quá chung như "real world", "mathematics" khi người đó có >200 keyword…). Giữ cả `keywords_raw`.
4. **embed-profiles** (chạy *trước* link để tránh phụ thuộc vòng tròn với bước embed) — embed bằng `bge-m3`: (i) keyword sạch của từng giảng viên; (ii) hồ sơ topic của từng tác giả UIUC ứng viên (nối `display_name` các topic của bài họ đứng tên). Lưu ở `faculty.keyword_embedding` và bảng `author_profile`; chỉ embed cho các trường hợp có nhiều ứng viên trùng tên.
5. **link-faculty** — tập ứng viên = tác giả có `is_uiuc` trong authorships đã ingest.
   - Chuẩn hóa tên: bỏ dấu (unidecode), lowercase, bỏ dấu câu, tách first/middle/last.
   - Khớp theo thứ tự: exact full name → (first, last) bỏ middle → (first initial, last).
   - Nhiều ứng viên → chọn theo cosine(embedding keyword giảng viên, embedding hồ sơ topic của tác giả) từ bước embed-profiles; `confidence` = điểm nền theo phương pháp (exact 0.9, bỏ middle 0.75, initials 0.6) + thưởng/phạt theo biên độ chênh cosine giữa ứng viên 1 và 2; dưới 0.5 thì không link.
   - Báo cáo tỷ lệ link (kỳ vọng 70–85%) vào `docs/data-quality.md`.
6. **embed** — gọi Ollama `/api/embed` theo batch: work = `title + abstract` (cắt ~512 token); faculty = `name + keywords sạch + title 5 bài nổi bật đã link`. Bỏ qua bản ghi đã có embedding.
7. **aggregate** — tính và ghi `stats_cache`: KPI tổng, công bố theo tháng, phân bố type, tỷ lệ OA, cây field→subfield (đếm), top topic tăng nhanh (12 tháng gần nhất vs 12 tháng trước, tối thiểu N bài), top venue, top tổ chức hợp tác, top giảng viên theo số bài.
8. **dump** — `pg_dump` ra `db/dump/portal.sql.gz` để người chấm restore nhanh.

## 6. API (FastAPI)

| Endpoint | Mô tả |
|---|---|
| `GET /health` | Trạng thái DB, Ollama, model đã pull |
| `GET /api/overview` | KPI + thông tin trường |
| `GET /api/stats/{key}` | Số liệu tổng hợp từ `stats_cache` (trends, topics, venues, collaborators…) |
| `GET /api/works` | Danh sách bài: `q`, `field`, `sort=recent|cited|relevance`, `page` |
| `GET /api/faculty` | Danh sách/tìm giảng viên: `q`, `position`, `field`, `page` |
| `GET /api/faculty/{id}` | Hồ sơ: keyword sạch, link OpenAlex + confidence, bài gần đây, topics |
| `POST /api/chat` | SSE: events `plan` → `sources` → `token`* → `done` (hoặc `error`) |

Pydantic schema cho mọi request/response; lỗi trả JSON chuẩn `{error, detail}`. Tìm kiếm trong `/api/works` và `/api/faculty` dùng chung service hybrid search với chat.

## 7. Trợ lý LLM

### 7.1 Bước 1 — Query understanding
Ollama `/api/chat` với `format=<JSON schema>`, `think=false`, temperature thấp, few-shot ~6 ví dụ. Output:

```json
{
  "intent": "papers | faculty | both | out_of_scope",
  "standalone_question": "…",
  "concepts": [["ai", "machine learning", "autonomous weapons"], ["war", "armed conflict", "military"]],
  "date_from": "YYYY-MM-DD | null",
  "date_to": "YYYY-MM-DD | null",
  "sort": "recent | cited | relevance",
  "limit": 5
}
```

- `concepts` là danh sách **nhóm khái niệm** (AND giữa nhóm, OR trong nhóm). Được bổ sung từ `data/synonyms.yaml` (bảng đồng nghĩa domain nhỏ, vd. computer vision ↔ image analysis, medical imaging…).
- Câu hỏi nối tiếp: đưa 4 lượt gần nhất vào prompt để viết `standalone_question`.
- JSON lỗi/timeout → parser theo luật (tách cụm theo "on/in/about/and", từ khóa "recent/latest", "most cited"…).

### 7.2 Bước 2 — Retrieval (tất định)
**Papers:**
1. Ứng viên = top 200 FTS (`websearch_to_tsquery` từ OR các concept) ∪ top 200 vector (embedding của `standalone_question`); gộp bằng RRF (k=60).
2. Lọc nhóm khái niệm: mỗi nhóm phải thỏa (khớp FTS ≥1 từ trong nhóm) **hoặc** (cosine(work, embedding nhóm) ≥ ngưỡng τ). τ khởi đầu 0.55, hiệu chỉnh trên eval set (quét 0.45–0.70, bước 0.025).
3. Lọc ngày; nhân điểm RRF của outlier với 0.5.
4. **LLM rerank (tùy chọn, cờ `RERANK_ENABLED`, mặc định tắt cho tới khi eval chứng minh có lợi):** đưa top 20 sau lọc cho chat model, yêu cầu trả JSON `{id, relevant: bool, score 0–3}` theo lô; loại bài `relevant=false`, sắp lại theo `score` rồi RRF. Timeout 30s; quá hạn thì bỏ qua rerank.
5. Sắp theo `sort`: `recent` → theo `publication_date` trong tập đã qua lọc; `cited` → theo citation; `relevance` → theo RRF (hoặc điểm rerank nếu bật).

**Faculty:** điểm = w1·(keyword khớp, có IDF) + w2·cosine(faculty embedding, query) + w3·(số bài liên quan trong top-K paper mà giảng viên là tác giả qua `faculty_author_link`).
- IDF = `log(N_faculty / df)`, df = số giảng viên có keyword đó. Mỗi thành phần chuẩn hóa min–max về 0–1 trên tập ứng viên trước khi cộng.
- Trọng số khởi đầu w1 = 0.4, w2 = 0.3, w3 = 0.3; K = 50. Hiệu chỉnh bằng grid search trên eval set (tổng w = 1, bước 0.1).
- Mỗi kết quả kèm `evidence`: keyword khớp + 1–3 bài liên quan.

Mọi tham số (τ, w1–w3, K, hệ số outlier, k của RRF) nằm trong `apps/api/config/retrieval.yaml`; `make tune` chạy grid search và ghi bộ tốt nhất cùng bảng kết quả vào `eval/tuning-report.md`. **Chống overfit:** eval set chia `tune` (~70%) và `holdout` (~30%); chỉ tune trên `tune`, báo cáo cả hai.

`intent = both` chạy cả hai; `out_of_scope` bỏ qua retrieval và trả lời lịch sự rằng trợ lý chỉ hỗ trợ về nghiên cứu UIUC.

### 7.3 Bước 3 — Generation
- Context = danh sách nguồn đánh số `[1]…[n]` (title, năm, venue, tác giả UIUC, 1–2 câu abstract; hoặc tên, chức danh, keyword khớp, bài bằng chứng).
- System prompt: chỉ dùng nguồn đã cho, trích dẫn `[n]`, không có nguồn phù hợp thì nói không tìm thấy, trả lời ngắn gọn bằng ngôn ngữ người hỏi.
- Hậu kiểm: loại `[n]` không tồn tại trước khi gửi event `done`.
- UI: event `sources` hiển thị thẻ kết quả ngay; `token` stream câu trả lời.

### 7.4 Evaluation
`eval/queries.yaml` ~40 câu (gồm 2 câu bắt buộc) với `expected_ids` (works hoặc faculty) gán nhãn sau khi xem dữ liệu, chia `tune`/`holdout`. `make eval` báo: tỷ lệ JSON hợp lệ ở bước 1, precision@5, recall@10, tỷ lệ citation hợp lệ, latency. Ma trận so sánh đưa vào README: `qwen3:4b` few-shot · `qwen3:4b` + rerank · `qwen3:8b` few-shot · (nếu có) bản finetune §13.

## 8. Giao diện

Single page, Tailwind + shadcn/ui, tông cam/navy Illinois, dark mode, responsive. Các section (có anchor nav dính trên cùng):

1. **Hero** — ảnh campus, tên, tagline; 4 KPI (công bố 2 năm, tổng citation, số giảng viên, số tổ chức hợp tác).
2. **Research Focus Areas** — treemap field→subfield; click để set filter field toàn trang; danh sách "rising topics".
3. **Scholarly Output** — line chart công bố theo tháng; donut type; tỷ lệ OA; top venues.
4. **Notable Publications** — tab Most cited / Most recent, lọc theo field; hiển thị tác giả UIUC (link sang drawer giảng viên), venue, DOI/OpenAlex link.
5. **Faculty Expertise** — ô tìm (hybrid search), filter position/field, lưới thẻ (avatar initials khi thiếu ảnh); drawer hồ sơ với keyword sạch, bài gần đây, topics, badge confidence của link OpenAlex.
6. **Collaboration & Campus** — bản đồ Leaflet (OSM tiles), top tổ chức đối tác, thông tin trường + credit ảnh.
7. **AI Research Assistant** — khung chat inline + nút nổi mở panel ở mọi vị trí; câu gợi ý (gồm 2 câu bắt buộc); hiển thị thẻ nguồn và câu trả lời có trích dẫn click được.

Dữ liệu tổng hợp được SSR (fetch có revalidate); search/chat chạy client-side. Mọi khối có skeleton, empty state, error state; chat hiển thị "Assistant offline" khi `/health` báo Ollama không sẵn sàng.

## 9. Xử lý lỗi

- Ollama không chạy / thiếu model → `/api/chat` trả 503 kèm hướng dẫn (`ollama pull qwen3:4b bge-m3`); portal vẫn hoạt động.
- Timeout từng bước LLM (query understanding 20s, generation 90s); query understanding lỗi → parser theo luật.
- Search vẫn chạy được nếu embedding query lỗi (chỉ dùng FTS, ghi log cảnh báo).
- Ingest: retry/backoff, resume từ cache, dừng khi gần hết quota OpenAlex và in hướng dẫn thêm `OPENALEX_API_KEY`.

## 10. Kiểm thử

- **Backend (pytest):** parse keyword mảng Postgres; dựng abstract từ inverted index; chuẩn hóa & khớp tên (middle name, initials, dấu); RRF; lọc nhóm khái niệm; parser dự phòng; router API với DB test (Postgres container) và Ollama giả lập.
- **Frontend:** Vitest + Testing Library cho component chính (chat message có citation, faculty card, filter); Playwright e2e: tải trang → tìm giảng viên → mở drawer → gửi chat (API chat mock).
- **Mock test hệ thống:** fixture dữ liệu nhỏ (~200 works, ~50 faculty dựng từ dữ liệu thật đã ẩn danh hóa nếu cần) nạp vào Postgres test; Ollama giả lập trả JSON/embedding cố định; kiểm thử end-to-end `/api/chat` cho 2 câu bắt buộc (event order `plan → sources → token* → done`, citation hợp lệ) và các nhánh lỗi (Ollama 503, JSON hỏng → parser luật, embedding lỗi → chỉ FTS).
- **Eval LLM:** như §7.4.

## 11. Đóng gói & bàn giao

- `docker-compose.yml`: `db` (pgvector/pgvector:pg16), `api`, `web`; healthcheck; volume cho DB.
- `Makefile`: `up`, `ingest`, `restore` (từ dump), `test`, `eval`, `tune`, `finetune` (tùy chọn).
- `.env.example`: `DATABASE_URL`, `OLLAMA_URL`, `OLLAMA_CHAT_MODEL=qwen3:4b`, `OLLAMA_EMBED_MODEL=bge-m3`, `OPENALEX_API_KEY=` (tùy chọn), `OPENALEX_MAILTO=` (tùy chọn), `OLLAMA_QU_MODEL=` (tùy chọn, model cho bước 1), `RERANK_ENABLED=false`.
- README (tiếng Anh, cho người chấm): kiến trúc + sơ đồ, quickstart (restore dump hoặc ingest), quyết định thiết kế & đánh đổi, chất lượng dữ liệu (outlier, tỷ lệ link giảng viên), kết quả eval, ảnh chụp màn hình.

## 12. Rủi ro & giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| `qwen3:4b` mở rộng khái niệm kém | Few-shot + `synonyms.yaml` + vector search; eval so với 8b |
| Tỷ lệ link giảng viên thấp | Nhiều tầng khớp tên; giảng viên chưa link vẫn tìm được qua keyword/embedding; báo cáo minh bạch |
| Quota OpenAlex | Cache, select tối thiểu, hỗ trợ API key |
| Embedding 21k văn bản chậm | Batch, resume, dump DB dựng sẵn |
| Câu bắt buộc #1 ít bài thật sự khớp | Nhóm khái niệm rộng (military, defense, warfare, armed conflict, geopolitics…); nếu ít kết quả, trả lời trung thực số lượng tìm được |
| Tune tham số overfit vào eval set | Chia tune/holdout; báo cáo holdout; không đưa 2 câu bắt buộc vào dữ liệu finetune |

## 13. Stretch — Finetune bước 1 (query understanding) bằng LoRA

Chỉ làm **sau khi** pipeline cơ bản chạy và đã có số eval nền. Chỉ giữ bản finetune nếu holdout tốt hơn bản gốc.

- **Mục tiêu:** tăng tỷ lệ JSON hợp lệ và chất lượng nhóm khái niệm (mở rộng đồng nghĩa domain), giảm phụ thuộc `synonyms.yaml`. **Không** finetune để nạp kiến thức về bài báo/giảng viên — đó là việc của retrieval.
- **Dữ liệu:** 800–1.500 cặp `câu hỏi → JSON` sinh từ dữ liệu UIUC đã ingest: lấy topic/subfield/keyword thật làm hạt giống, sinh câu hỏi đa dạng (papers/faculty/both/out_of_scope, có/không mốc thời gian, câu nối tiếp), sinh nhãn bằng model lớn hơn (`qwen3:8b` hoặc model ngoài), validate bằng JSON schema, khử trùng lặp. Loại mọi câu gần trùng với `eval/queries.yaml` (cosine ≥ 0.9). Lưu `finetune/data/{train,valid}.jsonl`.
- **Huấn luyện:** LoRA bằng `mlx-lm` trên Apple Silicon, base `Qwen/Qwen3-4B`; rank 8–16, 2–3 epoch, lr 1e-4; theo dõi valid loss.
- **Đóng gói:** fuse adapter → chuyển GGUF (llama.cpp) → quantize Q4_K_M → `ollama create uiuc-qu:4b -f finetune/Modelfile`. Bước 1 dùng biến `OLLAMA_QU_MODEL` (mặc định = `OLLAMA_CHAT_MODEL`).
- **Yêu cầu tài nguyên:** ~20 GB đĩa trống (weights fp16 ~8 GB + bản fused + GGUF), RAM ≥ 16 GB.
- **Bàn giao:** đẩy GGUF lên Hugging Face/Ollama registry; README ghi cách tải; mặc định vẫn chạy được với `qwen3:4b` gốc.
