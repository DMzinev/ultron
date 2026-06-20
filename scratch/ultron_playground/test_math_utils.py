import unittest
from math_utils import add_elements, complex_operation, highly_coupled_calculator

class TestPlaygroundMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add_elements(5, 10), 15)
        
    def test_complex(self):
        self.assertEqual(complex_operation(10, 5, "subtract"), 5)
        
    def test_calculator(self):
        res = highly_coupled_calculator(5, 5, "add")
        self.assertEqual(res, 20)
        
if __name__ == "__main__":
    unittest.main()
