# 技术路线与可靠导出

先用用户能判断的结果来推荐：想让观众看见什么、需要真实产品操作还是概念演示、是否反复改文案和比例、能接受多长渲染时间。说明推荐理由后由助手实施，不要求新手回答“要 GSAP 还是 Remotion”。保留用户已经明确的技术选择。

| 路线 id | 用户得到的好处 | 适合 | 实际限制 | 开工检查 |
|---|---|---|---|---|
| `native-html` | 快速得到清晰、易改的图形动画；依赖少 | 字幕、流程、数据图形、简洁产品宣传 | 复杂时间线要自行组织；Canvas 中文排版要主动检查 | Python 3.10+、Node 20+、Playwright/Chromium、FFmpeg/ffprobe |
| `gsap` | 连续变形、拖拽手势和卡点更容易保持一致 | UI 演示、一镜到底、动态排版 | 库本身不导出视频；自动播放的时间线不能稳定逐帧抓取 | 上述工具 + 本地 GSAP 包 |
| `remotion` | 文案、截图、语言和比例可做成参数，适合批量改版 | React/TS 团队、组件化多场景宣传片 | 需要 React 工程；版本应配套；按官方许可判断商业使用条件 | Node、npm、同版 `remotion` / `@remotion/cli`、可启动的浏览器 |
| `threejs` | 产品能旋转、拆解，镜头可以穿行空间 | 3D 产品、材质、空间叙事、程序化环境 | WebGL 在无头环境可能走软件渲染；复杂透明/阴影成本高；不应把简单 UI 强行 3D 化 | 浏览器工具 + Three.js；先测本机渲染能力 |
| `blender` | 细致材质、灯光、景深和复杂三维更有把握 | 精细产品广告、离线高质量 3D、真实光照 | 建模和渲染慢；GPU、版本、字体与资源路径影响输出 | `blender --version`、所选渲染设备、测试帧；FFmpeg/ffprobe |
| `hybrid` | 观众看到真实产品、真人或实物，信任感更强 | 软件实录、客户案例、实拍与图形混剪 | 需要实际录屏/素材；先确认素材内容、尺寸和使用范围；转场需处理不同比例与帧率 | 可用本地素材、FFmpeg/ffprobe；需要时调用录屏工具 |

## 工程与检查工具

`scripts/promo.py` 只用 Python 标准库，可独立运行，不依赖其他 Bella 技能。

```bash
python3 /path/to/bella-product-promo/scripts/promo.py doctor
python3 /path/to/bella-product-promo/scripts/promo.py list --kind styles
python3 /path/to/bella-product-promo/scripts/promo.py list --kind tech
python3 /path/to/bella-product-promo/scripts/promo.py init --project "/absolute/path/My Product" --product "产品名" --url "https://example.com" --style auto --tech native-html --duration 15 --fps 30 --aspect 9:16
```

`init` 的可选参数：`--product`、`--url`、`--style`、`--tech`、`--duration`、`--fps`、`--aspect`、`--width`、`--height`。默认 20 秒、30 fps、16:9、`style_id=auto`、`tech_id=native-html`。`auto` 表示由助手继续选择风格；传具体风格时必须是 `presets.json` 中的 id。自定义宽高必须一起给出、为偶数且符合所选比例。时长乘帧率必须为整数帧。目标目录已存在时拒绝覆盖。

工程记录 `brief.json`，包含 `schema_version=1`、`product`、`url`、`style_id`、`tech_id`、`duration`、`fps`、`aspect`、`width`、`height`、`status`、`audio`。`audio` 为相对工程目录的本地文件路径或 `null`。初始化的状态是 `unstarted`，只有实际编写内容后才能改为 `authored`。`engine/` 是工作入口；脚手架没有默认营销画面。

```bash
python3 /path/to/skill/scripts/promo.py check --project "/absolute/path/My Product"
python3 /path/to/skill/scripts/promo.py verify "/absolute/path/My Product/output.mp4" --project "/absolute/path/My Product" --expect-audio
```

`check` 是静态完整性检查，阻止未制作状态、占位入口、无内容的其他技术工程。不能替代真实画面审阅。`verify` 调用真实 ffprobe，读取视频流的尺寸、平均帧率、时长、帧数和音频流，对照 brief 检查。`--expect-audio` 用于有声交付；不传 `--project` 时仅核验基本媒体结构。`FFMPEG`、`FFPROBE` 环境变量可以指定可执行文件绝对路径，脚本不会自动安装或修改系统配置。

