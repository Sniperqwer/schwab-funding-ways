"""Schwab 入金流程的可视化有向图.

节点 = (机构, 币种); 边分两种:
  transfer  同币跨机构 (FPS / CHATS / wire / ACH / 跨境支付通 / 存款)
  fx        异币同机构 (内部换汇)

改结构只需编辑下方 NODES / EDGES 两个列表, 然后重跑本脚本.
"""
from dataclasses import dataclass
from pathlib import Path
import webbrowser

from pyvis.network import Network


INSTITUTION_COLOR = {
    "origin":   "#d0d0d0",
    "中行":     "#ffadad",
    "中银香港": "#ffd6a5",
    "汇丰香港": "#caffbf",
    "Wise":     "#9bf6ff",
    "Schwab":   "#bdb2ff",
}
EDGE_COLOR = {"transfer": "#444444", "fx": "#e67e22"}


@dataclass
class Node:
    id: str
    label: str
    institution: str
    currency: str
    layer: int


@dataclass
class Edge:
    src: str
    dst: str
    instrument: str
    kind: str  # "transfer" | "fx"


NODES: list[Node] = [
    # layer 0: 资金起点
    Node("CNY_CASH",            "人民币",                "origin",   "CNY", 0),

    # layer 1: 大陆中行
    Node("BOC_CN_CNY",          "中行\nCNY",             "中行",     "CNY", 1),
    Node("BOC_CN_HKD",          "中行\nHKD",             "中行",     "HKD", 1),

    # layer 2: 中银香港 (离岸港口)
    Node("BOCHK_CNH",           "中银香港\nCNY",         "中银香港", "CNH", 2),
    Node("BOCHK_HKD",           "中银香港\nHKD",         "中银香港", "HKD", 2),
    Node("BOCHK_USD",           "中银香港\nUSD",         "中银香港", "USD", 2),

    # layer 3: 汇丰香港 (配置中心)
    Node("HSBC_CNH",            "汇丰香港\nCNY",         "汇丰香港", "CNH", 3),
    Node("HSBC_HKD",            "汇丰香港\nHKD",         "汇丰香港", "HKD", 3),
    Node("HSBC_USD",            "汇丰香港\nUSD",         "汇丰香港", "USD", 3),

    # layer 4: Wise
    Node("WISE_HKD",            "Wise\nHKD",             "Wise",     "HKD", 4),
    Node("WISE_USD",            "Wise\nUSD",             "Wise",     "USD", 4),

    # layer 5: Schwab 三个收款端点
    Node("SCHWAB_CITI_HK",      "Schwab\nCiti HK",       "Schwab",   "HKD", 5),
    Node("SCHWAB_CITIBANK_NYC", "Schwab\nCitibank NYC",  "Schwab",   "USD", 5),
    Node("SCHWAB_JPM_SF",       "Schwab\nJPM SF",        "Schwab",   "USD", 5),
]


EDGES: list[Edge] = [
    # ---- transfer 边 (同币跨机构) ----
    Edge("CNY_CASH",    "BOC_CN_CNY",           "存入",            "transfer"),
    Edge("CNY_CASH",    "BOC_CN_HKD",           "购汇+存入",       "transfer"),
    Edge("BOC_CN_CNY",  "BOCHK_CNH",            "跨境支付通",      "transfer"),
    Edge("BOC_CN_HKD",  "BOCHK_HKD",            "跨境支付通",      "transfer"),
    Edge("BOCHK_CNH",   "HSBC_CNH",             "FPS",             "transfer"),
    Edge("BOCHK_HKD",   "HSBC_HKD",             "FPS",             "transfer"),
    Edge("BOCHK_USD",   "HSBC_USD",             "CHATS USD",       "transfer"),
    Edge("HSBC_HKD",    "WISE_HKD",             "FPS",             "transfer"),
    Edge("HSBC_HKD",    "SCHWAB_CITI_HK",       "FPS→Citi HK",     "transfer"),
    Edge("HSBC_USD",    "SCHWAB_CITIBANK_NYC",  "wire→Citibank NYC", "transfer"),
    Edge("WISE_USD",    "SCHWAB_JPM_SF",        "ACH",             "transfer"),

    # ---- fx 边 (异币同机构, 换汇) ----
    Edge("BOCHK_CNH",   "BOCHK_HKD",            "换汇",            "fx"),
    Edge("BOCHK_CNH",   "BOCHK_USD",            "换汇",            "fx"),
    Edge("BOCHK_HKD",   "BOCHK_USD",            "换汇",            "fx"),
    Edge("HSBC_CNH",    "HSBC_HKD",             "换汇",            "fx"),
    Edge("HSBC_CNH",    "HSBC_USD",             "换汇",            "fx"),
    Edge("HSBC_HKD",    "HSBC_USD",             "换汇",            "fx"),
    Edge("WISE_HKD",    "WISE_USD",             "换汇",            "fx"),
]


