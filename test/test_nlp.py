import unittest

class TestProofreading(unittest.TestCase):
    def assert_valid_label(self, label):
        """Valid labels are empty strings or match legal-style patterns like A, 1, a, i"""
        import re
        allowed = (
            label == ""
            or re.fullmatch(r"[A-Z]", label)
            or re.fullmatch(r"[a-z]", label)
            or re.fullmatch(r"\d+", label)
            or re.fullmatch(r"[ivxlcdm]+", label)  # Roman numerals
        )
        self.assertTrue(
            allowed,
            f"Invalid label: {label!r}. Expected '', 'A', '1', 'a', or similar.",
        )

    def test_labels_are_valid(self):
        parsed = [
            {
                "label": "Every ",
                "text": "person who is authorized or enjoined to arrest any person for a violation of this act is equally authorized or enjoined to seize an evidentiary copy of any obscene material or child sexual abuse material or all copies of explicit child sexual abuse material found in the possession of or under the control of the person so arrested and to deliver the obscene material or child sexual abuse material to the magistrate before whom the person so arrested is required to be taken."
            }
        ]
        for item in parsed:
            self.assertIn("label", item)
            self.assert_valid_label(item["label"])

    def test_text_is_not_empty(self):
        parsed = [
            {"label": "A", "text": "This is a valid statute clause."},
            {"label": "B", "text": ""},
        ]
        for item in parsed:
            self.assertIn("text", item)
            self.assertIsInstance(item["text"], str)
            self.assertGreater(len(item["text"].strip()), 0, f"Empty text for label {item['label']}")

    def test_required_fields_present(self):
        parsed = [
            {"label": "1", "text": "Valid clause."},
            {"label": "2"},  # missing "text"
        ]
        for item in parsed:
            self.assertIn("label", item)
            self.assertIn("text", item, f"Missing 'text' field for label {item.get('label')}")

    def test_label_and_text_types(self):
        parsed = [
            {"label": "a", "text": "Text is valid"},
            {"label": 1, "text": "Label should be str"},  # invalid
        ]
        for item in parsed:
            self.assertIsInstance(item["label"], str, f"Label is not a string: {item['label']!r}")
            self.assertIsInstance(item["text"], str, f"Text is not a string: {item['text']!r}")
