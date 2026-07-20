# WDS Mod Manager

WDS 系列兵棋游戏（Panzer Campaigns 等）的美化包管理工具。一条命令完成安装、切换、回滚，告别手动复制粘贴数百个 BMP 文件的日子。

## 功能

- 自动识别 mod 目录结构，智能匹配游戏内目标路径（类别优先 + 字符规范化）
- 交互式路径审查：逐组确认，支持修改目标、跳过、展开查看单文件
- 一键安装 / 卸载 / 启用 / 禁用，原版文件自动备份与还原
- 多 mod 叠加管理，支持跨 mod 混搭（A 的阵营贴图 + B 的地图贴图）
- `undo` 回退上一步操作
- 交互式 REPL：输入 `wds` 进入，持续执行命令无需重复输入前缀

## 环境要求

- Windows 10/11
- Python 3.10+（推荐 3.12+）
- WDS 系列游戏（Panzer Campaigns / Panzer Battles 等）

## 安装

**方式一：双击安装（推荐）**

```
双击项目根目录的 install.bat
```

**方式二：手动安装**

```cmd
pip install "路径\wds-mod-manager"
```

**方式三：开发模式（可编辑安装）**

```cmd
pip install -e "路径\wds-mod-manager"
```

安装完成后，在任意终端输入 `wds` 即可启动。

## 快速上手

```cmd
C:\> wds
```

进入交互界面后：

```
wds> install "D:\Mods\Hawkeyes_P39_Mod_V2"   安装美化包
wds> status P39                                查看状态
wds> switch hawkeyes_p39_mod_v2 --off          临时禁用
wds> switch hawkeyes_p39_mod_v2 --on           重新启用
wds> uninstall hawkeyes_p39_mod_v2             卸载（还原原版）
wds> undo                                      撤销上一步
wds> q                                         退出
```

也可以不进入交互模式，直接执行单条命令：

```cmd
C:\> wds scan "D:\Mods\Hawkeyes_F40_Mod"
C:\> wds install "D:\Mods\Hawkeyes_F40_Mod" --auto
```

## 命令一览

| 命令 | 说明 |
|------|------|
| `scan <mod路径>` | 扫描 mod，展示路径映射表（只读） |
| `install <mod路径>` | 安装美化包（交互式路径审查） |
| `install <mod路径> --auto` | 安装美化包（全自动） |
| `status [游戏ID]` | 查看美化包安装状态 |
| `uninstall <mod_id>` | 卸载美化包（还原原版） |
| `switch <mod_id> --on/--off` | 启用/禁用美化包 |
| `rename <mod_id> <名称>` | 修改美化包别名 |
| `ls-mods` | 列出所有已注册美化包 |
| `undo` | 回退上一次操作 |

全局选项：`--wds-root <路径>`（指定游戏根目录，默认 `D:\WDS`）

工具管理：`wds -u`（更新） / `wds -un`（卸载工具） / `wds -help`（完整文档）

## 备份机制

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

游戏 exe 完全忽略 `_backup/` 目录，不影响运行。**请勿手动删除此文件夹。**

## 项目结构

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

## 更新与卸载

```cmd
wds -u          从 GitHub 拉取最新版
wds -un         卸载工具（可选还原所有美化包）
```

## 许可证

私人项目，仅供个人使用。
