# 管内粒子与时间轴：读过什么，用了什么

2026-11-16 只读查看。没有克隆后改写这些仓库，没有 star、follow 或评论。数字只写在源文件里能对上的内容；各仓库 README 上的下载量、排名和片长宣传没有当作事实抄进来。

本仓库自己的 B/24 模板（`examples/b24-bamai-yuanli/template.html`）已经把粒子裁在色带多边形里，领头是白芯加一串沿路径后退的圆。增强版沿用这个约束：光点不能离开所属笔划。下面的参考仓库提供的是时间轴，不是另一套管线。

## 用了的机制

都是按公开许可重写的一小段，没有把对方的库打进页面，也没有复制品牌、音乐或字体文件。

| 来源 | 提交 | 许可 | 读过的文件 | 用了什么 |
| --- | --- | --- | --- | --- |
| [bangtutorial/bang-motion](https://github.com/bangtutorial/bang-motion)（fork [hzq61882-rgb/bang-motion](https://github.com/hzq61882-rgb/bang-motion)） | `c1aa65e921c970d858705fcb4a53a8294d1a4131` | MIT | `SKILL.md`「法律 #2」 | 画面是时间的函数。不用 `Math.random`，不按帧累加速度。拖动和逐帧导出看到同一帧。 |
| [givemotion/givemotion](https://github.com/givemotion/givemotion)（fork 同名） | `a2b02980f18d6392ce311acb7697751f43d4d429` | MIT | `src/runtime/runtime.js` 开头 | 虚拟时钟，`seek` 决定当前秒。没有注入它的运行时（它会换掉 `Date`、`Math.random` 和 `requestAnimationFrame`）。 |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)（fork [hzq61882-rgb/hyperframes](https://github.com/hzq61882-rgb/hyperframes)） | `6e0e03f542beacf758d8abe86f8a448f59b2ef1e` | Apache-2.0 | `docs/packages/player.mdx`，`docs/concepts/compositions.mdx` | 播放器可以 `seek` 到某一秒；渲染时不靠墙钟，渲染器按帧要画面。没有安装 `@hyperframes/player`，也没有用它文档里的 GSAP 时间轴示例。本仓库原来的 `renderAt(秒)` 继续承担这件事。 |
| [greensock/gsap-skills](https://github.com/greensock/gsap-skills)（fork [hzq61882-rgb/gsap-skills](https://github.com/hzq61882-rgb/gsap-skills)） | `aed9cfd3277740755f6bfc1155c7aa645403b760` | MIT | `skills/gsap-timeline/SKILL.md`「Controlling Playback」 | 暂停、跳到某一秒、跳到进度。页面里没有打包 GSAP。 |
| [oil-oil/oil-motion](https://github.com/oil-oil/oil-motion)（fork [hzq61882-rgb/oil-motion](https://github.com/hzq61882-rgb/oil-motion)） | `07e31f2265f80caa8f2c1df825d85ac24a46307c` | MIT | `SKILL.md`，`references/runtime.md` 的 frame-scrub | 拖动把输入映射到时间，松手停在那一帧。进度拖动用同一套 `seek`。 |

对应实现：`template/flow.js`。通用模板 `template/template.html` 用 `__FLOW__` 嵌进去，`scripts/build.py` 负责替换。B/4 圆环增强版由 `scripts/ring_enhance.py` 把同一份脚本和 `template/ring-pipes.js` 嵌进圆环版页面。

## 看过但没有搬进来

| 来源 | 提交 | 许可 | 原因 |
| --- | --- | --- | --- |
| [Vincentwei1021/mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15)（fork [hzq61882-rgb/mg-styles-15](https://github.com/hzq61882-rgb/mg-styles-15)） | `49052d80bfaf9fa8412cc9710530e5e95a3b8d8c` | MIT | `demos/07-liquid/js/shaders.js` 是整幅 WebGL 液体着色器，会盖住扫描图和标签。其他片子是片头风格，不是经络路径。 |
| [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) | `1482e8469b0a9e0d8cc18ea2740a01423d29ae80` | MIT | README 说明它做的是等轴机械剖视。本仓库 README 早已说明受它启发、不复制代码。这次也没有复制。 |
| [annnguyentt/anatomy-reveal-skill](https://github.com/annnguyentt/anatomy-reveal-skill) | 未把提交写进实现 | MIT | 拆件和爆炸镜头，不适合留在原扫描图上的循行。 |
| [threerocks/sweety-handdraw-video](https://github.com/threerocks/sweety-handdraw-video) | 未把提交写进实现 | MIT | 它重新画线稿并配音。这张图要保留扫描底图和已描好的路径。 |
| [Warrickchenxin/iso-explode-film](https://github.com/Warrickchenxin/iso-explode-film) | 未使用 | 许可证字段是 `NOASSERTION`，没有当成可复制的代码 | 等轴爆炸片，而且许可不明确。 |

账号下其余 fork 没有逐个克隆。挑选依据是目录和 README 是否涉及时间轴或沿路径流动，不是 star 数。
