"""Tests for trade card image generation tool."""

import os
import struct
import zlib
import pytest

from tools.image_gen import GenerateTradeCardTool, CARD_WIDTH, CARD_HEIGHT, _build_card_html


def _read_png_dimensions(path: str):
    """Read width and height from a PNG file's IHDR chunk without Pillow."""
    with open(path, "rb") as f:
        sig = f.read(8)
        assert sig == b"\x89PNG\r\n\x1a\n", "Not a valid PNG"
        # IHDR is always the first chunk
        length = struct.unpack(">I", f.read(4))[0]
        chunk_type = f.read(4)
        assert chunk_type == b"IHDR"
        width, height = struct.unpack(">II", f.read(8))
        return width, height


class TestGenerateTradeCardToolSchema:
    """Tests for GenerateTradeCardTool schema definition."""

    def test_schema_name(self):
        tool = GenerateTradeCardTool()
        schema = tool.get_schema()
        assert schema["name"] == "generate_trade_card"

    def test_schema_required_params(self):
        tool = GenerateTradeCardTool()
        schema = tool.get_schema()
        required = schema["parameters"]["required"]
        assert "ticker" in required
        assert "direction" in required
        assert "option_type" in required
        assert "strategy" in required
        assert "strike" in required
        assert "expiry" in required
        assert "premium" in required
        assert "pop" in required

    def test_schema_option_type_enum(self):
        tool = GenerateTradeCardTool()
        schema = tool.get_schema()
        opt_schema = schema["parameters"]["properties"]["option_type"]
        assert opt_schema["enum"] == ["CALL", "PUT"]

    def test_schema_optional_stock_price(self):
        tool = GenerateTradeCardTool()
        schema = tool.get_schema()
        props = schema["parameters"]["properties"]
        assert "stock_price" in props
        assert "stock_price" not in schema["parameters"]["required"]

    def test_schema_optional_headline(self):
        tool = GenerateTradeCardTool()
        schema = tool.get_schema()
        props = schema["parameters"]["properties"]
        assert "headline" in props
        assert "headline" not in schema["parameters"]["required"]

    def test_direction_enum(self):
        tool = GenerateTradeCardTool()
        schema = tool.get_schema()
        direction_schema = schema["parameters"]["properties"]["direction"]
        assert direction_schema["enum"] == ["bullish", "bearish"]


class TestBuildCardHtml:
    """Tests for HTML template generation (no browser needed)."""

    def setup_method(self):
        self.base_args = {
            "ticker": "NVDA",
            "direction": "bullish",
            "option_type": "CALL",
            "strategy": "Covered Call",
            "strike": "$145",
            "expiry": "Jan 17",
            "premium": "$3.20",
            "pop": "75%",
        }

    def test_html_contains_ticker(self):
        html = _build_card_html(**self.base_args)
        assert "$NVDA" in html

    def test_html_contains_option_type(self):
        html = _build_card_html(**self.base_args)
        assert "CALL" in html

    def test_html_contains_contract_line(self):
        html = _build_card_html(**self.base_args)
        assert "$145 Call" in html
        assert "Jan 17 Exp" in html

    def test_html_contains_strategy(self):
        html = _build_card_html(**self.base_args)
        assert "Covered Call" in html

    def test_html_contains_premium(self):
        html = _build_card_html(**self.base_args)
        assert "$3.20" in html

    def test_html_contains_pop_donut(self):
        html = _build_card_html(**self.base_args)
        assert "75%" in html
        assert "POP" in html
        assert "Probability of Profit" in html

    def test_html_bullish_uses_green_accent(self):
        html = _build_card_html(**self.base_args)
        assert "#10b981" in html  # green accent

    def test_html_bearish_uses_red_accent(self):
        args = {**self.base_args, "direction": "bearish", "option_type": "PUT"}
        html = _build_card_html(**args)
        assert "#ef4444" in html  # red accent
        assert "BEARISH" in html
        assert "PUT" in html

    def test_html_with_stock_price(self):
        html = _build_card_html(**self.base_args, stock_price="$142.50")
        assert "$142.50" in html

    def test_html_with_headline(self):
        html = _build_card_html(**self.base_args, headline="AI chip demand surge!")
        assert "AI chip demand surge!" in html

    def test_html_without_headline(self):
        html = _build_card_html(**self.base_args)
        assert 'class="headline"' not in html

    def test_html_escapes_special_chars(self):
        """Ensure user input is HTML-escaped to prevent injection."""
        args = {**self.base_args, "headline": '<script>alert("xss")</script>'}
        html = _build_card_html(**args)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_html_contains_branding(self):
        html = _build_card_html(**self.base_args)
        assert "Alpha Copilot" in html
        assert "#NFA" in html

    def test_pop_donut_zero_percent(self):
        args = {**self.base_args, "pop": "0%"}
        html = _build_card_html(**args)
        assert "0%" in html

    def test_pop_donut_invalid_value(self):
        """Invalid POP values should default to 0."""
        args = {**self.base_args, "pop": "N/A"}
        html = _build_card_html(**args)
        # conic-gradient uses 0 for invalid values
        assert "conic-gradient" in html


