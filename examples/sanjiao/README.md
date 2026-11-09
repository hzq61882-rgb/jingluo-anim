# 10 手少阳三焦经 · 准确版 · 火音（30 秒）

- `make_sj.py`：逐帧生成 1920×1080 / 30fps 画面（背面观，右臂外展、手背朝向观众；左上角为头颈部右侧面放大）。
- `audio_sj.py`：生成 30 秒「火音」背景音乐（徵调五声 G A C D E，与 01/02 金音同一套合成方式：长音铺底 + 每穴一声钟磬 + 混响）。
- `10_三焦经_准确版_火音.mp4`：成品（H.264 + AAC，30.0 秒）。
- `check_*.png`：3s / 10s / 18s / 27s 检查帧。

重新生成：
```bash
python3 audio_sj.py && python3 make_sj.py render
ffmpeg -i sj_noaudio.mp4 -i huo_sj.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -t 30 10_三焦经_准确版_火音.mp4
```
需要 Pillow、numpy、ffmpeg 和 Noto Sans CJK 字体。
