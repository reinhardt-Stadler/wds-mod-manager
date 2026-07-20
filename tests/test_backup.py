"""M05 backup.py 测试: 备份管理（全部在 tmp_path 中运行）"""

from pathlib import Path

import pytest

from wds.backup import (
    BACKUP_DIR_NAME,
    create_mod_backup,
    create_original_backup,
    ensure_backup_dir,
    has_original_backup,
    list_backups,
    restore_from_backup,
)
from wds.utils import collect_bmp_files


# ===========================================================================
# ensure_backup_dir
# ===========================================================================

class TestEnsureBackupDir:
    def test_creates_dir(self, mock_game_root: Path):
        backup = ensure_backup_dir(mock_game_root)
        assert backup.is_dir()
        assert backup.name == BACKUP_DIR_NAME
        assert backup.parent == mock_game_root

    def test_idempotent(self, mock_game_root: Path):
        b1 = ensure_backup_dir(mock_game_root)
        b2 = ensure_backup_dir(mock_game_root)
        assert b1 == b2
        assert b1.is_dir()

    def test_returns_path(self, mock_game_root: Path):
        result = ensure_backup_dir(mock_game_root)
        assert isinstance(result, Path)
        assert result == mock_game_root / BACKUP_DIR_NAME


# ===========================================================================
# create_original_backup
# ===========================================================================

