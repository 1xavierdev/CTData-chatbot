import unittest
from unittest import mock

from bs4 import BeautifulSoup

import lmstudio
import rag
import scraper
import server
from kb import KnowledgeBase, build_chunks, chunk_text

PAGES = [
    {
        "url": "https://www.ctdata.org/education",
        "title": "Education Data by CTData",
        "text": "Educational Attainment\nFour Year Graduation Rates, available by:\nGender\nStudent Behavior\nChronic Absenteeism",
        "links": [
            {"label": "Four Year Graduation Rates", "url": "https://public-edsight.ct.gov/grad"},
            {"label": "Chronic Absenteeism", "url": "https://public-edsight.ct.gov/absent"},
        ],
    },
    {
        "url": "https://www.ctdata.org/blog/student-debt",
        "title": "Older Connecticut Residents Have Higher Student Loan Debt",
        "text": "Borrowers aged 50 and older hold a growing share of student loan debt.",
        "links": [],
    },
]


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase(build_chunks(PAGES))

    def test_chunks_respect_size(self):
        chunks = chunk_text("\n".join(f"line {i} " + "x" * 50 for i in range(100)), size=300, overlap=60)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 360 for c in chunks))

    def test_keyword_search_finds_relevant_page(self):
        with mock.patch("lmstudio.embed", return_value=None):
            results = self.kb.search("student loan debt")
        self.assertEqual(results[0]["url"], "https://www.ctdata.org/blog/student-debt")

    def test_unrelated_question_returns_nothing(self):
        self.assertEqual(self.kb.search("weather forecast"), [])


