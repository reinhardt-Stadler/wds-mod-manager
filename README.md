# 🎖️ WDS Mod Manager

一条命令安装 / 切换 / 回滚 WDS 兵棋美化包，告别手动复制粘贴数百个 BMP 的日子

---

✨ 功能亮点

- **智能路径匹配** — 自动识别 mod 目录结构，按"国家/功能类别"对应游戏目录，大小写、空格、连字符差异自动归一
- **交互式审查** — 安装前逐组确认映射，可改目标、可跳过、可展开看单文件，绝不盲目覆盖
- **安全可逆** — 原版文件自动备份，任何操作都能 `undo` 回退
- **多包共存** — 多个美化包叠加管理，支持跨包混搭（A 的阵营贴图 + B 的地图贴图）
- **交互式终端** — 输入 `wds` 进入 REPL，持续执行命令无需重复敲前缀
- **配置透明** — 所有备份与状态数据集中在游戏目录的 `_backup/`，无隐形文件、无残留

---

🖥️ 环境要求

- Windows 10 / 11
- Python 3.10+（推荐 3.12+）
- WDS 系列游戏（Panzer Campaigns / Panzer Battles 等）

---

🛠️ 安装方式

```
git clone https://github.com/reinhardt-Stadler/wds-mod-manager.git

cd wds-mod-manager

pip install -e .
```

或直接双击项目根目录的 `install.bat` 一键安装。

安装完成后，在任意终端（或资源管理器地址栏）输入 `wds` 即可启动。

---

🍓 简易使用

```
C:\> wds
```

进入交互界面后直接敲命令：

```
wds> install "D:\Mods\Hawkeyes_P39_Mod_V2"   安装美化包（交互式审查）
wds> status P39                                查看安装状态
wds> switch hawkeyes_p39_mod_v2 --off          临时禁用
wds> switch hawkeyes_p39_mod_v2 --on           重新启用
wds> uninstall hawkeyes_p39_mod_v2             卸载（还原原版）
wds> undo                                      撤销上一步
wds> q                                         退出
```

也可以不进入交互模式，直接执行单条命令：

```
C:\> wds scan "D:\Mods\Hawkeyes_F40_Mod"
C:\> wds install "D:\Mods\Hawkeyes_F40_Mod" --auto
```

---

📌 常用命令

```
scan <mod路径>              扫描 mod，展示路径映射表（只读，不修改文件）

install <mod路径>           安装美化包（交互式路径审查）
install <mod路径> --auto    安装美化包（全自动，跳过审查）
install <mod路径> -g P39    手动指定目标游戏
install <mod路径> -n 别名   设置美化包别名

status [游戏ID]             查看美化包安装状态（■已安装 / ◐部分 / □未安装）

uninstall <mod_id>          卸载美化包（还原原版文件）

switch <mod_id> --on        启用美化包
switch <mod_id> --off       禁用美化包

rename <mod_id> <名称>      修改美化包别名

ls-mods                     列出所有已注册美化包
ls-mods --all               含无 mod 的游戏

undo                        回退上一次操作
undo -g P39                 回退指定游戏的上一次操作
```

全局选项：`--wds-root <路径>` 指定游戏根目录（默认 `D:\WDS`，也可设环境变量 `WDS_ROOT`）

---

🗃️ 备份机制

所有操作均安全可逆。工具在游戏目录内创建 `_backup/` 文件夹：

```
游戏目录/
├── _backup/
│   ├── {游戏ID}_original/     原版文件全量备份（首次安装时创建）
│   ├── {mod_id}_{时间戳}/     安装前快照（多 mod 叠加回退链）
│   ├── {mod_id}_modfiles/     mod 文件副本（供 switch 重新启用）
│   ├── game_registry.json     注册表（工具状态数据库）
│   └── operation_log.json     操作日志（供 undo 使用）
├── German/                    游戏正常目录
├── Map/
└── ...
```

游戏 exe 完全忽略 `_backup/` 目录（已实证），不影响运行。

**注意：请勿手动删除 `_backup/` 文件夹，否则无法回退。**

---

🗑️ 卸载方式

#### 1. 自动卸载（推荐）

```
wds -un
```

会先询问是否还原所有已安装的美化包，然后卸载工具本身。

#### 2. 手动卸载

```
pip uninstall wds-mod-manager -y
```

**注意**：`pip uninstall` 只卸载全局命令，不会删除 git clone 下载的项目文件夹，也不会触碰游戏目录里的 `_backup/`。如需彻底清理，手动删除项目文件夹即可。游戏文件若想还原原版，请在卸载工具前先执行 `wds -un` 或 `wds uninstall <mod_id>`。

---

🔄 更新方式

#### 自动更新（推荐）

```
wds -u
```

此命令会自动从 GitHub 拉取最新版本并安装。

#### 手动更新

```
cd <项目文件夹路径>
git pull
pip install -e .
```

---

📖 完整文档

输入 `wds -help` 打开完整使用说明（含常见问题解答），***或查阅 `docs/使用说明.md`***。

---

📁 项目结构

```
wds-mod-manager/
├── src/wds/
│   ├── cli/
│   │   ├── app.py             主入口 + 交互 REPL + 自管理命令
│   │   ├── display.py         Rich 终端输出格式化
│   │   ├── install_cmd.py     install 命令逻辑
│   │   ├── manage_cmd.py      uninstall/switch/rename/ls-mods
│   │   ├── review.py          交互式路径审查
│   │   ├── scan_cmd.py        scan 命令逻辑
│   │   └── status_cmd.py      status 命令逻辑
│   ├── models.py              数据结构
│   ├── utils.py               工具函数
│   ├── scanner.py             游戏发现
│   ├── matcher.py             路径匹配引擎（类别优先）
│   ├── backup.py              备份管理
│   ├── registry.py            注册表管理
│   ├── installer.py           安装引擎
│   └── operation_log.py       操作日志（undo）
├── tests/                     344 个自动化测试
├── docs/使用说明.md           完整使用文档
├── pyproject.toml
└── README.md
```

---

⚖️ 许可证

Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.

私人项目，保留所有权利。未经作者书面许可，不得复制、修改、分发或用于商业用途。详见 [LICENSE](LICENSE)。
