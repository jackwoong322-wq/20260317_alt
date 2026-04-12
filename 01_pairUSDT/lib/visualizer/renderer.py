import json
import re
import time
from pathlib import Path


def rewrite_dist_imports(dist_dir: Path, version: int) -> None:
    """dist/*.js 내 모든 상대 import 경로에 ?v=version 을 붙여 서브모듈 캐시 무효화."""
    for path in dist_dir.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        # from './xxx.js' / from "./xxx.js" → from './xxx.js?v=123' / from "./xxx.js?v=123"
        new_text = re.sub(
            r"from (['\"])(\.\/[^'\"]+\.js)\1",
            lambda m: f"from {m.group(1)}{m.group(2)}?v={version}{m.group(1)}",
            text,
        )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")


def generate_html(data_json: dict, script_version: int | None = None) -> str:
    template_path = Path(__file__).resolve().parents[2] / "templates" / "chart.html"
    template = template_path.read_text(encoding="utf-8")
    json_str = json.dumps(data_json, ensure_ascii=False)
    html = template.replace("__CHART_DATA__", json_str)
    # 페이지 로드 직후 F12 콘솔에 예측 데이터 출력 (인라인 스크립트로 캐시/로드 순서 무관)
    console_script = """
<script>
(function(){
  try {
    var out = {};
    for (var coinId in ALL_DATA) {
      var coin = ALL_DATA[coinId];
      (coin.cycles || []).forEach(function(c){
        var p = c.prediction_paths;
        if (p && ((p.bull && p.bull.length) || (p.bear && p.bear.length))) {
          var key = (coin.symbol || coinId) + '_cycle' + c.cycle_number;
          out[key] = p;
        }
      });
    }
    if (Object.keys(out).length) console.log('[예측 데이터] prediction_paths 전부:', out);
    else console.log('[예측 데이터] prediction_paths 없음 (DB coin_prediction_paths 확인)');
  } catch(e) { console.log('[예측 데이터] 오류:', e.message); }
})();
</script>
"""
    html = html.replace(
        "</script>\n<script type=\"module\"",
        "</script>" + console_script + "\n<script type=\"module\""
    )
    html = html.replace('href="chart.css"', 'href="templates/chart.css"')
    # 캐시 무효화: 메인·서브모듈 모두 같은 v= 사용 (Disable cache 없이 새로고침만으로 반영)
    ver = script_version if script_version is not None else int(time.time())
    html = html.replace('src="dist/chart.js"', f'src="templates/dist/chart.js?v={ver}"')
    # 템플릿에서는 IDE 경로를 맞추기 위해 ../pairUSDT/... 를 사용하지만,
    # 실제로 생성되는 HTML은 pairUSDT 루트에 위치하므로 ./pairUSDT/... 로 교체한다.
    html = html.replace("../pairUSDT/template_script.js", "./pairUSDT/template_script.js")
    return html
