# Thử nghiệm embedding node KG

Phạm vi: chỉ KG + embedding node Điều/Khoản/Điểm (4534 node); không BM25, không embed chunk.
Quy trình đầy đủ (E0–E9) và các lệnh: `evaluation/README.md`.

## Trạng thái (2026-11-10)

Nhãn dev/test đã lên **v2**: duyệt đủ 801 dòng pooling mù (issue #4) trên trang dùng chung, thêm 32 node đúng
vào các nhóm bằng chứng (20 ở dev, 12 ở test). 748 dòng là nháp Claude được người xác nhận, 53 dòng do người tự quyết; người duyệt
quyết định khác nháp 1/762 lần (`evaluation/summary.json`). Các run dev được gắn lại nhãn bằng
`python -m legal_kg.relabel_runs` (thứ hạng chỉ phụ thuộc văn bản câu hỏi nên không encode lại).

Bộ câu hỏi giữ 40 câu (20 dev / 20 test); việc mở rộng lên ~120 câu (issue #3) để sau.

**Đã chốt trên dev** (`evaluation/frozen_config.json`): model M = **e5-base**, text Điều v1, pipeline P1, ngưỡng từ chối
theo từng cấu hình. Lý do: theo quy tắc #5, vn-embedding cao nhất nhưng e5-base và bge-m3 không kém có ý nghĩa thống kê
(CI 95% chứa 0), chỉ e5-small kém có ý nghĩa; e5-base nhẹ/nhanh nhất trong nhóm không kém. Text v2, P2 và router+P2
không đổi Recall@5 của e5-base nên giữ cấu hình đơn giản nhất. Split test đã chạy **một lần** (2026-11-10). Kết quả và nhận xét trong [`REPORT.md`](REPORT.md):
e5-base đạt Recall@5 0.833 trên test, còn vn-embedding đạt 1.000 và hơn e5-base có ý nghĩa thống kê. Cấu hình không được sửa sau khi xem test.

| Model | Hugging Face | Chiều | Token/cửa sổ | Encode trên T4 |
|---|---|---:|---:|---:|
| e5-small | `intfloat/multilingual-e5-small` | 384 | 512 | 19 s |
| e5-base | `intfloat/multilingual-e5-base` | 768 | 512 | 62 s |
| vn-embedding | `AITeamVN/Vietnamese_Embedding` | 1024 | 8192 | 215 s |
| bge-m3 | `BAAI/bge-m3` | 1024 | 8192 | 206 s |

Mọi model được encode trong **cùng một môi trường** (Colab, Tesla T4, float32, tắt TF32;
phiên bản thư viện trong `colab_env.txt`) để so sánh công bằng; revision model được pin trong từng `manifest.json`.
`bge-m3` chỉ có `pytorch_model.bin` trên nhánh chính nên được nạp qua `weights_only`; các model khác dùng safetensors.

## Kết quả dev tạm thời (P1, text v1, nhãn v2)

| Model | Recall nhóm @1 | @5 | Node chính @5 | MRR@10 |
|---|---:|---:|---:|---:|
| e5-small | 0.694 | 0.806 | 0.694 | 0.781 |
| e5-base | 0.722 | 0.917 | 0.750 | 0.823 |
| vn-embedding | **0.889** | **1.000** | **0.917** | **0.969** |
| bge-m3 | 0.806 | 0.889 | 0.861 | 0.917 |

- Nhãn v2 tăng recall của mọi model vì pooling bổ sung node đúng mà nhãn v1 bỏ sót (chủ yếu Nghị định 12/2022 và
  Nghị định 145/2020 nhắc lại cùng quy định); thứ tự giữa các model không đổi.
- vn-embedding cao nhất ở mọi chỉ số, nhưng với 18 câu chỉ khác biệt có ý nghĩa thống kê so với e5-small
  (CI 95% paired bootstrap [−0.389, −0.056]). So với e5-base, CI của chênh lệch là [0.000, +0.222]; so với bge-m3 là [0.000, +0.278].
  Theo quy tắc đã chốt (chênh trong CI thì chọn model nhẹ hơn), bộ 18 câu **chưa đủ** để kết luận; cần bộ ~120 câu.
- Text Điều v2 (tiêu đề + phần dẫn): e5-small Recall@5 0.806 → 0.861, e5-base và bge-m3 không đổi; vn-embedding
  node chính @5 0.917 → 0.972 nhưng Recall@5 1.000 → 0.972. Không chênh nào có ý nghĩa thống kê.
- P2 (mở rộng 1 bước trên KG, cùng ngân sách 10 node / 12.000 ký tự) không đổi Recall@5 ở model nào trên dev.
  Router KG đúng 3/3 câu direct, không định tuyến nhầm câu nào khác; router + P2 tăng bge-m3 Recall@5 lên 0.944
  (MRR 0.969) và MRR vn-embedding lên 1.000.
- Ngưỡng từ chối (cosine top-1) đều từ chối đúng 2/2 câu không trả lời được trên dev với từ chối nhầm ≤ 5.6%;
  chỉ có 2 câu âm nên ngưỡng còn rất bất định.
- Chỉ nâng phiên bản thư viện (torch 2.5→2.15, transformers 5.3→5.22) đã làm e5-small đảo hai node sát nhau ở câu q006
  (cosine dịch ~0.001). Với bộ nhỏ, mọi chênh lệch cỡ một câu đều là nhiễu.
- `minilm` (`paraphrase-multilingual-MiniLM-L12-v2`, cửa sổ 128 token) chỉ chạy trên CPU ngoài môi trường chung,
  nên không vào bảng so sánh; top-10 của nó chỉ được dùng để mở rộng pool duyệt (Recall@5 tham khảo 0.722).

## Neo4j

Vector cả 4 model đã nạp vào snapshot `1d10ded4…` (thuộc tính `embedding_<model>`, index cosine
`kg_node_embedding_<model>`). Độ khớp top-10 giữa vector index (HNSW, overfetch 10) và cosine chính xác:
e5-small 0.99, e5-base 0.965, vn-embedding 0.975, bge-m3 0.945 (`<model>/ann_check.json`).

## File

| File | Nội dung |
|---|---|
| `comparison.md/.json` | So sánh 4 model (P1, text v1, nhãn v2), CI bootstrap, ngưỡng từ chối, thông tin encode |
| `pipelines.md/.json` | P1-budget / P2 / router+P2 cho từng model |
| `text_versions.md/.json` | Text Điều v1 và v2 |
| `<model>/` (gồm cả `minilm/`, chỉ dùng cho pool) | `manifest.json`, `results.json`, `predictions.json` (top-20/câu), `query_ids.json`, `ann_check.json`; `node_vectors.npy`, `query_vectors.npy` (gitignore) |
| `<model>/p1-budget`, `p2`, `router-p2` | Run sinh bởi `legal_kg.kg_expansion`; `expansion_report.json` ghi kết quả router |
| `text-v2/<model>/` | Run với text Điều v2 |
| `test/`, `text-v2/test/` | Run test (một lần) và báo cáo `test/comparison.md`, `pipelines.md`, `text_versions.md`; `test_runs.json` đếm số lần chạy |
| `REPORT.md` | Báo cáo cuối (issue #11) |
| `pool/{dev,test}/<model>/pool.json` | Top-10 node ID theo thứ tự chữ cái, không điểm, để duyệt pooling mù |

Vector `.npy` không vào git; bản đầy đủ nằm trong `colab_results.zip` (gitignore) — nên giữ lại file này.
