"""Summarize completed development experiments without opening test labels."""
import json
from pathlib import Path


def main():
    base = Path('output/kg/embedding_benchmark')
    results = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(base.glob('*/results.json'))]
    if not results:
        raise ValueError('No completed experiments')
    if len({r['question_set_hash'] for r in results}) != 1:
        raise ValueError('Question sets differ')
    if len({tuple(r['manifest']['config']['candidate_ids']) for r in results}) != 1:
        raise ValueError('Candidate sets differ')
    if len({tuple(r['manifest']['config']['content_hashes']) for r in results}) != 1:
        raise ValueError('Node texts differ')
    lines = ['# So sánh embedding node trên development', '',
             'Đây là thử nghiệm trên bộ nhãn nháp, chưa đánh giá tập test hoặc Neo4j ANN.', '',
             '| Model | Node | Token/window | Số window | Recall nhóm @1 | @3 | @5 | @10 | Node chính @5 | MRR@10 (1 nhóm) |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        m=r['metrics']; manifest=r['manifest']; config=manifest['config']
        values=[f"{m['by_k'][str(k)]['group_recall_macro']:.3f}" for k in (1,3,5,10)]
        lines.append(f"| {r['model']} | {r['candidate_count']} | {config['max_seq_length']} | {manifest['window_count']} | "
                     + ' | '.join(values) + f" | {m['by_k']['5']['primary_group_recall_macro']:.3f} | {m['single_group_mrr_at_max_k']:.3f} |")
    lines += ['', '## Theo loại câu hỏi', '',
              '| Model | Loại | Số câu có đáp án | Recall nhóm @5 | Đủ mọi nhóm @5 |',
              '|---|---|---:|---:|---:|']
    for r in results:
        for kind,m in r['metrics']['by_type'].items():
            k=m['by_k']['5']
            lines.append(f"| {r['model']} | {kind} | {m['answerable_questions']} | {k['group_recall_macro']:.3f} | {k['all_groups_hit_rate']:.3f} |")
    questions = [json.loads(line) for line in Path('evaluation/dev.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    questions = {q['question_id']:q for q in questions}
    lines += ['', '## Câu chưa lấy đủ bằng chứng ở top 5', '']
    for r in results:
        lines += [f"### {r['model']}", '']
        predictions = json.loads((base/r['model']/'predictions.json').read_text(encoding='utf-8'))
        for p in predictions:
            q=questions[p['question_id']]
            if not q['answerable']:
                continue
            found={n['node_id'] for n in p['top_nodes'][:5]}
            missing=[g['primary_node_id'] for g in q['evidence_groups'] if not found.intersection(g['acceptable_node_ids'])]
            if missing:
                lines += [f"- {q['question_id']}: {q['question']} — thiếu nhóm {', '.join(missing)}"]
        lines += ['']
    lines += ['', '## Giao thức và giới hạn', '',
              '- Tìm trên toàn bộ node Điều/Khoản/Điểm bằng cosine chính xác, không hạn chế ứng viên theo nhãn đáp án.',
              '- Cả hai dùng cửa sổ token chồng lấn, chuẩn hóa vector cửa sổ, lấy trung bình có trọng số token mới rồi chuẩn hóa vector node.',
              '- Đây là so sánh model cùng cấu hình độ dài gốc của từng model, không phải thí nghiệm chỉ thay trọng số model.',
              '- Xem batch_size trong manifest: E5 giảm batch để phù hợp RAM. Không dùng thời gian encode hai lượt khác batch để kết luận tốc độ model trong điều kiện kiểm soát.',
              '- E5 dùng passage: cho node và query: cho câu hỏi. MiniLM không dùng hai tiền tố này.',
              '- Recall nhóm cho phép node tổ tiên nếu chứa nguyên văn bằng chứng; xem thêm node chính để tránh kết quả quá lạc quan.',
              '- Câu multi cần xem all_groups_hit_rate, không chỉ có một đáp án đúng.',
              '- Câu không trả lời được chỉ xuất chẩn đoán top-k; chưa chọn ngưỡng từ chối trên bộ quá nhỏ.',
              '- Thời gian encode trong manifest là thời gian phần chạy của session; nếu resume không phải tổng thời gian từ đầu. Thời gian tải model được ghi riêng.',
              '- Chưa kiểm tra sử dụng RAM đỉnh; chưa có reranker, graph traversal, sinh câu trả lời hoặc ghi Neo4j.',
              '- Các file predictions.json chứa thứ hạng theo từng câu để phân tích lỗi; manifest.json lưu commit model và hash nội dung.', '',
              '## Nguồn cấu hình model', '',
              '- https://huggingface.co/intfloat/multilingual-e5-small',
              '- https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', '']
    (base/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
    print(base/'comparison.md')


if __name__=='__main__':
    main()
