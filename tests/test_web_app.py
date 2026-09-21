"""Web API、プレビュー、進捗結果のテスト。"""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from organizer_service import select_folder_native
from web_app import create_app


class WebAppTests(unittest.TestCase):
    @patch("organizer_service.subprocess.run")
    def test_native_picker_uses_helper_process(self, run_mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"folder": "C:\\\\Users\\\\test"}\n', stderr=""
        )

        selected = select_folder_native()

        self.assertEqual("C:\\Users\\test", selected)
        command = run_mock.call_args.args[0]
        self.assertTrue(command[1].endswith("folder_picker.py"))
        self.assertEqual("utf-8", run_mock.call_args.kwargs["encoding"])

    def test_health_and_home_page(self) -> None:
        app = create_app(folder_picker=lambda: None)
        app.testing = True

        with app.test_client() as client:
            health = client.get("/api/health")
            home = client.get("/")

        self.assertEqual(200, health.status_code)
        self.assertEqual({"status": "ok"}, health.get_json())
        self.assertEqual(200, home.status_code)
        self.assertIn("整理予定プレビュー", home.get_data(as_text=True))

    def test_folder_picker_can_be_cancelled(self) -> None:
        app = create_app(folder_picker=lambda: None)
        app.testing = True

        with app.test_client() as client:
            response = client.post("/api/select-folder", json={})

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["cancelled"])

    def test_preview_and_background_execution(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sample.JPG").write_text("image", encoding="utf-8")
            (root / "document.pdf").write_text("document", encoding="utf-8")
            (root / "no_extension").write_text("skip", encoding="utf-8")

            app = create_app(folder_picker=lambda: str(root))
            app.testing = True

            with app.test_client() as client:
                selected = client.post("/api/select-folder", json={})
                self.assertEqual(str(root), selected.get_json()["folder"])

                preview_response = client.post("/api/preview", json={"folder": str(root)})
                self.assertEqual(200, preview_response.status_code)
                preview = preview_response.get_json()
                self.assertEqual(2, preview["plan_count"])
                self.assertEqual(0, preview["failure_count"])
                self.assertEqual({"jpg", "pdf"}, {item["destination_folder"] for item in preview["plans"]})

                start_response = client.post(
                    "/api/jobs", json={"preview_id": preview["preview_id"]}
                )
                self.assertEqual(202, start_response.status_code)
                job = start_response.get_json()

                deadline = time.monotonic() + 5
                while job["status"] not in {"completed", "failed"}:
                    self.assertLess(time.monotonic(), deadline, "整理処理がタイムアウトしました")
                    time.sleep(0.02)
                    job = client.get(f"/api/jobs/{job['job_id']}").get_json()

                self.assertEqual("completed", job["status"])
                self.assertEqual(2, job["success_count"])
                self.assertEqual(0, job["failure_count"])
                self.assertEqual(100, job["progress"])
                self.assertTrue((root / "jpg" / "sample.JPG").is_file())
                self.assertTrue((root / "pdf" / "document.pdf").is_file())
                self.assertTrue((root / "no_extension").is_file())

                duplicate_start = client.post(
                    "/api/jobs", json={"preview_id": preview["preview_id"]}
                )
                self.assertEqual(409, duplicate_start.status_code)

    def test_invalid_folder_is_reported_in_preview(self) -> None:
        app = create_app(folder_picker=lambda: None)
        app.testing = True
        missing = str(Path("this-folder-does-not-exist-987654321").resolve())

        with app.test_client() as client:
            response = client.post("/api/preview", json={"folder": missing})

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(0, payload["plan_count"])
        self.assertEqual(1, payload["failure_count"])
        self.assertIn("存在しません", payload["failures"][0]["message"])


if __name__ == "__main__":
    unittest.main()