## 共用浏览器起步工程：仅 native-html / gsap / threejs

这三条路线初始化时会复制 `assets/browser-starter/`。内置的是时间定位与逐帧输出协议；助手仍要把产品叙事、场景、文字、镜头和音轨写出来。Remotion、Blender 和 hybrid 初始化仅创建 brief、assets 与空 engine 目录，使用下文各自的出口，没有伪装成可用的统一引擎。

在生成的工程目录安装：

```bash
npm install
npx playwright install chromium
```

起步工程精确固定 Playwright `1.64.1`，GSAP 路线添加 `3.15.0`，Three.js 路线添加 `0.186.1`；版本于 2026-10-26 从官方 npm registry 核验。保留首次安装得到的 lockfile，后续用 `npm ci`。不依赖远程 CDN。GSAP 可从 `../node_modules/gsap/dist/gsap.min.js` 引入全局 `gsap`；Three.js 可在模块中从 `../node_modules/three/build/three.module.js` 引入。升级时先查官方版本并重做小样，不把本文件中的版本当作永久最新。

### 场景协议

- `engine/index.html` 公开 `async window.seek(t)`，`t` 以秒计。任意时刻可独立调用；`seek(0) → seek(10) → seek(0)` 应得到相同首帧。用固定种子的随机值或解析函数；粒子和物理状态应按时间计算，不能依赖此前调用次数。
- 每帧固定 brief 中的宽高、帧率，DPR 为 1。不得把 CSS 自适应尺寸或系统像素比当交付尺寸。
- 原生 Canvas/SVG/CSS：按 `t` 绘制/赋值；CSS Animation 使用暂停的动画并设置 `currentTime`。不要让 `requestAnimationFrame` 的实时时钟驱动画面。
- GSAP：创建暂停时间线，再在 `seek(t)` 里设置 `timeline.time(t, false)`；为每次重定位恢复完整状态，避免回调累加或依赖正向经过事件。
- Three.js：按 `t` 设置位置、材质与相机，随后 `renderer.render(scene, camera)`。纹理先预载；需要时让 GPU 完成提交。不要只更新相机却等下一次实时循环才绘制。
- `seek(t)` 等待字体、图片和其他资源就绪；可调用 `protocol.js` 的 `waitForAssets()`。动态添加的图片每次也要等待；视频需显式定位时间、等 `seeked` 与帧就绪。不要依赖浏览器自动播放音频，也不要靠录制播放中的网页捕获音轨。
- 用独立音频文件合成最终音轨；程序合成音效/音乐也应先输出 WAV。指定听得见的声画节点，按相同时间轴核对。静音片可令 `audio=null`，明确其交付是静音。

写完场景，移除入口中的 `BELLA_PROMO_UNAUTHORED` 占位并把状态设为 `authored`。这只是允许导出，不能证明已达到交付质量。

```bash
node render.mjs --project . --output output.mp4 --audio assets/music.wav
node render.mjs --project . --output output-blur.mp4 --audio assets/music.wav --samples 4 --shutter 0.5
```

渲染器拒绝覆盖输出或帧目录。默认 `--samples 1`；可选 3 或 4 个子帧，`--shutter` 为 0–1 帧宽的曝光区间，样本在输出帧附近等距取样、边界截断后等权累积。它是轻量浏览器运动模糊近似，先比较文字清晰度与运行时间再使用。会先做首帧重定位一致性检查，再输出 PNG 序列，并调用 FFmpeg 用 H.264 / yuv420p / AAC 合成，保留帧以便 QA。短音频会补静音、长音频按 brief 时长截断；音乐结尾的淡出要在创作阶段设计。

`--frames DIR` 自定帧目录；`--frames-only` 仅输出帧供检查，不生成成片；`--ffmpeg PATH` 指定工具。所有输出路径相对 `--project`，也可使用绝对路径。失败后先查错误和已有帧，再选择新输出路径重试。脚本最终状态是 `rendered-unverified`；必须运行 `verify` 并查看分镜关键帧、片头片尾、密集文字和听感，才能交付。

## Remotion：使用项目自己的渲染器

