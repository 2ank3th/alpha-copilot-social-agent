"""Tool for generating options trade card images using HTML/CSS rendering."""

import logging
import re
import time
import html as html_mod
from typing import Any, Dict

from .base import BaseTool

logger = logging.getLogger(__name__)

# Card dimensions (16:9 landscape — optimal for Twitter mobile feed)
CARD_WIDTH = 1200
CARD_HEIGHT = 675


def _render_html_to_png(html_content: str, output_path: str, width: int, height: int) -> None:
    """Render HTML string to a PNG file using Playwright."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.set_content(html_content, wait_until="networkidle")
        page.screenshot(path=output_path, type="png")
        browser.close()


def _build_card_html(
    ticker: str,
    direction: str,
    option_type: str,
    strategy: str,
    strike: str,
    expiry: str,
    premium: str,
    pop: str,
    stock_price: str = "",
    headline: str = "",
) -> str:
    """Build the HTML/CSS for an options trade card."""
    is_bullish = direction == "bullish"
    accent = "#10b981" if is_bullish else "#ef4444"
    accent_soft = "#d1fae5" if is_bullish else "#fee2e2"
    accent_glow = "rgba(16,185,129,0.15)" if is_bullish else "rgba(239,68,68,0.12)"
    badge_bg = "rgba(16,185,129,0.12)" if is_bullish else "rgba(239,68,68,0.10)"
    direction_label = direction.upper()

    # Parse POP
    try:
        pop_val = int(pop.replace("%", "").replace("~", "").strip())
    except ValueError:
        pop_val = 0
    pop_val = max(0, min(100, pop_val))

    # Normalize display values
    def _ensure_dollar(val: str) -> str:
        stripped = val.strip().lstrip("$").strip()
        return f"${stripped}" if stripped else val

    def _ensure_percent(val: str) -> str:
        stripped = val.strip().rstrip("%").strip()
        return f"{stripped}%" if stripped else val

    strike_display = _ensure_dollar(strike)
    premium_display = _ensure_dollar(premium)
    pop_display = _ensure_percent(pop)

    # Escape all user-provided text
    ticker = html_mod.escape(ticker)
    strategy = html_mod.escape(strategy)
    strike_display = html_mod.escape(strike_display)
    expiry = html_mod.escape(expiry)
    premium_display = html_mod.escape(premium_display)
    pop_display = html_mod.escape(pop_display)
    stock_price = html_mod.escape(stock_price)
    headline = html_mod.escape(headline)

    stock_price_html = f'<span class="stock-price">{stock_price}</span>' if stock_price else ""
    headline_html = f'<div class="headline">{headline}</div>' if headline else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    width: {CARD_WIDTH}px;
    height: {CARD_HEIGHT}px;
    background: radial-gradient(ellipse at top left, {accent_soft} 0%, #f0f5fc 40%, #eaf1fa 100%);
    font-family: -apple-system, "SF Pro Display", "Segoe UI", sans-serif;
    color: #0f172a;
    overflow: hidden;
    padding: 16px;
  }}

  .card {{
    width: 100%;
    height: 100%;
    background: #ffffff;
    border: 1px solid #dce8f5;
    border-radius: 24px;
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.10), 0 2px 8px rgba(15, 23, 42, 0.04);
    padding: 28px 36px 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
  }}

  .card::before {{
    content: "";
    position: absolute;
    top: -120px;
    right: -80px;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    background: radial-gradient(circle, {accent_glow} 0%, transparent 70%);
    pointer-events: none;
  }}

  /* ── Top section: two columns ── */
  .top {{
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 24px;
    align-items: center;
    position: relative;
    z-index: 1;
  }}

  .badges {{
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }}

  .badge {{
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}

  .badge-dir {{
    background: {badge_bg};
    color: {accent};
    border: 1.5px solid {accent}44;
  }}

  .badge-type {{
    background: #f1f5f9;
    color: #475569;
    border: 1.5px solid #d1dbe8;
  }}

  .ticker-row {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 6px;
  }}

  .ticker {{
    font-size: 72px;
    font-weight: 800;
    letter-spacing: -2px;
    line-height: 1;
  }}

  .stock-price {{
    font-size: 28px;
    color: #64748b;
    font-weight: 600;
  }}

  .contract {{
    font-size: 32px;
    font-weight: 700;
    color: {accent};
    line-height: 1.1;
    margin-bottom: 4px;
  }}

  .strategy {{
    font-size: 20px;
    color: #64748b;
    font-weight: 600;
  }}

  /* ── News banner at top ── */
  .headline {{
    background: {accent}0D;
    border: 1.5px solid {accent}33;
    border-radius: 12px;
    padding: 10px 16px;
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.25;
    margin-bottom: 6px;
  }}

  .headline::before {{
    content: "\\1F4F0\\00a0";
    font-size: 18px;
  }}

  /* ── POP donut ── */
  .pop-widget {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }}

  .pop-ring {{
    width: 184px;
    height: 184px;
    border-radius: 50%;
    background: conic-gradient({accent} 0 {pop_val}%, #e8eff8 {pop_val}% 100%);
    display: grid;
    place-items: center;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
  }}

  .pop-center {{
    width: 140px;
    height: 140px;
    border-radius: 50%;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }}

  .pop-num {{
    font-size: 48px;
    font-weight: 800;
    line-height: 1;
    color: #0f172a;
  }}

  .pop-label {{
    margin-top: 4px;
    font-size: 13px;
    letter-spacing: 1.2px;
    font-weight: 700;
    color: #64748b;
  }}

  .pop-caption {{
    font-size: 12px;
    color: #94a3b8;
    font-weight: 600;
  }}

  /* ── Bottom stats row ── */
  .stats {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }}

  .stat {{
    background: #f8fbff;
    border: 1px solid #e2ecf5;
    border-radius: 14px;
    padding: 18px 16px;
  }}

  .stat-label {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 4px;
  }}

  .stat-value {{
    font-size: 34px;
    font-weight: 700;
    color: #0f172a;
  }}

  .stat-value.premium {{
    color: #b45309;
  }}

  /* ── Footer ── */
  .footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 12px;
    border-top: 1px solid #e8f0f8;
  }}

  .footer-brand {{
    font-size: 18px;
    font-weight: 700;
    color: #2563eb;
  }}

  .footer-right {{
    font-size: 13px;
    color: #94a3b8;
    font-weight: 600;
  }}
</style>
</head>
<body>
  <div class="card">
    {headline_html}
    <div class="top">
      <div>
        <div class="badges">
          <div class="badge badge-dir">{direction_label}</div>
          <div class="badge badge-type">{option_type}</div>
        </div>
        <div class="ticker-row">
          <div class="ticker">${ticker}</div>
          {stock_price_html}
        </div>
        <div class="contract">{strike_display} {option_type.title()} &middot; {expiry} Exp</div>
        <div class="strategy">{strategy}</div>
      </div>

      <div class="pop-widget">
        <div class="pop-ring">
          <div class="pop-center">
            <div class="pop-num">{pop_display}</div>
            <div class="pop-label">POP</div>
          </div>
        </div>
        <div class="pop-caption">Probability of Profit</div>
      </div>
    </div>

    <div class="stats">
      <div class="stat">
        <div class="stat-label">Strike</div>
        <div class="stat-value">{strike_display}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Expiry</div>
        <div class="stat-value">{expiry}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Premium</div>
        <div class="stat-value premium">{premium_display}</div>
      </div>
    </div>

    <div class="footer">
      <div class="footer-brand">Alpha Copilot</div>
      <div class="footer-right">Options Trade &middot; #NFA</div>
    </div>
  </div>
</body>
</html>"""


