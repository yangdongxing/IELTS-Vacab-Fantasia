# 维护说明

## 唯一构建命令

```bash
python3 build_site.py build
```

构建入口为 `dist/index.html`。

## 增量规则

- 新增 `content/**/*.md`：生成同路径 HTML。
- 修改 Markdown：只重新编译发生变化的文件。
- 未变化 Markdown：跳过。
- 删除 Markdown：清理对应旧 HTML。
- 修改 `build_site.py`：自动重新编译全部内容。
- 新增或修改图片：自动更新图片索引。
- 新增、修改或删除内容：自动同步 `dist/index.html` 的完整页面列表。

## 修改入口

- 学习内容：`content/`
- 页面样式：`assets/css/almond.css`
- 阅读、TTS 与生词本：`assets/js/monkey-for-extensions.js`
- 图片与记忆卡：`assets/js/word-image-preview.js`
- 单词图片：`assets/images/`
- 原始 CSV：`data/`
- 中英实用例句：`data/spoken-usage.jsonl`
- 原模板句的策展替换：`data/guided-replacements.jsonl`
- 已有例句共享映射：`data/shared-example-reuse.jsonl`
- 例句生成与校验：`tools/generate_spoken_usage.py`
- 策展替换工具：`tools/curate_guided_usage.py`
- 构建逻辑：`build_site.py`

## 注意事项

- 不要手工修改 `dist/` 中的 HTML、图片索引或构建状态。
- `dist/assets` 是目录链接，不是第二份资源。
- 项目文档放在 `docs/`，不会进入静态学习站点。
- 历史文件放在 `archive/`，不会参与构建。

## 检查命令

```bash
python3 tools/generate_spoken_usage.py validate
python3 -m py_compile build_site.py
python3 build_site.py build
node --check assets/js/monkey-for-extensions.js
node --check assets/js/word-image-preview.js
```

## 口语例句

`data/spoken-usage.jsonl` 为每个唯一图片词条保存一条简短自然的英文例句和简体中文翻译。语料中的优质短句会保留原貌，不添加说明性前缀。已有条目默认保留，重新生成使用：

```bash
python3 tools/generate_spoken_usage.py build
```

`source: tatoeba` 的记录来自 Tatoeba 中英平行语料，并在记录内保留句子编号、作者与 CC BY 2.0 FR 归属信息；`curated` 和 `guided` 为项目整理内容。构建产物只包含朗读所需的中英文，不重复携带归属元数据。

原有的 779 条通用 `guided` 模板句已由 `data/guided-replacements.jsonl` 覆盖。`curated-corpus` 表示经过筛选和翻译的真实英文语料，`curated` 表示人工编写或人工优选句。主生成器会逐条校验替换清单，缺失、重复或内容不一致都会报错。

重新策展这组句子需要完整英文语料和网络翻译服务，使用：

```bash
python3 tools/curate_guided_usage.py build
python3 tools/curate_guided_usage.py validate
```

例句共享不受章节限制，会在全部图片词条中寻找能被同一句自然覆盖的单词。选择时优先考虑日常表达的自然度和实用性，再考虑一句覆盖的单词数量；不会为了提高共享数量使用生硬句子。

共享例句的每个单词仍保留独立记录，但使用相同的 `usage_id`、英文和中文，并通过 `shared_with` 标明同句词条。例如 `thoughtful` 与 `patient` 共用 `She is very thoughtful and patient.`。人工复核后的共享组合写在生成器的 `CURATED_SHARED` 中，并由校验器作为回归样例检查。

减少例句数量时，只允许复用 `data/spoken-usage.jsonl` 中已经存在的完整中英文句对。不得新增、改写、拼接、翻译或替换关键词来制造共享例句。人工复核通过后，在 `data/shared-example-reuse.jsonl` 中记录目标词和锚点词；构建时会原样复制锚点的英文、中文、来源和署名，并拒绝缺失或链式引用。

添加共享映射前，必须确认锚点句保留目标词当前释义和词性。仅仅出现同形词、派生形式或拼写相近的词，不构成共享理由；常用含义会被偏门含义替代时，也必须保留原例句。
