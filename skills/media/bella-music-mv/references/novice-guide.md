# 新手指引

## 第一层：你只要提供两样东西

上传音乐文件，再上传或粘贴完整歌词，然后说：

> 使用 $bella-music-mv，把这首音乐和歌词做成完整动画 MV，其余由你决定。

agent 会先分析音乐、写分镜，确定角色和画风，再制作动画、检查动作和字幕、导出 MP4。它会告知方向，并继续完成，不需要你逐镜审批或运行命令。

默认是整首音乐、横屏 16:9、水彩墨线二维动画和 karaoke 歌词。你可以直接追加“竖屏”“不要字幕”“用我的角色”“冷色科幻风”等要求。想先看分镜再开工，就明确说“先给我看分镜，等我确认”。

歌词没有时间戳也能开始。初次时间分配会标为“估算”，agent 会根据可用的本地分析与抽查修正；这与有真实语音对齐依据的逐字时间不同。

## 第二层：你会收到什么

| 文件 | 你可以怎么用 |
|---|---|
| `out/video.mp4` | 完整成片，包含原曲及所选歌词字幕 |
| `STORYBOARD.md` | 中文分镜：每段在讲什么、如何转场 |
| 项目文件夹 | 可编辑角色、场景、歌词和时间设置，之后继续修改 |
| 检查图片、短片及记录 | 查看关键镜头、字幕与转场的实际检查结果 |

制作过程中的静帧、拼图和短预览用于检查，不是最终 MV。完整作品应覆盖前奏、演唱、间奏、尾奏，时长与原曲相符。

这套方式是让 agent 写动画程序，再逐帧渲染。它适合统一角色、明确节拍和有故事的二维 MV；默认不会变成拍摄实景、自动口型拟合或写实电影。你提供新的视觉要求时，agent 应先判断如何在现有底座里实现。

## 第三层：怎样提出修改最有效

直接告诉 agent 想改变的感受或具体时间点，例如：

- “0:35 的副歌更热闹一点，主角大一些。”
- “第二段动作太快，让我先看清角色发现了什么，再让它追过去。”
- “歌词比歌声慢半秒，后半首再核对一下。”
- “改成竖屏，主角和歌词都要在安全区。”
- “保留原曲和角色，换成夜晚到日出的色彩变化。”

无需理解 JS 或 p5.brush。一次修改可以只影响一个章节，agent 会更新相关镜头、重新检查，再输出完整成片。修改画幅、节拍或共享角色可能影响更多镜头，需要重新检查全片。

## 只有需要自己运行时再看命令

从 skill 所在目录运行；路径用实际文件替换，含空格时保留引号：

```bash
python3 scripts/mv.py doctor
python3 scripts/mv.py init --audio "/path/to/song.mp3" --lyrics "/path/to/lyrics.txt" --project "/path/to/my-mv"
python3 scripts/mv.py install --project "/path/to/my-mv"
python3 scripts/mv.py analyze --project "/path/to/my-mv"
```

接下来仍需要编码 agent 编写分镜与全部动画镜头。`init` 建立的占位工程不能直接当成作品；`analyze` 分析声音，不会自动画出歌曲的剧情。`install` 安装项目的 Node 依赖，已经装好时可以跳过。

全部场景完成后，由 agent 将 `src/config.js` 内 `PROJECT.status` 设为 `authored`，更新完成元数据；歌词被修改时先执行 `sync`。然后执行：

```bash
python3 scripts/mv.py sync --project "/path/to/my-mv"
python3 scripts/mv.py check --project "/path/to/my-mv"
python3 scripts/mv.py render --project "/path/to/my-mv"
python3 scripts/mv.py verify --project "/path/to/my-mv" --video out/video.mp4
```

需要 Node.js、Chrome 和 ffmpeg。水彩笔触在没有独立 GPU 的机器上也可能很慢；静帧检查快，并不代表整首歌马上渲染完。出错时把报错交给 agent 定位即可，不必先重装全部工具。
