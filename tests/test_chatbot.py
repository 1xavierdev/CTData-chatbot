import unittest

from app import get_answer


class ChatbotTests(unittest.TestCase):
    def test_answer_for_capital(self):
        answer = get_answer("What is the capital of Connecticut?")
        self.assertIn("Hartford", answer)

    def test_answer_for_population(self):
        answer = get_answer("What is Connecticut's population?")
        self.assertIn("3.6 million", answer)

    def test_unknown_question(self):
        answer = get_answer("What is the weather today?")
        self.assertIn("I can help with Connecticut data", answer)


if __name__ == "__main__":
    unittest.main()
