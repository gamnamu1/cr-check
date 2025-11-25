import unittest
from json_parser import robust_json_parse

class TestRobustJsonParse(unittest.TestCase):
    def test_valid_json(self):
        text = '{"key": "value"}'
        result = robust_json_parse(text)
        self.assertEqual(result, {"key": "value"})

    def test_missing_comma(self):
        # 쉼표 누락
        text = '{"key1": "value1" "key2": "value2"}'
        result = robust_json_parse(text)
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})

    def test_single_quotes(self):
        # 작은 따옴표 사용
        text = "{'key': 'value'}"
        result = robust_json_parse(text)
        self.assertEqual(result, {"key": "value"})

    def test_trailing_comma(self):
        # 후행 쉼표
        text = '{"key": "value",}'
        result = robust_json_parse(text)
        self.assertEqual(result, {"key": "value"})

    def test_markdown_block(self):
        # 마크다운 코드 블록
        text = '```json\n{"key": "value"}\n```'
        result = robust_json_parse(text)
        self.assertEqual(result, {"key": "value"})

    def test_unescaped_newlines(self):
        # 이스케이프되지 않은 개행 (json_repair가 처리 가능한지 확인)
        text = '{"key": "line1\nline2"}'
        result = robust_json_parse(text)
        self.assertEqual(result, {"key": "line1\nline2"})

if __name__ == '__main__':
    unittest.main()
