# Bug 分类和分配系统

一个可直接运行的单体项目，支持 Bug 提交、自动分类、自动分配、状态跟踪、团队成员维护和基础看板统计。

## 功能

- 新建 Bug 时自动分类：根据标题和描述关键字，自动识别为前端界面、后端服务、数据库、性能、安全、集成或其他。
- 自动分配负责人：优先分配给对应分类的专长成员，并按当前开放 Bug 数量和容量上限做负载均衡。
- Bug 列表筛选：支持按状态、分类、严重级别、负责人和关键字搜索。
- Bug 编辑与流转：支持手动修改分类、状态、负责人，并保留操作历史。
- 团队成员管理：支持新增成员、维护邮箱、专长、容量和启用状态。
- 仪表盘：查看总量、待处理、处理中、已关闭、分类分布和团队负载。
- 自带示例数据：首次启动会自动写入默认成员和示例 Bug，打开即可演示。

## 技术栈

- Python 3
- Flask
- SQLite
- Jinja2 模板

## 运行方式

```powershell
cd bug-triage-system
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

浏览器打开：`http://127.0.0.1:5000`

## 测试

```powershell
cd bug-triage-system
python -m unittest discover -s tests -v
```

## 目录结构

```text
bug-triage-system/
├─ app.py
├─ database.py
├─ requirements.txt
├─ README.md
├─ services/
│  ├─ assignment.py
│  └─ classification.py
├─ static/
├─ templates/
└─ tests/
```

## 说明

- 默认数据库文件为项目根目录下的 `bug_triage.db`。
- 如果你需要接入企业微信、邮件通知或更复杂的规则引擎，可以在当前结构上继续扩展。