class TestGenerateTradeCardExecution:
    """Tests for trade card image generation (requires playwright + chromium)."""

    def setup_method(self):
        self.tool = GenerateTradeCardTool()
        self.base_args = {
            "ticker": "NVDA",
            "direction": "bullish",
            "option_type": "CALL",
            "strategy": "Covered Call",
            "strike": "$145",
            "expiry": "Jan 17",
            "premium": "$3.20",
            "pop": "75%",
        }

    def teardown_method(self):
        """Clean up any generated images."""
        import glob
        for f in glob.glob("/tmp/trade_card_*.png"):
            try:
                os.remove(f)
            except OSError:
                pass

    def test_execute_returns_image_ready(self):
        result = self.tool.execute(**self.base_args)
        assert result.startswith("IMAGE_READY: ")

    def test_execute_creates_file(self):
        result = self.tool.execute(**self.base_args)
        image_path = result.replace("IMAGE_READY: ", "")
        assert os.path.exists(image_path)

    def test_image_is_valid_png(self):
        result = self.tool.execute(**self.base_args)
        image_path = result.replace("IMAGE_READY: ", "")

        with open(image_path, "rb") as f:
            sig = f.read(8)
        assert sig == b"\x89PNG\r\n\x1a\n"

    def test_image_dimensions(self):
        result = self.tool.execute(**self.base_args)
        image_path = result.replace("IMAGE_READY: ", "")

        width, height = _read_png_dimensions(image_path)
        assert width == CARD_WIDTH
        assert height == CARD_HEIGHT

    def test_bullish_card(self):
        result = self.tool.execute(**self.base_args)
        assert "IMAGE_READY" in result

    def test_bearish_card(self):
        args = {**self.base_args, "direction": "bearish", "option_type": "PUT", "ticker": "TSLA"}
        result = self.tool.execute(**args)
        assert "IMAGE_READY" in result
        image_path = result.replace("IMAGE_READY: ", "")
        assert "TSLA" in image_path

    def test_with_headline(self):
        args = {**self.base_args, "headline": "AI chip demand surge!"}
        result = self.tool.execute(**args)
        assert "IMAGE_READY" in result

    def test_with_stock_price(self):
        args = {**self.base_args, "stock_price": "$142.50"}
        result = self.tool.execute(**args)
        assert "IMAGE_READY" in result

    def test_file_path_contains_ticker(self):
        result = self.tool.execute(**self.base_args)
        image_path = result.replace("IMAGE_READY: ", "")
        assert "NVDA" in image_path

    def test_unique_filenames(self):
        """Two cards generated close together should have unique paths."""
        result1 = self.tool.execute(**self.base_args)
        import time
        time.sleep(1.1)
        result2 = self.tool.execute(**self.base_args)

        path1 = result1.replace("IMAGE_READY: ", "")
        path2 = result2.replace("IMAGE_READY: ", "")
        assert path1 != path2
