# Thử nghiệm embedding node KG

Phạm vi: chỉ KG + embedding node Điều/Khoản/Điểm (4534 node); không BM25, không embed chunk.
Quy trình đầy đủ (E0–E9) và các lệnh: `evaluation/README.md`.

## Trạng thái (2026-11-10)

Kết quả dưới đây là **tạm thời**: bộ dev mới có 20 câu (18 câu có đáp án) với nhãn v1 chưa qua pooling.
Chưa chọn chính thức model M, chưa chốt cấu hình, chưa chạy test. Các bước còn chờ người làm:
mở rộng bộ câu hỏi lên ~120 câu (issue #3) và duyệt `evaluation/pooling_review.jsonl` (issue #4).

| Model | Hugging Face | Chiều | Token/cửa sổ | Encode trên T4 |
|---|---|---:|---:|---:|
| e5-small | `intfloat/multilingual-e5-small` | 384 | 512 | 19 s |
| e5-base | `intfloat/multilingual-e5-base` | 768 | 512 | 62 s |
| vn-embedding | `AITeamVN/Vietnamese_Embedding` | 1024 | 8192 | 215 s |
| bge-m3 | `BAAI/bge-m3` | 1024 | 8192 | 206 s |

Mọi model được encode trong **cùng một môi trường** (Colab, Tesla T4, float32, tắt TF32;
phiên bản thư viện trong `colab_env.txt`) để so sánh công bằng; revision model được pin trong từng `manifest.json`.
`bge-m3` chỉ có `pytorch_model.bin` trên nhánh chính nên được nạp qua `weights_only`; các model khác dùng safetensors.

## Kết quả dev tạm thời (P1, text v1)

| Model | Recall nhóm @1 | @5 | Node chính @5 | MRR@10 |
|---|---:|---:|---:|---:|
| e5-small | 0.583 | 0.750 | 0.694 | 0.698 |
| e5-base | 0.583 | 0.833 | 0.750 | 0.738 |
| vn-embedding | **0.833** | **1.000** | **0.917** | **0.938** |
| bge-m3 | 0.639 | 0.889 | 0.861 | 0.812 |

- vn-embedding cao nhất ở mọi chỉ số, nhưng với 18 câu chỉ khác biệt có ý nghĩa thống kê so với e5-small
  (CI 95% paired bootstrap). So với e5-base, CI là [0.000, +0.333]; so với bge-m3 là [0.000, +0.278].
  Theo quy tắc đã chốt (chênh trong CI thì chọn model nhẹ hơn), bộ 18 câu **chưa đủ** để kết luận; cần bộ ~120 câu.
- Text Điều v2 (tiêu đề + phần dẫn) tăng Recall@5 của e5-small/e5-base (+0.083/+0.056) và tăng node chính @5
  của vn-embedding (0.917 → 0.972), giảm một nhóm ở Recall@5 của vn-embedding; không chênh nào có ý nghĩa thống kê.
- P2 (mở rộng 1 bước trên KG, cùng ngân sách 10 node / 12.000 ký tự) không đổi Recall@5 ở model nào trên dev.
  Router KG đúng 3/3 câu direct, không định tuyến nhầm câu nào khác; router + P2 tăng bge-m3 lên 0.944 và MRR vn-embedding lên 0.969.
- Ngưỡng từ chối (cosine top-1) đều từ chối đúng 2/2 câu không trả lời được trên dev với từ chối nhầm ≤ 5.6%;
  chỉ có 2 câu âm nên ngưỡng còn rất bất định.
- Chỉ nâng phiên bản thư viện (torch 2.5→2.15, transformers 5.3→5.22) đã làm e5-small đổi Recall@5 từ 0.806 xuống 0.750:
  cosine dịch ~0.001 làm đảo hai node sát nhau ở câu q006. Với bộ nhỏ, mọi chênh lệch cỡ một câu đều là nhiễu.

## Neo4j

Vector cả 4 model đã nạp vào snapshot `1d10ded4…` (thuộc tính `embedding_<model>`, index cosine
`kg_node_embedding_<model>`). Độ khớp top-10 giữa vector index (HNSW, overfetch 10) và cosine chính xác:
e5-small 0.99, e5-base 0.965, vn-embedding 0.975, bge-m3 0.945 (`<model>/ann_check.json`).

## File

| File | Nội dung |
|---|---|
| `comparison.md/.json` | So sánh 4 model (P1, text v1), CI bootstrap, ngưỡng từ chối, thông tin encode |
| `pipelines.md/.json` | P1-budget / P2 / router+P2 cho từng model |
| `text_versions.md/.json` | Text Điều v1 và v2 |
| `<model>/` | `manifest.json`, `results.json`, `predictions.json` (top-20/câu), `query_ids.json`, `ann_check.json`; `node_vectors.npy`, `query_vectors.npy` (gitignore) |
| `<model>/p1-budget`, `p2`, `router-p2` | Run sinh bởi `legal_kg.kg_expansion`; `expansion_report.json` ghi kết quả router |
| `text-v2/<model>/` | Run với text Điều v2 |
| `pool/{dev,test}/<model>/pool.json` | Top-10 node ID theo thứ tự chữ cái, không điểm, để duyệt pooling mù |

Vector `.npy` không vào git; bản đầy đủ nằm trong `colab_results.zip` (gitignore) — nên giữ lại file này.
