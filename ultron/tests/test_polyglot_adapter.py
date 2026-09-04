"""
ultron.tests.test_polyglot_adapter
Unit test suite asserting multi-language AST, import extraction, and branch complexity across TS, JS, Go, and Python.
"""

import unittest
from ultron.core.polyglot_adapter import PolyglotAdapter, norm_path


class TestPolyglotAdapter(unittest.TestCase):
    """Unit tests for PolyglotAdapter."""

    def test_detect_language(self):
        """Asserts correct language identification from file paths."""
        self.assertEqual(PolyglotAdapter.detect_language("src/App.tsx"), "typescript")
        self.assertEqual(PolyglotAdapter.detect_language("src/api/client.ts"), "typescript")
        self.assertEqual(PolyglotAdapter.detect_language("web/modules/ui.js"), "javascript")
        self.assertEqual(PolyglotAdapter.detect_language("cmd/server/main.go"), "go")
        self.assertEqual(PolyglotAdapter.detect_language("ultron/core/hub.py"), "python")
        self.assertEqual(PolyglotAdapter.detect_language("README.md"), "unknown")

    def test_parse_typescript_imports_and_complexity(self):
        """Asserts TypeScript ES6/CJS import extraction, functions, and complexity."""
        ts_code = """
import React, { useState } from 'react';
import { Button } from '@/components/ui';
const lodash = require('lodash');

export class DashboardView {
    constructor() {}
}

export function calculateMetrics(a: number, b: number) {
    if (a > 0 && b > 0) {
        return a + b;
    } else if (a === 0 || b === 0) {
        return 0;
    }
    return -1;
}
"""
        res = PolyglotAdapter.parse_file("src/Dashboard.tsx", ts_code)
        self.assertEqual(res["language"], "typescript")
        self.assertIn("react", res["imports"])
        self.assertIn("@/components/ui", res["imports"])
        self.assertIn("lodash", res["imports"])
        self.assertEqual(len(res["classes"]), 1)
        self.assertEqual(res["classes"][0]["name"], "DashboardView")
        self.assertGreaterEqual(res["complexity"], 4.0)

    def test_parse_javascript_arrow_functions(self):
        """Asserts JavaScript arrow function extraction and dynamic imports."""
        js_code = """
const helper = () => {
    const dynamicMod = import('./dynamic');
    return true;
};
"""
        res = PolyglotAdapter.parse_file("utils.js", js_code)
        self.assertEqual(res["language"], "javascript")
        self.assertIn("./dynamic", res["imports"])
        self.assertEqual(len(res["functions"]), 1)
        self.assertEqual(res["functions"][0]["name"], "helper")

    def test_parse_go_package_and_methods(self):
        """Asserts Go package extraction, imports, structs, methods, and complexity."""
        go_code = """
package server

import (
    "fmt"
    "net/http"
)

type Router struct {
    port int
}

func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
    if req.Method == "GET" {
        fmt.Fprintf(w, "Hello")
    } else {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
    }
}
"""
        res = PolyglotAdapter.parse_file("cmd/server/main.go", go_code)
        self.assertEqual(res["language"], "go")
        self.assertEqual(res["package"], "server")
        self.assertIn("fmt", res["imports"])
        self.assertIn("net/http", res["imports"])
        self.assertEqual(len(res["classes"]), 1)
        self.assertEqual(res["classes"][0]["name"], "Router")
        self.assertEqual(len(res["functions"]), 1)
        self.assertEqual(res["functions"][0]["name"], "ServeHTTP")
        self.assertGreaterEqual(res["complexity"], 2.0)

    def test_parse_python_ast(self):
        """Asserts native Python AST parsing and complexity."""
        py_code = """
import os
from math import sqrt

class Matrix:
    pass

def solve(x):
    if x > 0:
        return sqrt(x)
    return 0
"""
        res = PolyglotAdapter.parse_file("matrix.py", py_code)
        self.assertEqual(res["language"], "python")
        self.assertIn("os", res["imports"])
        self.assertIn("math", res["imports"])
        self.assertEqual(len(res["classes"]), 1)
        self.assertEqual(len(res["functions"]), 1)
        self.assertGreaterEqual(res["complexity"], 2.0)

    def test_empty_and_unknown_language_resilience(self):
        """Asserts empty content or unknown extensions return safe schema without errors."""
        empty_res = PolyglotAdapter.parse_file("test.py", "")
        self.assertEqual(empty_res["complexity"], 1.0)
        self.assertEqual(empty_res["imports"], [])

        unknown_res = PolyglotAdapter.parse_file("config.yaml", "key: value")
        self.assertEqual(unknown_res["language"], "unknown")
        self.assertEqual(unknown_res["loc"], 1)


if __name__ == "__main__":
    unittest.main()
