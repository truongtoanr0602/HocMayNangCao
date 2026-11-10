// Pure helpers for Claude-drafted pooling suggestions. No DOM, no capabilities: the page
// inlines this file, and Node can load it for tests (module.exports at the end).
(function (root) {
  const PROMPT_VERSION = "pooling-draft-v1";
  const MAX_NODE_CHARS = 8000;
  const SUGGESTIONS = ["relevant", "not_relevant", "flag_question"];

  function buildPrompt(question, nodeIds, nodes) {
    const groups = question.groups.length
      ? question.groups.map((g, i) => `- Nhóm ${i}: node ${g.primary}\n  Bằng chứng: "${g.quote}"`).join("\n")
      : "- (Câu này hiện được gán là KHÔNG trả lời được từ corpus.)";
    const allowed = question.answerable ? '"relevant" hoặc "not_relevant"' : '"not_relevant" hoặc "flag_question"';
    const candidates = nodeIds.map(id => {
      const node = nodes[id];
      const text = node.text.length > MAX_NODE_CHARS ? node.text.slice(0, MAX_NODE_CHARS) + "\n[…bị cắt…]" : node.text;
      return `### node_id: ${id}\n${node.document} — ${node.address}\n${text}`;
    }).join("\n\n");
    return `Bạn hỗ trợ một nhóm duyệt nhãn cho bộ đánh giá truy xuất văn bản pháp luật lao động Việt Nam.
Đây là bản NHÁP: người sẽ kiểm tra từng gợi ý của bạn, nên hãy thận trọng và nêu lý do ngắn.

Câu hỏi: ${question.question}
Loại câu: ${question.type}
Tiêu chí trả lời: ${question.rubric}
Bằng chứng đã có trong nhãn:
${groups}

Với MỖI node ứng viên bên dưới, quyết định node đó có TỰ MÌNH đủ để trả lời câu hỏi theo tiêu chí không.
Quy tắc:
1. "relevant" chỉ khi đọc riêng node (cùng phần dẫn của nó) là đủ đưa ra kết luận theo tiêu chí. Cùng chủ đề, cùng Điều hay "có liên quan" là CHƯA đủ.
2. Cùng chủ đề nhưng khác trường hợp (ví dụ ngày thường thay vì ngày nghỉ, ban đêm thay vì ban ngày, đối tượng khác) → "not_relevant".
3. Văn bản hướng dẫn hoặc nghị định nhắc lại đúng quy định trả lời câu hỏi → "relevant".
4. Câu có nhiều nhóm: "group_index" là số nhóm mà node thay thế được. Câu một nhóm: 0.
5. Câu hiện được gán là không trả lời được: chỉ dùng "flag_question" khi node thật sự trả lời được câu hỏi (khi đó câu hỏi bị gán nhầm loại); còn lại "not_relevant".
6. Với "relevant": "evidence_quote" phải là một đoạn CHÉP NGUYÊN VĂN, liền mạch, nằm trong MỘT dòng của nội dung node (không sửa chữ, không thêm dấu ba chấm). Với gợi ý khác: null.
7. "reason": tiếng Việt, tối đa 25 từ.
Giá trị "suggestion" được phép: ${allowed}.

Trả lời DUY NHẤT một mảng JSON, mỗi node đúng một phần tử, theo dạng:
[{"node_id": "...", "suggestion": "...", "group_index": 0, "evidence_quote": null, "reason": "..."}]

Các node ứng viên (${nodeIds.length} node):

${candidates}`;
  }

  function parseJsonArray(text) {
    const fenced = /```(?:json)?\s*([\s\S]*?)```/.exec(text);
    const body = fenced ? fenced[1] : text;
    const start = body.indexOf("["), end = body.lastIndexOf("]");
    if (start < 0 || end <= start) throw new Error("Không tìm thấy mảng JSON trong câu trả lời");
    return JSON.parse(body.slice(start, end + 1));
  }

  // Normalise one answer into {node_id: item}; every candidate gets an entry, invalid parts are nulled with a note.
  function validateDraft(question, nodeIds, nodes, answer) {
    const items = {};
    const byId = new Map();
    for (const raw of Array.isArray(answer) ? answer : []) {
      if (raw && typeof raw.node_id === "string" && nodeIds.includes(raw.node_id) && !byId.has(raw.node_id)) byId.set(raw.node_id, raw);
    }
    for (const id of nodeIds) {
      const raw = byId.get(id);
      const item = { suggestion: null, group_index: null, evidence_quote: null, reason: "", problems: [] };
      if (!raw) { item.problems.push("missing"); items[id] = item; continue; }
      item.reason = typeof raw.reason === "string" ? raw.reason.slice(0, 300) : "";
      const allowed = question.answerable ? ["relevant", "not_relevant"] : ["not_relevant", "flag_question"];
      if (!SUGGESTIONS.includes(raw.suggestion) || !allowed.includes(raw.suggestion)) {
        item.problems.push("bad_suggestion");
      } else {
        item.suggestion = raw.suggestion;
      }
      if (item.suggestion === "relevant") {
        const groups = question.groups.length;
        const g = Number(raw.group_index);
        item.group_index = Number.isInteger(g) && g >= 0 && g < groups ? g : (groups === 1 ? 0 : null);
        if (item.group_index === null) item.problems.push("bad_group");
        const quote = typeof raw.evidence_quote === "string" ? raw.evidence_quote.trim() : "";
        if (quote && nodes[id].text.includes(quote)) item.evidence_quote = quote;
        else item.problems.push("quote_not_verbatim");
      }
      items[id] = item;
    }
    return items;
  }

  const api = { PROMPT_VERSION, MAX_NODE_CHARS, buildPrompt, parseJsonArray, validateDraft };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.PoolingDraft = api;
})(typeof window !== "undefined" ? window : globalThis);
