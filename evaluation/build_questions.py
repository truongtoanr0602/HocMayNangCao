"""Build a corpus-grounded, reviewable retrieval benchmark. No model calls."""
import argparse
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_kg.models import fingerprint  # noqa: E402

# Target composition of the expanded benchmark (ticket #3); enforced with --enforce-composition.
COMPOSITION_TARGET = {'natural': 70, 'direct': 15, 'multi': 20, 'unanswerable': 15}
TABLE_OR_APPENDIX_TARGET = 10
POOLING_REVIEW = ROOT / 'evaluation' / 'pooling_review.jsonl'

# Each reference is (document, article, optional clause, optional point, evidence substring).
# Splits are assigned by provision family, not by paraphrase.
SEEDS = [
    ("dev", "natural", "Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?",
     [("01", "17", "1", None, "Giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ")],
     "Nêu hành vi bị cấm; phân biệt bản chính với bản sao."),
    ("dev", "natural", "Công việc cần trình độ cao đẳng thì được thử việc tối đa bao lâu?",
     [("01", "25", "2", None, "Không quá 60 ngày")],
     "Nêu giới hạn cho đúng nhóm trình độ; không áp dụng mức của người quản lý doanh nghiệp."),
    ("test", "natural", "Trong thời gian làm thử, lương có được thấp hơn 85 phần trăm lương công việc không?",
     [("01", "26", None, None, "ít nhất phải bằng 85%")],
     "Nêu mức tối thiểu và cơ sở so sánh là lương của công việc đó."),
    ("test", "natural", "Đang thử việc mà thấy không phù hợp, tôi có phải báo trước khi nghỉ không?",
     [("01", "27", "2", None, "không cần báo trước và không phải bồi thường")],
     "Giới hạn kết luận trong thời gian thử việc."),
    ("test", "natural", "Tôi làm hợp đồng không xác định thời hạn, muốn nghỉ việc thì thường phải báo trước mấy ngày?",
     [("01", "35", "1", "a", "Ít nhất 45 ngày")],
     "Nêu mốc thông thường; không khẳng định áp dụng mọi trường hợp đặc thù hoặc được miễn báo trước."),
    ("dev", "natural", "Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?",
     [("01", "98", "1", "b", "ít nhất bằng 200%")],
     "Nêu tỷ lệ và căn cứ tính ở phần dẫn Khoản 1."),
    ("test", "natural", "Nếu công ty bố trí giờ làm theo ngày thì giờ làm bình thường tối đa bao nhiêu một ngày và một tuần?",
     [("01", "105", "1", None, "không quá 08 giờ trong 01 ngày và không quá 48 giờ")],
     "Trả lời cho chế độ theo ngày, phân biệt cách bố trí theo tuần."),
    ("dev", "natural", "Làm ban đêm từ sáu giờ trở lên trong ngày thì được nghỉ giữa giờ tối thiểu bao lâu?",
     [("01", "109", "1", None, "làm việc ban đêm thì được nghỉ giữa giờ ít nhất 45 phút")],
     "Giữ điều kiện thời giờ làm việc của Khoản 1; nêu thời gian liên tục."),
    ("test", "natural", "Công ty có bắt buộc cho nghỉ hằng tuần vào Chủ nhật không?",
     [("01", "111", "2", None, "ngày Chủ nhật hoặc ngày xác định khác trong tuần")],
     "Nêu quyền sắp xếp ngày khác và yêu cầu ghi trong nội quy."),
    ("test", "natural", "Tôi nghỉ việc mà vẫn còn ngày phép năm chưa dùng hết thì có được thanh toán không?",
     [("01", "113", "3", None, "thanh toán tiền lương cho những ngày chưa nghỉ")],
     "Nêu phạm vi thôi việc hoặc mất việc và phần phép chưa nghỉ."),
    ("dev", "natural", "Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày?",
     [("01", "115", "1", "a", "Kết hôn: nghỉ 03 ngày")],
     "Nêu thời gian và nghĩa vụ thông báo trong phần dẫn Khoản 1."),
    ("test", "natural", "Công ty có được phạt tiền thay cho xử lý kỷ luật nhân viên không?",
     [("01", "127", "2", None, "Phạt tiền, cắt lương thay việc xử lý kỷ luật")],
     "Nêu đây là hành vi bị nghiêm cấm; không đánh đồng với mọi khoản khấu trừ hợp pháp."),
    ("dev", "natural", "Sổ quản lý lao động của doanh nghiệp có thể lập điện tử hay phải dùng giấy?",
     [("02", "3", "2", None, "bản giấy hoặc bản điện tử")],
     "Nêu hai hình thức và điều kiện bảo đảm các thông tin cơ bản."),
    ("test", "natural", "Lao động nữ đang nuôi con dưới một tuổi được nghỉ trong ngày làm việc bao nhiêu phút để cho con bú?",
     [("02", "80", "4", "a", "nghỉ mỗi ngày 60 phút")],
     "Nêu thời gian và việc vẫn hưởng đủ lương."),
    ("dev", "natural", "Hợp đồng lao động cần ghi địa điểm thế nào nếu tôi thường xuyên làm ở nhiều nơi?",
     [("03", "3", "3", "b", "ghi đầy đủ các địa điểm đó")],
     "Nêu yêu cầu ghi địa điểm cho công việc thường xuyên ở nhiều nơi."),
    ("test", "natural", "Thỏa thuận giữ bí mật kinh doanh có nhất thiết phải nằm ngay trong hợp đồng lao động không?",
     [("03", "4", "1", None, "trong hợp đồng lao động hoặc bằng văn bản khác")],
     "Nêu khả năng lập văn bản khác, giữ điều kiện công việc liên quan trực tiếp đến bí mật."),
    ("test", "natural", "Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?",
     [("04", "3", None, None, "Vùng II | 4.730.000 | 22.700")],
     "Đọc đúng hàng bảng vùng II, đơn vị tháng/giờ; trả lời theo corpus, không tự xác nhận hiệu lực hiện hành."),
    ("dev", "natural", "Trả lương theo tuần thì quy đổi ra mức tháng để so với lương tối thiểu bằng cách nào?",
     [("04", "4", "3", "a", "mức lương theo tuần nhân với 52 tuần chia cho 12 tháng")],
     "Nêu công thức cho lương tuần và mục đích đối chiếu mức tối thiểu."),
    ("test", "natural", "Theo Luật BHXH 2024, người mang thai được nghỉ đi khám thai mấy lần và mỗi lần mấy ngày?",
     [("05", "51", "1", None, "tối đa 05 lần, mỗi lần không quá 02 ngày")],
     "Nêu hai giới hạn, không thay bằng quy định của luật cũ."),
    ("dev", "natural", "Nam đang đóng BHXH bắt buộc có vợ sinh con phải phẫu thuật thì được nghỉ bao nhiêu ngày làm việc?",
     [("05", "53", "2", "b", "07 ngày làm việc")],
     "Nêu trường hợp tại Điểm b; phân biệt trường hợp sinh đôi phải phẫu thuật ở Điểm d."),
    ("test", "natural", "Nộp hồ sơ BHXH trực tiếp thì cơ quan BHXH có thể xác nhận bản sao sau khi đối chiếu bản chính không?",
     [("06", "4", None, None, "cơ quan bảo hiểm xã hội xác nhận đã đối chiếu với bản chính")],
     "Nêu phạm vi bản sao thuộc trường hợp được Điều 4 dẫn chiếu và hồ sơ nộp trực tiếp."),
    ("dev", "natural", "Khi chưa bỏ lương cơ sở thì mức tham chiếu để tính BHXH bằng mức nào?",
     [("06", "5", "2", None, "mức tham chiếu quy định tại Luật Bảo hiểm xã hội bằng mức lương cơ sở")],
     "Nêu điều kiện chưa bãi bỏ mức lương cơ sở."),
    ("dev", "natural", "Thời điểm bắt đầu hưởng chế độ hưu trí là ngày nào sau thời điểm nghỉ hưu?",
     [("07", "3", "2", None, "ngày đầu tiên của tháng liền kề sau thời điểm nghỉ hưu")],
     "Phân biệt thời điểm nghỉ hưu và bắt đầu hưởng chế độ."),
    ("test", "natural", "Đã đến tuổi nghỉ hưu nhưng tôi và công ty muốn tiếp tục làm việc thì có được thỏa thuận không?",
     [("07", "6", "1", None, "thỏa thuận với người sử dụng lao động tiếp tục làm việc")],
     "Nêu khả năng thỏa thuận theo Điều 6; không suy diễn đủ điều kiện hưởng lương hưu."),
    ("test", "direct", "Khoản 4 Điều 97 Bộ luật Lao động 2019 quy định gì về đền bù khi chậm trả lương từ 15 ngày trở lên?",
     [("01", "97", "4", None, "nếu trả lương chậm từ 15 ngày trở lên")],
     "Nêu đầy đủ cơ sở tính khoản đền bù, giữ bối cảnh bất khả kháng của Khoản 4."),
    ("dev", "direct", "Điểm b khoản 1 Điều 112 Bộ luật Lao động 2019 quy định nghỉ Tết Âm lịch bao nhiêu ngày?",
     [("01", "112", "1", "b", "Tết Âm lịch: 05 ngày")],
     "Nêu số ngày theo đúng Điểm b; không lập lịch nghỉ cho một năm cụ thể."),
    ("test", "direct", "Khoản 6 Điều 58 Nghị định 145/2020/NĐ-CP có tính thời giờ tập huấn theo yêu cầu công ty vào giờ hưởng lương không?",
     [("02", "58", "6", None, "Thời giờ hội họp, học tập, tập huấn")],
     "Nêu điều kiện theo yêu cầu hoặc được người sử dụng lao động đồng ý."),
    ("dev", "direct", "Khoản 1 Điều 5 Nghị định 293/2025/NĐ-CP ghi ngày có hiệu lực là ngày nào?",
     [("04", "5", "1", None, "ngày 01 tháng 01 năm 2026")],
     "Chỉ đọc mốc trong corpus; không suy ra chưa có văn bản sửa đổi."),
    ("dev", "direct", "Điểm b khoản 1 Điều 52 Luật BHXH 2024 quy định số ngày nghỉ tối đa khi thai từ đủ 5 đến dưới 13 tuần như thế nào?",
     [("05", "52", "1", "b", "20 ngày nếu thai từ đủ 05 tuần tuổi đến dưới 13 tuần tuổi")],
     "Giữ bối cảnh sự kiện thai sản của Điều 52 và chỉ định của người hành nghề khám chữa bệnh."),
    ("test", "direct", "Điểm c khoản 1 Điều 5 Nghị định 135/2020/NĐ-CP nêu mức suy giảm khả năng lao động nào cho trường hợp nghỉ hưu ở tuổi thấp hơn?",
     [("07", "5", "1", "c", "từ 61% trở lên")],
     "Nêu ngưỡng của Điểm c; không kết luận đây là điều kiện duy nhất để hưởng lương hưu."),
    ("dev", "multi", "Nghỉ việc có phải hoàn trả chi phí đào tạo không? Cần xem trách nhiệm khi nghỉ trái luật và thỏa thuận đào tạo ở đâu?",
     [("01", "40", "3", None, "Phải hoàn trả"),
      ("01", "62", "2", "d", "trách nhiệm hoàn trả chi phí đào tạo")],
     "Kết hợp nghĩa vụ khi chấm dứt trái luật và nội dung hợp đồng đào tạo; không khẳng định mọi trường hợp nghỉ đều phải hoàn trả. Hỏi thêm hợp đồng, cam kết và cách chấm dứt."),
    ("test", "multi", "Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?",
     [("01", "137", "4", None, "nuôi con dưới 12 tháng tuổi được nghỉ mỗi ngày 60 phút"),
      ("02", "80", "4", "a", "nghỉ mỗi ngày 60 phút")],
     "Đối chiếu quy định của Bộ luật và hướng dẫn; nêu thời gian nghỉ hưởng đủ lương."),
    ("test", "multi", "Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?",
     [("01", "169", "2", None, "đủ 62 tuổi đối với lao động nam vào năm 2028"),
      ("07", "4", None, None, "2026 | 61 tuổi 6 tháng | 2026 | 57 tuổi")],
     "Kết hợp lộ trình và bảng theo corpus; không đồng nhất tuổi nghỉ hưu với toàn bộ điều kiện hưởng lương hưu."),
    ("dev", "multi", "Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?",
     [("01", "98", "1", "b", "ít nhất bằng 200%"),
      ("08", "17", "2", None, "không trả hoặc trả không đủ tiền lương làm thêm giờ")],
     "Tìm cả quy định tiền lương và chế tài; không tự tính tiền phạt khi chưa có số người vi phạm và tư cách chủ thể."),
    ("dev", "natural", "Nhà tuyển dụng bắt tôi đặt cọc tiền để bảo đảm thực hiện hợp đồng lao động có được không?",
     [("01", "17", "2", None, "biện pháp bảo đảm bằng tiền hoặc tài sản khác")],
     "Nêu hành vi bị cấm; giữ ngữ cảnh bảo đảm thực hiện hợp đồng lao động."),
    ("dev", "natural", "Nam đang tham gia BHXH bắt buộc có vợ sinh đôi phải phẫu thuật thì được nghỉ bao nhiêu ngày?",
     [("05", "53", "2", "d", "nghỉ 14 ngày làm việc")],
     "Phân biệt sinh đôi phải phẫu thuật với một con phải phẫu thuật; nêu ngày làm việc."),
    ("dev", "unanswerable", "Công ty ABC chuyển lương tháng này vào tài khoản của tôi lúc mấy giờ?", [],
     "Không có dữ liệu giao dịch/nghiệp vụ riêng của công ty; cần xác nhận từ doanh nghiệp hoặc ngân hàng."),
    ("test", "unanswerable", "Mã số hồ sơ BHXH của riêng tôi đang được xử lý đến bước nào?", [],
     "Corpus văn bản không có trạng thái hồ sơ cá nhân; không bịa dữ liệu tra cứu."),
    ("dev", "unanswerable", "Viết giúp tôi thuật toán sắp xếp nhanh bằng Python.", [],
     "Ngoài phạm vi corpus pháp luật lao động/BHXH."),
    ("test", "unanswerable", "Thời tiết ở Đà Nẵng sáng mai có mưa không?", [],
     "Ngoài phạm vi corpus và cần dữ liệu thời tiết trực tiếp."),
]


