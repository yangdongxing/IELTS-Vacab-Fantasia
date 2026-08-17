# IELTS-Vacab-Fantasia

一个本地 IELTS 词汇与词伙记忆工具。项目将 `content/` 中新增或变更的 Markdown 增量编译到 `dist/`，并提供翻译气泡、图片记忆卡、TTS、生词本和快捷键切词等交互。

## 构建

项目只使用一条构建命令：

```bash
python3 build_site.py build
```

构建完成后直接打开 `dist/index.html`。未变化的 Markdown 会被跳过，新增或修改的内容会生成对应 HTML，删除 Markdown 时也会清理旧 HTML。

## GitHub Pages

`main` 分支中影响站点的文件发生变化后，`.github/workflows/deploy-pages.yml` 会重新构建并发布 `dist/`。站点地址为：

<https://yangdongxing.github.io/IELTS-Vacab-Fantasia/>

首次使用时，需要在仓库的 **Settings > Pages > Build and deployment > Source** 中选择 **GitHub Actions**。也可以在 Actions 页面手动运行 `Deploy GitHub Pages`。

`dist/assets` 在仓库中仍是指向外层 `assets/` 的符号链接；Pages 官方上传 Action 会在打包时解引用该链接，因此线上产物包含完整 CSS、JavaScript 和图片，但仓库中仍只维护一份资源。

## 目录结构

```text
IELTS-Vacab-Fantasia/
├── README.md                     # 项目入口与目录说明
├── build_site.py                 # Markdown 增量构建器
├── content/                      # 需要编译的学习内容
│   ├── index.md                  # 自动汇总全部内容的静态站点首页
│   ├── ielts/
│   │   ├── chapters/             # IELTS 章节串记
│   │   ├── vocabulary-notebooks/ # 生词本与复习材料
│   │   ├── phrase-notebooks/     # 词伙与短语材料
│   │   └── vocabulary-list.md    # 雅思词汇真经总表
│   ├── writing/                  # IELTS 写作词伙
│   └── junior-high/              # 初中英语内容
├── assets/                       # 唯一静态资源库
│   ├── css/                      # 页面样式
│   ├── js/                       # 页面交互脚本
│   └── images/                   # 单词图片
├── data/                         # CSV 等原始数据
│   ├── spoken-usage.jsonl        # 图片词条的中英实用例句与来源
│   ├── guided-replacements.jsonl # 原模板句的人工策展替换
│   └── shared-example-reuse.jsonl # 仅复用已有例句的共享映射
├── tools/                        # 数据生成与校验工具
│   └── generate_spoken_usage.py  # 生成、保留和检查口语例句
│   └── curate_guided_usage.py    # 筛选和维护模板句替换
├── docs/                         # 项目维护文档
├── archive/                      # 不参与构建的历史资料
│   ├── legacy-html/              # 旧版 HTML 页面
│   └── notes/                    # 旧笔记与临时材料
└── dist/                         # 自动生成的静态站点
    ├── assets -> ../assets       # 资源目录链接，不复制资源
    ├── index.html
    ├── word-images.js
    └── __word_images__.json
```

## 目录职责

- 需要展示为网页的 Markdown 只放入 `content/`。
- CSS、JavaScript 和图片只保存在 `assets/`，避免重复数据。
- CSV 等生成来源放入 `data/`。
- 项目说明放入 `docs/`，不会被编译成学习页面。
- 旧文件放入 `archive/`，不会进入 `dist/`。
- `dist/` 是构建产物，不手工编辑其中的 HTML 或图片索引。
- `dist/index.html` 会自动列出其余所有学习页面，无需手工维护目录。

## 关键文件

- `assets/css/almond.css`：阅读页面基础样式。
- `assets/js/monkey-for-extensions.js`：翻译、TTS、生词本和快捷键交互。
- `assets/js/word-image-preview.js`：图片气泡与全屏记忆卡。
- `data/雅思词汇真经单词共3674个.csv`：原始词汇数据。
- `data/spoken-usage.jsonl`：图片词条的中英口语例句；构建时写入 `word-images.js`。
- `data/shared-example-reuse.jsonl`：人工复核后的目标词到已有例句锚点映射；不保存或创造新例句。
- `tools/generate_spoken_usage.py`：口语例句生成器和完整性校验器。

## 更多说明

- [项目结构](docs/project-structure.md)
- [内容索引](docs/content-index.md)
- [维护说明](docs/maintenance.md)
