# 项目结构

项目按照内容、资源、数据、文档、历史文件和构建产物划分职责。

## 内容层

`content/` 是构建器唯一扫描的 Markdown 根目录：

- `content/index.md`：提供首页说明；构建器会追加其余全部页面的分组列表。
- `content/ielts/chapters/`：IELTS 章节串记。
- `content/ielts/vocabulary-notebooks/`：生词本与复习材料。
- `content/ielts/phrase-notebooks/`：词伙和短语材料。
- `content/ielts/vocabulary-list.md`：雅思词汇真经总表。
- `content/writing/`：IELTS 写作词伙。
- `content/junior-high/`：初中阶段英语内容。

除 `index.md` 外，Markdown 在 `dist/` 中保持相同相对结构并改为 `.html` 扩展名。

## 资源层

- `assets/css/`：页面样式。
- `assets/js/`：页面交互脚本。
- `assets/images/`：按单词或词组命名的 `.jpg` 图片。

构建器创建 `dist/assets -> ../assets`，因此所有资源只有一份。页面可通过 `dist/assets/...` 访问，不复制 CSS、JavaScript 或图片。

## 数据与文档

- `data/`：CSV 与口语例句等结构化数据。`spoken-usage.jsonl` 保存中英例句及可选的 `focus` 核心短语，并在图片索引生成时合入每个词条的 `spoken` 字段；`shared-example-reuse.jsonl` 只记录复用已有例句的目标词与锚点词。
- `tools/`：数据生成和校验脚本，不参与网页编译。
- `docs/`：项目结构、内容索引和维护说明，不参与网页构建。
- `archive/`：历史 HTML 和笔记，仅供留档。

## 构建层

`build_site.py` 负责：

- 扫描 `content/**/*.md`。
- 使用 SHA-256 内容哈希识别新增、修改和未变化文件。
- 清理源文件删除后遗留的 HTML。
- 将 Markdown 内部 `.md` 链接转换为 `.html`。
- 自动生成包含全部静态学习页面的 `dist/index.html` 目录。
- 生成图片索引 `word-images.js` 和 `__word_images__.json`，并合入口语例句。
- 创建 `dist/assets` 目录链接。

构建状态保存在 `dist/.build-state.json`。
