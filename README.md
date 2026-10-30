# 经络图流动画

把 J. Martin-Hartz 的经络、脉诊扫描图描成矢量，做成可循环播放的单文件 HTML，再导出 MP4、GIF 和 PNG。流程、配色和八张已完成的图都在这一个仓库里，换一张新扫描图时按同一套步骤重做。

完整步骤、每张图的线型与流向，写在 [SKILL.md](SKILL.md)。

原图作者为 **J. Martin-Hartz / Fondation Cornelius Celsus**。动画是按扫描图上的色带、线条和箭头做的示意，不是原作者的作品。

做法上受 [Anatomy](https://github.com/wheresryan22/anatomy)（MIT）的启发：把解剖或经络结构收成可播放的流动画面。本仓库没有复制它的代码。

## 快速开始

```bash
pip install -r scripts/requirements.txt
# 系统里需要 ffmpeg。嵌字体需要 Noto Sans CJK（fonts-noto-cjk）和 pyftsubset。
# 录制用本机的 Chrome；只装 Python 包时：pip install playwright

python scripts/build.py \
  --config template/config.json \
  --image path/to/clean.jpg \
  --out out/新图.html

python scripts/record.py --html out/新图.html --out-dir out --name 新图 --still-time 0
python scripts/verify_loop.py --html out/新图.html
```

`template/config.json` 是空起点：周期、图层、右上图例、页脚里的流向假定都留好了，`items` 为空。描完线之后把折线和圆填进去。页面自带播放/暂停、两档速度、图层开关；地址栏加 `?video=1` 只留画面，给录制用。

坐标一律用扫描图的原始像素，不要归一化。

## 八张成片

| 图号 | 名称 | 目录 | 周期 |
| --- | --- | --- | --- |
| B/4 | 脉诊图 | [examples/b4-maizhen](examples/b4-maizhen) | 24 秒 |
| B/28 | 五行六经图 | [examples/b28-wuxing-liujing](examples/b28-wuxing-liujing) | 24 秒 |
| B/31 | 寸关尺四季表里图 | [examples/b31-cunguan-siji](examples/b31-cunguan-siji) | 24 秒 |
| B/45 | 玉龍八法 | [examples/b45-yulong-bafa](examples/b45-yulong-bafa) | 24 秒 |
| B/1 | 玉龍 | [examples/b1-yulong](examples/b1-yulong) | 24 秒 |
| B/39 | 氣的循環奇經八脈圖 | [examples/b39-qi-qijing](examples/b39-qi-qijing) | 24 秒 |
| B/36 | 神應經穴法圖 | [examples/b36-shenying](examples/b36-shenying) | 24 秒 |
| B/24 | 把脈的原理 | [examples/b24-bamai-yuanli](examples/b24-bamai-yuanli) | 60 秒 |

每个目录里是成品单文件 HTML，以及描线得到的矢量或生成动画时用的 config。用浏览器直接打开 HTML 即可播放。

扫描原图已经嵌在对应 HTML 里，仓库不再另存一份。中间用的标签蒙版 `lbl28.npy`（约 3.8MB，不是矢量）和调试页没有放进来。打包时没有任何文件超过约 20MB，所以没有因体积被丢掉的成片或矢量。上传材料里本来就没有视频和单独的 PNG 序列。

## 脚本

| 脚本 | 作用 |
| --- | --- |
| `scripts/trace_mask.py` | 粗折线吸到色带中线 |
| `scripts/trace_strokes.py` | 直线、二次曲线吸到墨线 |
| `scripts/trace_dashes.py` | 把断开的虚线墨迹串起来 |
| `scripts/trace_hough.py` | 霍夫长直线 |
| `scripts/trace_arcs.py` | 拟合圆弧 |
| `scripts/overlay.py` | 按原图像素把矢量叠回扫描图 |
| `scripts/inpaint.py` | 擦手写，保住细线 |
| `scripts/labels.py` | 检查标签、叠字预览、切 Noto 子集 |
| `scripts/build.py` | 合成单文件 HTML |
| `scripts/record.py` | 录 HD MP4、GIF、静帧 PNG，并守住体积上限 |
| `scripts/verify_loop.py` | 对照循环首尾 |
| `scripts/gif.sh` | 从现成 MP4 再压一张 GIF |
| `scripts/wuxing.py` | 五行色：木绿、火红、土黄、金白、水蓝 |

路径都走命令行参数，不写死到某一台机器的目录。

## 许可

MIT，见 [LICENSE](LICENSE)。扫描图的署名仍是 J. Martin-Hartz / Fondation Cornelius Celsus，请在成片页脚保留。
