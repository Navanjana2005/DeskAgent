import unittest
from unittest.mock import patch

from tools.file_tools import delete_file
from tools.messaging_app_automation import send_message_to_contact
from tools.security_tools import calculate
from tools.system_tools import shutdown_computer
import tools


class CalculateToolTests(unittest.TestCase):
    def test_supports_arithmetic_and_math_functions(self):
        self.assertIn("= 437", calculate.invoke({"expression": "23 * 19"}))
        self.assertIn("= 12.0", calculate.invoke({"expression": "sqrt(144)"}))
        self.assertIn("= 1.0", calculate.invoke({"expression": "cos(0)"}))

    def test_rejects_non_math_expressions(self):
        for expression in (
            "__import__('os').system('echo unsafe')",
            "pi.real",
            "[1, 2, 3]",
        ):
            with self.subTest(expression=expression):
                result = calculate.invoke({"expression": expression})
                self.assertIn("unsupported operation", result)

    def test_bounds_exponents(self):
        result = calculate.invoke({"expression": "2 ** 1001"})
        self.assertIn("Exponent magnitude", result)

    def test_destructive_tools_are_disabled_by_default(self):
        with patch.dict("os.environ", {"ALLOW_DANGEROUS_TOOLS": "0"}):
            self.assertIn(
                "File deletion is disabled",
                delete_file.invoke({"file_path": "unused"}),
            )
            self.assertIn(
                "Shutdown is disabled",
                shutdown_computer.invoke({}),
            )

    def test_message_tool_requires_explicit_confirmation(self):
        result = send_message_to_contact.invoke({
            "app_name": "whatsapp",
            "contact_name": "Example",
            "message": "Hello",
        })
        self.assertIn("Not sent", result)

    def test_registered_tool_names_are_unique(self):
        names = [registered_tool.name for registered_tool in tools.get_tools()]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("desktop_type_text", names)
        self.assertIn("desktop_scroll_page", names)


if __name__ == "__main__":
    unittest.main()
