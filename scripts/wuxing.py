"""五行配色。描矢量圆、太极和色块时用这一套，不要随扫描图的褪色取样。

木绿、火红、土黄、金白、水蓝。亮色填阳鱼或高光，暗色填阴鱼或描边，glow 用于脉动光晕。
B/28 成片用的是这张表。B/24 的五行圆是同一套色相、饱和度略高的近色，见 SKILL.md。
"""

WUXING = {
    '木': {'light': '#8fd16a', 'dark': '#2f8a3c', 'glow': '#3fdc5a', 'line': '#3fbf5a'},
    '火': {'light': '#ff9d92', 'dark': '#c0201c', 'glow': '#ff3b30', 'line': '#e53935'},
    '土': {'light': '#ffe46e', 'dark': '#caa005', 'glow': '#ffd60a', 'line': '#ffc400'},
    '金': {'light': '#ffffff', 'dark': '#c3c8d1', 'glow': '#ffffff', 'line': '#e8e8e8'},
    '水': {'light': '#7cc0ff', 'dark': '#1e5bb8', 'glow': '#2f80ff', 'line': '#2f80ff'},
}

# 相生、相克的固定次序。金生水、水生木收束成环。
SHENG = ['木', '火', '土', '金', '水']
KE = ['木', '土', '水', '火', '金']


def resolve(name, role='dark'):
    item = WUXING.get(name)
    if not item:
        return None
    return item[role]
