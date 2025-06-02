#!/usr/bin/env python3
"""
简化测试复现问题
"""

import unittest
from apps.awr_parser.parsers.factory import create_parser
from apps.awr_parser.parsers.oracle_19c import Oracle19cParser
from pathlib import Path

class TestSimpleDebug(unittest.TestCase):
    
    def test_simple_oracle_19c_parsing(self):
        """简化的19c解析测试"""
        awr_file = Path("awrrpt/19c/awrrpt_1_17676_17677.html")
        
        with open(awr_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 这里复现错误
        parser = create_parser(content)
        print(f"DEBUG: parser = {parser}")
        self.assertIsInstance(parser, Oracle19cParser, 
                            f"Expected Oracle19cParser for {awr_file}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 