VIS_OPTIONS = """{
  "layout": {
    "hierarchical": {
      "enabled": true,
      "direction": "LR",
      "sortMethod": "directed",
      "levelSeparation": 280,
      "nodeSpacing": 160,
      "treeSpacing": 220,
      "blockShifting": true,
      "edgeMinimization": true,
      "parentCentralization": true,
      "shakeTowards": "roots"
    }
  },
  "physics": { "enabled": false },
  "edges": {
    "smooth": { "type": "cubicBezier", "forceDirection": "horizontal", "roundness": 0.45 },
    "arrows": { "to": { "enabled": true, "scaleFactor": 0.65 } }
  },
  "nodes": {
    "borderWidth": 2,
    "borderWidthSelected": 3,
    "shape": "box",
    "font": { "size": 14, "face": "Helvetica, Arial, PingFang SC", "color": "#222" },
    "margin": 14,
    "shapeProperties": { "borderRadius": 8 },
    "widthConstraint": { "minimum": 110 }
  },
  "interaction": { "hover": true, "zoomView": true, "dragView": true, "tooltipDelay": 80 }
}"""


def build_graph(nodes: list[Node], edges: list[Edge],
                output: str = "flow_graph.html") -> Path:
    net = Network(
        directed=True, height="720px", width="100%",
        bgcolor="#fafafa", font_color="#222",
        cdn_resources="in_line",
    )
    for n in nodes:
        bg = INSTITUTION_COLOR.get(n.institution, "#eeeeee")
        net.add_node(
            n.id, label=n.label, level=n.layer,
            shape="box",
            color={"background": bg, "border": "#555",
                   "highlight": {"background": bg, "border": "#000"}},
            title=f"{n.institution} · {n.currency}",
        )
    fx_seen: dict[str, int] = {}
    for e in edges:
        is_fx = e.kind == "fx"
        kwargs = dict(
            label=e.instrument,
            title=f"{e.kind}: {e.instrument}",
            color={"color": EDGE_COLOR.get(e.kind, "#888")},
            dashes=is_fx,
            width=1 if is_fx else 1.8,
            font={"size": 10 if is_fx else 12,
                  "color": "#a04500" if is_fx else "#222",
                  "strokeWidth": 5, "strokeColor": "#fafafa",
                  "align": "middle"},
        )
        if is_fx:
            # 同源多条 FX 边轮流向左/右扇出, 越远的目标弯得越大, 避免重叠
            idx = fx_seen.get(e.src, 0)
            fx_seen[e.src] = idx + 1
            kwargs["smooth"] = {
                "enabled": True,
                "type": "curvedCW" if idx % 2 == 0 else "curvedCCW",
                "roundness": 0.25 + 0.25 * (idx // 2),
            }
        net.add_edge(e.src, e.dst, **kwargs)
    net.set_options(VIS_OPTIONS)
    path = Path(output)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    net.save_graph(str(path))
    return path


if __name__ == "__main__":
    out = build_graph(NODES, EDGES)
    print(f"已生成: {out}")
    webbrowser.open(f"file://{out}")