def apply_pooling(questions, nodes, rows):
    """Add reviewer-approved pooled nodes as acceptable evidence; returns (label_version, pending)."""
    by_id = {q['question_id']: q for q in questions}
    pending = 0
    for row in rows:
        decision = row.get('decision')
        if decision is None:
            pending += 1
            continue
        if decision not in {'relevant', 'not_relevant'}:
            raise ValueError(f"Unknown pooling decision {decision!r} for {row['question_id']}")
        if decision == 'not_relevant':
            continue
        q = by_id[row['question_id']]
        if not q['answerable']:
            raise ValueError(f"{q['question_id']} is unanswerable but a pooled node was judged relevant; "
                             'fix its SEED instead')
        index = row.get('group_index')
        if type(index) is not int or not 0 <= index < len(q['evidence_groups']):
            raise ValueError(f"Invalid group_index for {row['question_id']} / {row['node_id']}")
        quote_text = row.get('evidence_quote') or ''
        if not quote_text.strip() or quote_text not in nodes[row['node_id']]['body_text']:
            raise ValueError(f"Evidence quote is not verbatim in {row['node_id']} ({row['question_id']})")
        group = q['evidence_groups'][index]
        if row['node_id'] not in group['acceptable_node_ids']:
            group['acceptable_node_ids'].append(row['node_id'])
            group.setdefault('pooled_additions', []).append(
                {'node_id': row['node_id'], 'evidence_quote': quote_text})
    return ('v2' if rows and not pending else 'v1'), pending


