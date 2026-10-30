#!/bin/bash
# 由已经压好的 MP4 再出一张循环 GIF。
# 用法: scripts/gif.sh input.mp4 output.gif 宽度 帧率 颜色数
# 例:   scripts/gif.sh chart.mp4 chart.gif 480 10 128
set -euo pipefail
if [ "$#" -ne 5 ]; then
  echo "用法: scripts/gif.sh input.mp4 output.gif 宽度 帧率 颜色数" >&2
  exit 2
fi
ffmpeg -y -loglevel error -i "$1" -vf "fps=$4,scale=$3:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=$5:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" -loop 0 "$2"
python3 - "$2" << 'PY'
import os, sys
# 十进制 MB，与 scripts/record.py 的上限同一把尺子（1 MB = 10^6 字节）。
print(f"{os.path.getsize(sys.argv[1]) / 1000000:.2f} MB")
PY
