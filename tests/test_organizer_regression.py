"""既存 organizer.py の仕様を保つための回帰テスト。"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from organizer import create_organization_plan, execute_organization_plan, organize_folder


class OrganizerRegressionTests(unittest.TestCase):
    def test_required_file_types_and_collision_are_organized(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "photo.jpg").write_text("new jpg", encoding="utf-8")
            (root / "cover.JPG").write_text("upper jpg", encoding="utf-8")
            (root / "report.pdf").write_text("pdf", encoding="utf-8")
            (root / "memo.txt").write_text("txt", encoding="utf-8")
            (root / "拡張子なし").write_text("no extension", encoding="utf-8")
            (root / "subfolder").mkdir()
            (root / "subfolder" / "nested.pdf").write_text("nested", encoding="utf-8")

            # 既存の同名ファイルは上書きされないことを確認する。
            (root / "jpg").mkdir()
            (root / "jpg" / "photo.jpg").write_text("keep me", encoding="utf-8")

            plan_result = create_organization_plan(root)

            self.assertEqual(4, len(plan_result.plans))
            self.assertEqual(0, len(plan_result.failures))
            self.assertTrue(all(plan.source.exists() for plan in plan_result.plans))
            self.assertEqual(
                {".jpg", ".pdf", ".txt"},
                {plan.extension for plan in plan_result.plans},
            )
            photo_plan = next(plan for plan in plan_result.plans if plan.source.name == "photo.jpg")
            self.assertEqual(root / "jpg" / "photo_1.jpg", photo_plan.destination)

            result = execute_organization_plan(plan_result)

            self.assertEqual(4, result.success_count)
            self.assertEqual(0, result.failure_count)
            self.assertEqual("keep me", (root / "jpg" / "photo.jpg").read_text(encoding="utf-8"))
            self.assertEqual("new jpg", (root / "jpg" / "photo_1.jpg").read_text(encoding="utf-8"))
            self.assertTrue((root / "jpg" / "cover.JPG").is_file())
            self.assertTrue((root / "pdf" / "report.pdf").is_file())
            self.assertTrue((root / "txt" / "memo.txt").is_file())
            self.assertTrue((root / "拡張子なし").is_file())
            self.assertTrue((root / "subfolder" / "nested.pdf").is_file())

    def test_one_failure_does_not_stop_other_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            missing = root / "missing.txt"
            good = root / "good.pdf"
            missing.write_text("delete after preview", encoding="utf-8")
            good.write_text("move me", encoding="utf-8")

            plan_result = create_organization_plan(root)
            missing.unlink()
            result = execute_organization_plan(plan_result)

            self.assertEqual(1, result.success_count)
            self.assertEqual(1, result.failure_count)
            self.assertTrue((root / "pdf" / "good.pdf").is_file())
            self.assertEqual(missing, result.failed_files[0].source)

    def test_cli_convenience_function_is_still_available(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "from_cli.txt").write_text("cli", encoding="utf-8")

            result = organize_folder(root)

            self.assertEqual(1, result.success_count)
            self.assertEqual(0, result.failure_count)
            self.assertTrue((root / "txt" / "from_cli.txt").is_file())


if __name__ == "__main__":
    unittest.main()