class GenerateTradeCardTool(BaseTool):
    """Generate an options trade card image for social media posts."""

    name = "generate_trade_card"
    description = (
        "Generate a professional options trade card image showing the contract details "
        "(ticker, call/put, strike, expiry), premium, and POP. Returns path to generated PNG."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., NVDA)"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["bullish", "bearish"],
                        "description": "Trade direction"
                    },
                    "option_type": {
                        "type": "string",
                        "enum": ["CALL", "PUT"],
                        "description": "Option type: CALL or PUT"
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Options strategy (e.g., Covered Call, Cash-Secured Put, Sell Put)"
                    },
                    "strike": {
                        "type": "string",
                        "description": "Strike price (e.g., $145)"
                    },
                    "expiry": {
                        "type": "string",
                        "description": "Expiration date (e.g., Jan 17)"
                    },
                    "premium": {
                        "type": "string",
                        "description": "Premium amount (e.g., $3.20)"
                    },
                    "pop": {
                        "type": "string",
                        "description": "Probability of profit (e.g., 75%)"
                    },
                    "stock_price": {
                        "type": "string",
                        "description": "Current stock price for context (e.g., $142.50)"
                    },
                    "headline": {
                        "type": "string",
                        "description": "Optional news headline/hook for the card"
                    },
                },
                "required": ["ticker", "direction", "option_type", "strategy", "strike", "expiry", "premium", "pop"],
            },
        }

    def execute(
        self,
        ticker: str,
        direction: str,
        option_type: str,
        strategy: str,
        strike: str,
        expiry: str,
        premium: str,
        pop: str,
        stock_price: str = "",
        headline: str = "",
    ) -> str:
        """Generate options trade card image and return the file path."""
        try:
            html_content = _build_card_html(
                ticker=ticker,
                direction=direction,
                option_type=option_type.upper(),
                strategy=strategy,
                strike=strike,
                expiry=expiry,
                premium=premium,
                pop=pop,
                stock_price=stock_price,
                headline=headline,
            )

            timestamp = time.time_ns()
            image_path = f"/tmp/trade_card_{ticker}_{timestamp}.png"

            _render_html_to_png(html_content, image_path, CARD_WIDTH, CARD_HEIGHT)

            logger.info(f"Trade card generated: {image_path}")
            return f"IMAGE_READY: {image_path}"
        except Exception as e:
            logger.error(f"Failed to generate trade card: {e}")
            raise
