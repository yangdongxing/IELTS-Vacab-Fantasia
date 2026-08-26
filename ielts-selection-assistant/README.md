# 雅思真经划词划划看 (IELTS Selection Assistant)

> 专为雅思考生打造的沉浸式划词标记与背词助手。在任意网页上划选英文段落，点击弹出的按钮即可**直接在正文中加粗标记真经核心词汇**（已加粗文本自动加波浪线区分），鼠标 Hover 展示 Tips 气泡与发音，点击微缩图展开全屏居中高清大图与原声例句记忆覆层，支持键盘拼写验证互动！

---

## 🚀 核心工作流

1. **选中文本**：用鼠标在任意网页上划选英文句子或段落。
2. **点击按钮**：选区右上角浮现 **【📖 标记真经 (N)】** 经典红色胶囊按钮。
3. **正文标注**：
   - 普通正文词汇：**直接加粗**（保持正文原色，不标红、无下划线）；
   - 原文已加粗词汇：**加粗 + 波浪下划线**进行精准区分。
4. **悬浮 Tips 气泡**：鼠标移至标记词上，平滑浮现暗色卡片（发音、中文释义、微缩配图，支持顶部边界智能避让）。
5. **全屏记忆覆层 (Modal)**：
   - 点击 Tips 中的微缩图，弹出全屏居中记忆卡片；
   - 包含高清大图、词目发音、真题语境例句（黄色考点词高亮与例句发音）；
   - 底部支持**单词拼写验证**：敲入正确单词后触发绿色对钩反馈与下落动画，停留 3 秒后自动平滑关闭覆层；
   - 随时可按 `ESC` 键或点击卡片外部遮罩快速退出。

---

## 🖼️ 启动本地图片服务 (推荐)

为保证在任意外部网站划词时所有 3,600+ 单词配图均可 **0 延迟本地秒开**，可以在终端中启动本地轻量图片服务：

```bash
cd ielts-selection-assistant
python3 serve_images.py
# 或者一键启动:
./start_server.sh
```

> **说明**：
> - 服务默认运行在 `http://127.0.0.1:8777/`，已开启全跨域 CORS 支持；
> - 若本地服务未开启，脚本会自动降级回退至远程 GitHub CDN，不影响基本功能。

---

## 📦 安装与使用方式

### 方式 A：油猴脚本 (Tampermonkey)
1. 打开浏览器并安装 **Tampermonkey** 扩展。
2. 打开 Tampermonkey 仪表盘，点击 **新建脚本**。
3. 复制 [`ielts-selection.user.js`](ielts-selection.user.js) 中的全部代码并粘贴保存。
4. 在任意英文网页（BBC、Medium、Wikipedia、知乎等）划选英文即可即时体验！

### 方式 B：Chrome 扩展程序 (Manifest V3)
1. 打开 Chrome 浏览器，访问 `chrome://extensions/`。
2. 开启右上角的 **开发者模式 (Developer Mode)**。
3. 点击 **加载已解压的扩展程序 (Load unpacked)**。
4. 选择当前文件夹 `ielts-selection-assistant/` 即可完成安装。

---

## 🧪 本地测试与预览
在浏览器中直接双击打开 [`test.html`](test.html)，划选测试段落并点击按钮即可即时体验完整交互与拼写背词功能！

---

## 🛠️ 项目构建与数据维护

如果更新了 `content/ielts/vocabulary-list.md` 或例句数据，只需在当前目录下重新运行打包器：

```bash
cd ielts-selection-assistant
python3 build.py
```
构建器将自动提取最新词库、形态还原映射表，并同步生成 `dictionary.json`、`content_script.js`、`ielts-selection.user.js` 以及 `test.html`。
