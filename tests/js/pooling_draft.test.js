// Checks for evaluation/pooling_review_page/draft.js on sample data.
const assert = require("assert");
const D = require(require("path").resolve(__dirname, "../../evaluation/pooling_review_page/draft.js"));
const nodes = {
  "doc-02/a55/c1": { text: "1. Mức lương:\nb) mức ít nhất bằng 200% vào ngày nghỉ hằng tuần;", document: "NĐ 145", address: "Điều 55 > Khoản 1" },
  "doc-01/a98/c1/p-a": { text: "a) Vào ngày thường, ít nhất bằng 150%;", document: "BLLĐ", address: "Điều 98 > Khoản 1 > Điểm a" },
  "doc-01/a98/c2": { text: "2. Làm việc ban đêm được trả thêm ít nhất 30%.", document: "BLLĐ", address: "Điều 98 > Khoản 2" },
};
const ids = Object.keys(nodes);
const q = { id: "q006", question: "Làm thêm ngày nghỉ hằng tuần bao nhiêu %?", type: "natural", rubric: "Nêu tỷ lệ.",
  answerable: true, groups: [{ primary: "doc-01/a98/c1/p-b", quote: "b) Vào ngày nghỉ hằng tuần, ít nhất bằng 200%;" }] };

const prompt = D.buildPrompt(q, ids, nodes);
assert(ids.every(id => prompt.includes("node_id: " + id)));
assert(prompt.includes('"relevant" hoặc "not_relevant"') && !/score|model|rank/i.test(prompt.replace(/JSON/g, "")));

const answer = D.parseJsonArray('Đây:\n```json\n[{"node_id":"doc-02/a55/c1","suggestion":"relevant","group_index":3,' +
  '"evidence_quote":"mức ít nhất bằng 200% vào ngày nghỉ hằng tuần","reason":"NĐ nhắc lại"},' +
  '{"node_id":"doc-01/a98/c1/p-a","suggestion":"relevant","group_index":0,"evidence_quote":"bịa ra","reason":"x"},' +
  '{"node_id":"doc-01/a98/c1/p-a","suggestion":"not_relevant"},{"node_id":"unknown","suggestion":"relevant"}]\n```');
const items = D.validateDraft(q, ids, nodes, answer);
assert.deepStrictEqual(Object.keys(items).sort(), ids.slice().sort());
assert.strictEqual(items["doc-02/a55/c1"].suggestion, "relevant");
assert.strictEqual(items["doc-02/a55/c1"].group_index, 0);             // single group: out-of-range index → 0
assert.strictEqual(items["doc-02/a55/c1"].evidence_quote, "mức ít nhất bằng 200% vào ngày nghỉ hằng tuần");
assert.deepStrictEqual(items["doc-01/a98/c1/p-a"].problems, ["quote_not_verbatim"]);  // first entry wins, quote rejected
assert.strictEqual(items["doc-01/a98/c1/p-a"].evidence_quote, null);
assert.deepStrictEqual(items["doc-01/a98/c2"].problems, ["missing"]);

const unanswerable = { ...q, answerable: false, groups: [] };
const flagged = D.validateDraft(unanswerable, ids, nodes, [{ node_id: "doc-02/a55/c1", suggestion: "relevant" },
  { node_id: "doc-01/a98/c2", suggestion: "flag_question", reason: "trả lời được" }]);
assert.deepStrictEqual(flagged["doc-02/a55/c1"].problems, ["bad_suggestion"]);   // relevant not allowed here
assert.strictEqual(flagged["doc-01/a98/c2"].suggestion, "flag_question");
assert.throws(() => D.parseJsonArray("không có json"));
console.log("draft.js checks passed");