class TestCreateOriginalBackup:
    def test_creates_backup_dir(self, mock_game_root: Path):
        result = create_original_backup(mock_game_root, "EP14")
        assert result.is_dir()
        assert result.name == "EP14_original"
        assert result.parent == mock_game_root / BACKUP_DIR_NAME

    def test_backs_up_all_bmps(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        backup_dir = mock_game_root / BACKUP_DIR_NAME / "EP14_original"
        # 备份中的 BMP 数量应与游戏中的一致
        game_bmps = collect_bmp_files(mock_game_root)
        backup_bmps = collect_bmp_files(backup_dir)
        assert len(backup_bmps) == len(game_bmps)

    def test_preserves_relative_structure(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        backup_dir = mock_game_root / BACKUP_DIR_NAME / "EP14_original"
        assert (backup_dir / "German" / "2DSymbolsLg.bmp").is_file()
        assert (backup_dir / "Info" / "BlankboxH.bmp").is_file()
        assert (backup_dir / "Map" / "2DFeatures50.bmp").is_file()

    def test_file_content_preserved(self, mock_game_root: Path):
        original = (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes()
        create_original_backup(mock_game_root, "EP14")
        backed = (mock_game_root / BACKUP_DIR_NAME / "EP14_original"
                  / "German" / "2DSymbolsLg.bmp").read_bytes()
        assert original == backed

    def test_idempotent(self, mock_game_root: Path):
        r1 = create_original_backup(mock_game_root, "EP14")
        r2 = create_original_backup(mock_game_root, "EP14")
        assert r1 == r2
        # 不应重复拷贝（文件数不变）
        backup_bmps = collect_bmp_files(r1)
        game_bmps = collect_bmp_files(mock_game_root)
        assert len(backup_bmps) == len(game_bmps)

    def test_excludes_backup_from_backup(self, mock_game_root: Path):
        """备份不应包含 _backup 目录本身的内容"""
        create_original_backup(mock_game_root, "EP14")
        backup_dir = mock_game_root / BACKUP_DIR_NAME / "EP14_original"
        # 不应有嵌套的 _backup
        assert not (backup_dir / BACKUP_DIR_NAME).exists()


# ===========================================================================
# has_original_backup
# ===========================================================================

class TestHasOriginalBackup:
    def test_false_initially(self, mock_game_root: Path):
        assert has_original_backup(mock_game_root, "EP14") is False

    def test_true_after_creation(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        assert has_original_backup(mock_game_root, "EP14") is True

    def test_different_game_id(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        assert has_original_backup(mock_game_root, "M41") is False


# ===========================================================================
# create_mod_backup
# ===========================================================================

class TestCreateModBackup:
    def test_creates_backup(self, mock_game_root: Path):
        files = {
            "German/2DSymbolsLg.bmp": mock_game_root / "German" / "2DSymbolsLg.bmp",
            "Info/BlankboxH.bmp": mock_game_root / "Info" / "BlankboxH.bmp",
        }
        result = create_mod_backup(mock_game_root, "test_mod", files)
        assert result.is_dir()
        assert result.parent == mock_game_root / BACKUP_DIR_NAME
        assert result.name.startswith("test_mod_")

    def test_backs_up_specified_files_only(self, mock_game_root: Path):
        files = {
            "German/2DSymbolsLg.bmp": mock_game_root / "German" / "2DSymbolsLg.bmp",
        }
        result = create_mod_backup(mock_game_root, "test_mod", files)
        assert (result / "German" / "2DSymbolsLg.bmp").is_file()
        # 不应备份其他文件
        assert not (result / "Info").exists()

    def test_content_preserved(self, mock_game_root: Path):
        original = (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes()
        files = {"German/2DSymbolsLg.bmp": mock_game_root / "German" / "2DSymbolsLg.bmp"}
        result = create_mod_backup(mock_game_root, "test_mod", files)
        backed = (result / "German" / "2DSymbolsLg.bmp").read_bytes()
        assert original == backed

    def test_timestamp_in_dirname(self, mock_game_root: Path):
        files = {"German/2DSymbolsLg.bmp": mock_game_root / "German" / "2DSymbolsLg.bmp"}
        result = create_mod_backup(mock_game_root, "hawkeyes_f40", files)
        # 目录名格式: hawkeyes_f40_YYYYMMDD_HHMMSS
        assert result.name.startswith("hawkeyes_f40_")
        parts = result.name.split("_")
        assert len(parts) >= 4  # hawkeyes, f40, date, time

    def test_empty_files_dict(self, mock_game_root: Path):
        result = create_mod_backup(mock_game_root, "empty_mod", {})
        assert result.is_dir()


# ===========================================================================
# restore_from_backup
# ===========================================================================

class TestRestoreFromBackup:
    def test_restore_all(self, mock_game_root: Path):
        # 先创建备份
        create_original_backup(mock_game_root, "EP14")
        # 修改一个游戏文件
        target = mock_game_root / "German" / "2DSymbolsLg.bmp"
        target.write_text("MODIFIED CONTENT")
        # 还原
        count = restore_from_backup(mock_game_root, "EP14_original")
        assert count > 0
        # 验证文件已还原
        restored = target.read_bytes()
        backup = (mock_game_root / BACKUP_DIR_NAME / "EP14_original"
                  / "German" / "2DSymbolsLg.bmp").read_bytes()
        assert restored == backup

    def test_restore_specific_files(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        # 修改两个文件
        (mock_game_root / "German" / "2DSymbolsLg.bmp").write_text("MOD1")
        (mock_game_root / "Info" / "BlankboxH.bmp").write_text("MOD2")
        # 只还原一个
        count = restore_from_backup(
            mock_game_root, "EP14_original",
            files=["German/2DSymbolsLg.bmp"],
        )
        assert count == 1
        # German 已还原
        assert (mock_game_root / "German" / "2DSymbolsLg.bmp").read_text() != "MOD1"
        # Info 未还原
        assert (mock_game_root / "Info" / "BlankboxH.bmp").read_text() == "MOD2"

    def test_restore_nonexistent_backup(self, mock_game_root: Path):
        with pytest.raises(FileNotFoundError):
            restore_from_backup(mock_game_root, "nonexistent_backup")

    def test_restore_creates_parent_dirs(self, mock_game_root: Path):
        """还原时如果游戏目录中缺少父目录，应自动创建"""
        create_original_backup(mock_game_root, "EP14")
        # 删除一个目录
        import shutil
        shutil.rmtree(mock_game_root / "German" / "Units")
        count = restore_from_backup(
            mock_game_root, "EP14_original",
            files=["German/Units/Infantry.bmp"],
        )
        assert count == 1
        assert (mock_game_root / "German" / "Units" / "Infantry.bmp").is_file()

    def test_restore_returns_count(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        count = restore_from_backup(mock_game_root, "EP14_original")
        game_bmps = collect_bmp_files(mock_game_root)
        assert count == len(game_bmps)


# ===========================================================================
# list_backups
# ===========================================================================

class TestListBackups:
    def test_empty(self, mock_game_root: Path):
        result = list_backups(mock_game_root)
        assert result == []

    def test_after_original_backup(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        result = list_backups(mock_game_root)
        assert len(result) == 1
        entry = result[0]
        assert entry["name"] == "EP14_original"
        assert entry["type"] == "original"
        assert entry["file_count"] > 0
        assert entry["size"] > 0

    def test_after_mod_backup(self, mock_game_root: Path):
        files = {"German/2DSymbolsLg.bmp": mock_game_root / "German" / "2DSymbolsLg.bmp"}
        create_mod_backup(mock_game_root, "test_mod", files)
        result = list_backups(mock_game_root)
        assert len(result) == 1
        assert result[0]["type"] == "mod"
        assert result[0]["name"].startswith("test_mod_")

    def test_multiple_backups(self, mock_game_root: Path):
        create_original_backup(mock_game_root, "EP14")
        files = {"German/2DSymbolsLg.bmp": mock_game_root / "German" / "2DSymbolsLg.bmp"}
        create_mod_backup(mock_game_root, "mod_a", files)
        create_mod_backup(mock_game_root, "mod_b", files)
        result = list_backups(mock_game_root)
        assert len(result) == 3

    def test_no_backup_dir(self, mock_game_root: Path):
        """_backup 目录不存在时返回空列表"""
        assert list_backups(mock_game_root) == []