先建实际 React/TS 工程和 Composition，尺寸、fps 与 `durationInFrames=duration×fps` 对照 brief。`useCurrentFrame()` 驱动状态；用项目音频组件与 Sequence 在同一帧轴排布。字体与素材使用其资源等待机制。对已有项目保留其依赖；新项目按官方创建流程，锁定相同版本的 Remotion 包，先 `npx remotion compositions src/index.ts` 确认入口和 composition id。此技能没有内置 Remotion 模板。

```bash
npx remotion render src/index.ts ProductPromo output.mp4 --codec h264
```

以上入口和 id 是说明格式，替换为工程实际值；在工程里设好正确的尺寸、时长、fps 后再导出。音频直接随 Composition 输出，不另录浏览器。批量版用 props JSON 文件，避免在 shell 中拼接含特殊字符的产品文案。完成后仍用 `promo.py verify` 对照 brief 检查。

## Blender：先测试帧，再渲染序列

在 `engine/` 放可重复运行的建场景脚本和/或 `.blend` 工程；固定随机种子、分辨率比例 100%、fps、起止帧、色彩管理、镜头和素材路径，记录实际使用的 Blender 版本。先低采样输出关键帧确认构图与材质，再用目标采样导出。设备不可用时选择可用的 CPU/渲染器并说明耗时，不承诺无头环境有 GPU。

```bash
blender --background --python engine/build_scene.py
blender --background engine/scene.blend --render-output //frames/frame_ --render-format PNG --render-anim
```

这些路径与文件必须由助手实际创建；命令行参数顺序会影响 Blender 行为。建议渲染无损序列再用 FFmpeg 按 brief 帧率合成；Blender 若从 1 开始编号，合成使用 `-start_number 1`。声音使用已制作 WAV/音乐文件，画面中的音画节点以帧号对应。复杂运动模糊优先使用 Blender 渲染器原生设置。不能把浏览器 `seek(t)` 渲染器直接用于 Blender。

## Hybrid：真实操作/实拍 + 图形与声音

先收集实际本地素材并用 ffprobe 查看尺寸、帧率、时长和音轨；若只有网站而无录屏，先实际录制所需交互，避免用虚构界面冒充产品操作。将需要的镜头转为统一尺寸和恒定帧率；按主体决定裁切或留边。界面上的客户信息等按素材实际情况处理。图形覆盖层可另行实现透明帧导出，或制作独立片段再合成。内置浏览器渲染器的截图默认带背景，H.264 成片不保留 alpha；需要透明序列时须专门设置透明画布/页面与 Playwright `omitBackground` 并检查实际 PNG alpha，当前 CLI 没有此选项。

常用最终合成格式（替换实际文件名、尺寸与时长；以下为 1920×1080、30fps、15秒）：

```bash
ffmpeg -n -i edited-visuals.mp4 -i soundtrack.wav -map 0:v:0 -map 1:a:0 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30" -af "apad=whole_dur=15" -t 15 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4
```

先剪好节奏再合成声音；保留 UI 点击反馈、讲解与音乐的层次，实际听取首尾与转场，不能只看到“存在 audio stream”就认为音效合格。需要横竖版时重排镜头与字幕安全区，避免机械裁切。

## 官方资料与安装核验

- [Playwright 安装与浏览器](https://playwright.dev/docs/intro)、[Node 支持与实际包版本](https://registry.npmjs.org/playwright/1.64.1)
- [GSAP 安装](https://gsap.com/docs/v3/Installation/)、[Timeline 时间定位](https://gsap.com/docs/v3/GSAP/Timeline/time/)、[固定包版本](https://registry.npmjs.org/gsap/3.15.0)
- [Three.js 安装](https://threejs.org/manual/#en/installation)、[固定包版本](https://registry.npmjs.org/three/0.186.1)
- [Remotion 创建工程](https://www.remotion.dev/docs/)、[CLI render](https://www.remotion.dev/docs/cli/render)、[许可](https://www.remotion.dev/license)
- [Blender 命令行](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html)
- [FFmpeg 下载](https://ffmpeg.org/download.html)、[FFmpeg 参数](https://ffmpeg.org/ffmpeg.html)、[ffprobe](https://ffmpeg.org/ffprobe.html)

工具可用性以当前机器的 `doctor`、实际启动和测试导出为准；有包名不代表浏览器已安装，也不代表三维 GPU 路径可用。
