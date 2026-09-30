import unittest
from unittest import mock

import rag
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

    def test_search_links_finds_relevant_dataset_links(self):
        results = self.kb.search_links("graduation rates")
        self.assertTrue(any("public-edsight.ct.gov/grad" in r["text"] for r in results))

    def test_search_links_empty_when_nothing_matches(self):
        self.assertEqual(self.kb.search_links("weather forecast"), [])


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

    def test_prompt_includes_trusted_resources_for_comparison(self):
        # "by town" is not in the context (missing answer), but related dataset
        # links must still be attached so the bot can reference/compare them.
        with mock.patch("lmstudio.chat", return_value="answer") as chat:
            rag.answer(self.kb, "do you have chronic absenteeism by town?", {})
        sent = chat.call_args[0][0]
        self.assertIn("Links to datasets", sent[-1]["content"])
        self.assertIn("compare what each covers", sent[0]["content"])


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