class RagTests(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase(build_chunks(PAGES))

    def test_prompt_is_tailored_to_profile(self):
        messages = rag.build_messages("q", {"age": "Under 13", "profession": "Student"}, [], [])
        system = messages[0]["content"]
        self.assertIn("child", system)
        self.assertIn("school project", system)

    def test_offline_answer_lists_matching_dataset_links(self):
        with mock.patch("lmstudio.chat", return_value=None):
            result = rag.answer(self.kb, "Where are graduation rates?", {})
        self.assertEqual(result["mode"], "offline")
        self.assertIn("https://public-edsight.ct.gov/grad", result["answer"])

    def test_llm_answer_used_when_available(self):
        with mock.patch("lmstudio.chat", return_value="Graduation rates are on EdSight.") as chat:
            result = rag.answer(self.kb, "graduation rates", {"education": "High school"})
        self.assertEqual(result, {**result, "mode": "llm", "answer": "Graduation rates are on EdSight."})
        sent = chat.call_args[0][0]
        self.assertIn("8th-grade", sent[0]["content"])
        self.assertIn("Four Year Graduation Rates", sent[-1]["content"])


class NotFoundTests(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase(build_chunks(PAGES))

    def passage(self, score, text="Chronic Absenteeism statewide 23.7%"):
        return [{"id": "x#0", "url": "https://x", "title": "EdSight: Chronic Absenteeism", "text": text,
                 "score": score, "match": "semantic"}]

    def test_off_topic_question_skips_the_model(self):
        with mock.patch("lmstudio.chat") as chat:
            result = rag.answer(self.kb, "What's the weather forecast?", {})
        chat.assert_not_called()
        self.assertEqual(result, {"answer": rag.NOT_FOUND, "sources": [], "mode": "not_found"})

    def test_low_similarity_is_not_found(self):
        with mock.patch.object(self.kb, "search", return_value=self.passage(0.45)), mock.patch("lmstudio.chat") as chat:
            result = rag.answer(self.kb, "Who won the chronic bowl?", {})
        chat.assert_not_called()
        self.assertEqual(result["mode"], "not_found")

    def test_no_topic_words_in_context_is_not_found(self):
        with mock.patch.object(self.kb, "search", return_value=self.passage(0.72)), mock.patch("lmstudio.chat") as chat:
            result = rag.answer(self.kb, "What is the unemployment rate?", {})
        chat.assert_not_called()
        self.assertEqual(result["mode"], "not_found")

    def test_model_marker_becomes_not_found(self):
        with mock.patch.object(self.kb, "search", return_value=self.passage(0.7)), \
                mock.patch("lmstudio.chat", return_value="NOT_IN_KB"):
            result = rag.answer(self.kb, "chronic absenteeism in my kid's school", {})
        self.assertEqual(result["mode"], "not_found")

    def test_offline_needs_every_topic_word(self):
        with mock.patch.object(self.kb, "search", return_value=self.passage(0.72)), \
                mock.patch("lmstudio.chat", return_value=None):
            partial = rag.answer(self.kb, "How many COVID cases were chronic?", {})
            full = rag.answer(self.kb, "chronic absenteeism statewide", {})
        self.assertEqual(partial["mode"], "not_found")
        self.assertEqual(full["mode"], "offline")


class LmStudioTests(unittest.TestCase):
    def reply(self, content):
        resp = mock.Mock()
        resp.json.return_value = {"choices": [{"message": {"content": content}}]}
        return resp

    def test_qwen3_thinking_is_disabled_and_hidden(self):
        with mock.patch("lmstudio.chat_model", return_value="qwen/qwen3-8b"), \
                mock.patch("requests.post", return_value=self.reply("<think>hmm</think> Hi")) as post:
            self.assertEqual(lmstudio.chat([{"role": "user", "content": "q"}]), "Hi")
        sent = post.call_args.kwargs["json"]
        self.assertTrue(sent["messages"][-1]["content"].endswith("/no_think"))
        self.assertEqual(sent["reasoning_effort"], "none")

    def test_empty_reply_counts_as_no_answer(self):
        with mock.patch("lmstudio.chat_model", return_value="m"), \
                mock.patch("requests.post", return_value=self.reply("<think>ran out of tokens</think>")):
            self.assertIsNone(lmstudio.chat([{"role": "user", "content": "q"}]))


class EdsightTableTests(unittest.TestCase):
    def test_multi_row_headers_become_one_line_per_year(self):
        table = BeautifulSoup("""<table>
            <tr><td>Chronic Absenteeism, Trend</td></tr><tr><td>Export .csv file</td></tr>
            <tr><th></th><th colspan="2">2021-22</th><th colspan="2">2022-23</th></tr>
            <tr><th>Organization</th><th>Count</th><th>%</th><th>Count</th><th>%</th></tr>
            <tr><th>State of Connecticut</th><td>117,513</td><td>23.7</td><td>99,071</td><td>20.0</td></tr>
        </table>""", "html.parser").table
        self.assertEqual(scraper.table_lines(table), [
            "Chronic Absenteeism, Trend",
            "State of Connecticut, 2021-22: Count 117,513; % 23.7",
            "State of Connecticut, 2022-23: Count 99,071; % 20.0",
        ])

    def test_rowspan_labels_keep_values_aligned(self):
        table = BeautifulSoup("""<table>
            <tr><th>District</th><th>Subject</th><th>2021-22</th></tr>
            <tr><th rowspan="2">State</th><td>ELA</td><td>49.1</td></tr>
            <tr><td>Math</td><td>40.0</td></tr>
        </table>""", "html.parser").table
        self.assertEqual(scraper.table_lines(table), ["State, ELA, 2021-22: 49.1", "State, Math, 2021-22: 40.0"])


class ApiTests(unittest.TestCase):
    def setUp(self):
        server.kb = KnowledgeBase(build_chunks(PAGES))
        self.client = server.app.test_client()

    def test_chat_requires_message(self):
        self.assertEqual(self.client.post("/api/chat", json={}).status_code, 400)

    def test_chat_returns_answer(self):
        with mock.patch("lmstudio.chat", return_value=None):
            resp = self.client.post("/api/chat", json={"message": "chronic absenteeism", "profile": {}})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Chronic Absenteeism", resp.get_json()["answer"])


if __name__ == "__main__":
    unittest.main()
