# -*- coding: utf-8 -*-
"""index.html + game/*.js 를 파일 하나로 합친다 → 지하철게임_9호선.html
파일 하나만 있으면 어디서든 열린다."""
import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")
board = (ROOT / "game" / "board.js").read_text(encoding="utf-8")
game = (ROOT / "game" / "game.js").read_text(encoding="utf-8")
html = html.replace(
    '<script src="game/board.js"></script>\n<script src="game/game.js"></script>',
    "<script>\n%s\n</script>\n<script>\n%s\n</script>" % (board, game))
assert "game/board.js" not in html
out = ROOT / "지하철게임_9호선.html"
out.write_text(html, encoding="utf-8")
print("→ %s (%.0f KB)" % (out.name, out.stat().st_size / 1024))