def read_lines(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def build(enforce_composition=False):
    records = read_lines(ROOT / 'output/kg/embedding_text/node_texts.jsonl')
    nodes = {r['node_id']: r for r in records}
    chunks = {c['chunk_id']: c for c in read_lines(ROOT / 'output/preprocessed/legal_chunks.jsonl')}
    questions = []
    for index, (split, kind, question, refs, rubric) in enumerate(SEEDS, 1):
        groups = []
        articles = set()
        for doc, article, clause, point, anchor in refs:
            suffix = f'/article-{article}'
            if clause is not None:
                suffix += f'/clause-{clause}'
            if point is not None:
                from urllib.parse import quote
                suffix += '/point-' + quote(point, safe='')
            matches = [r for r in records if r['document_id'] == 'doc-' + doc and r['node_id'].endswith(suffix)]
            if len(matches) != 1:
                raise ValueError(f'Ambiguous or missing node: {index} {refs}')
            node = matches[0]
            if anchor not in node['body_text']:
                raise ValueError(f'Evidence anchor absent: {index} {node["node_id"]}: {anchor}')
            # Include the entire source line around the manually selected anchor.
            position = node['body_text'].index(anchor)
            start = node['body_text'].rfind('\n', 0, position) + 1
            end = node['body_text'].find('\n', position + len(anchor))
            if end < 0:
                end = len(node['body_text'])
            quote_text = node['body_text'][start:end]
            article_node = next(p for p in node['path_node_ids'] if nodes.get(p, {}).get('label') == 'Article')
            articles.add(article_node)
            # Ancestors are alternatives only if their body contains the evidence.
            # Descendants are not assumed relevant merely by sharing an article.
            acceptable = [p for p in node['path_node_ids'] if p in nodes and quote_text in nodes[p]['body_text']]
            # Flag evidence that sits in a table or appendix chunk (reported as its own slice).
            in_table = any(chunks[c]['chunk_type'] in {'table', 'appendix'} and quote_text in chunks[c]['text']
                           for c in node['source_chunk_ids'])
            groups.append({'primary_node_id': node['node_id'], 'acceptable_node_ids': acceptable,
                           'evidence_in_table_or_appendix': in_table,
                           'evidence_quote': quote_text, 'body_start': start, 'body_end': end,
                           'source_chunk_ids': node['source_chunk_ids'],
                           'note': 'Chunk IDs are node provenance candidates, not exact-span relevance judgments.'})
        questions.append({'question_id': f'q{index:03d}', 'split': split, 'type': kind,
                          'question': question, 'answerable': bool(refs),
                          'snapshot_id': records[0]['snapshot_id'], 'graph_hash': records[0]['graph_hash'],
                          'evidence_groups': groups, 'article_family_ids': sorted(articles),
                          'evidence_in_table_or_appendix': any(g['evidence_in_table_or_appendix'] for g in groups),
                          'answer_rubric': rubric, 'review_status': 'draft_corpus_checked',
                          'requires_human_review': True,
                          'scope': 'fixed_corpus_not_current_legal_advice'})
    families = {}
    for q in questions:
        for article in q['article_family_ids']:
            if article in families and families[article] != q['split']:
                raise ValueError(f'Article-family split leakage: {article}')
            families[article] = q['split']
    rows = read_lines(POOLING_REVIEW) if POOLING_REVIEW.exists() else []
    label_version, pending = apply_pooling(questions, nodes, rows)
    for q in questions:
        q['label_version'] = label_version
    composition = dict(Counter(q['type'] for q in questions))
    table_count = sum(q['evidence_in_table_or_appendix'] for q in questions)
    if enforce_composition:
        if composition != COMPOSITION_TARGET:
            raise ValueError(f'Composition {composition} differs from target {COMPOSITION_TARGET}')
        if table_count < TABLE_OR_APPENDIX_TARGET:
            raise ValueError(f'Only {table_count} questions have table/appendix evidence; '
                             f'need {TABLE_OR_APPENDIX_TARGET}')
        splits = Counter(q['split'] for q in questions)
        if abs(splits['dev'] - splits['test']) > 1:
            raise ValueError(f'Dev and test must split the questions evenly: {dict(splits)}')
    output = ROOT / 'evaluation'
    for name, subset in [('questions', questions), ('dev', [q for q in questions if q['split']=='dev']),
                         ('test', [q for q in questions if q['split']=='test'])]:
        (output / f'{name}.jsonl').write_text(''.join(json.dumps(q, ensure_ascii=False)+'\n' for q in subset), encoding='utf-8')
    summary = {'total': len(questions), 'by_split': dict(Counter(q['split'] for q in questions)),
               'by_type': dict(Counter(q['type'] for q in questions)),
               'documents_with_evidence': sorted({g['primary_node_id'].split('/')[0] for q in questions for g in q['evidence_groups']}),
               'article_family_split_overlap': 0, 'all_evidence_quotes_checked': True,
               'requires_human_review': True, 'snapshot_id': records[0]['snapshot_id'],
               'table_or_appendix_questions': table_count, 'label_version': label_version,
               'pooling_rows': len(rows), 'pooling_pending': pending,
               'label_hash': fingerprint(questions),
               'dev_question_hash': fingerprint([q for q in questions if q['split'] == 'dev']),
               'test_question_hash': fingerprint([q for q in questions if q['split'] == 'test'])}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    review = ['# Bộ câu hỏi đánh giá truy xuất node', '',
              'Bản nháp kiểm tra theo corpus cố định; cần duyệt nội dung và độ đủ của bằng chứng.', '']
    for q in questions:
        review += [f"## {q['question_id']} — {q['split']} — {q['type']}", '', q['question'], '',
                   'Tiêu chí trả lời: ' + q['answer_rubric'], '']
        for group in q['evidence_groups']:
            review += ['Node chính: `' + group['primary_node_id'] + '`', '',
                       '> ' + group['evidence_quote'].replace('\n', '\n> '), '']
        if not q['answerable']:
            review += ['Không gán node đáp án; đánh giá khả năng báo thiếu bằng chứng/ngoài phạm vi.', '']
    (output / 'questions_review.md').write_text('\n'.join(review), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enforce-composition', action='store_true',
                        help=f'Require the target composition {COMPOSITION_TARGET} and an even dev/test split')
    build(parser.parse_args().enforce_composition)
