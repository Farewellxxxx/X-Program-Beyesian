from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from openpyxl import Workbook


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audit_ieee_thms_dataset.py"
)


def load_module():
    if not MODULE_PATH.exists():
        raise AssertionError("dataset audit module has not been implemented")
    spec = importlib.util.spec_from_file_location("audit_ieee_thms_dataset", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("dataset audit module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DatasetAuditTests(unittest.TestCase):
    def test_normalize_group_label_handles_observed_numeric_and_chinese_forms(self):
        module = load_module()
        cases = {
            "3": 3,
            "第三组": 3,
            "7": 7,
            "七": 7,
            "21": 21,
            "21组": 21,
            "二十一组": 21,
            "29": 29,
            "第29组": 29,
            "  第 29 组 ": 29,
            "": None,
            None: None,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(module.normalize_group_label(raw), expected)

    def test_safe_public_record_never_emits_direct_identifier_values(self):
        module = load_module()
        raw = {
            "姓名": "Direct Name",
            "IP地址": "192.0.2.24",
            "device_id": "device-secret-123",
            "组别": "第三组",
            "评分": 6,
        }
        public = module.safe_public_record(raw, salt=b"audit-test-salt")
        serialized = repr(public)

        self.assertNotIn("Direct Name", serialized)
        self.assertNotIn("192.0.2.24", serialized)
        self.assertNotIn("device-secret-123", serialized)
        self.assertEqual(public["group_id"], 3)
        self.assertEqual(public["评分"], 6)
        self.assertEqual(set(public), {"participant_key", "group_id", "评分"})

    def test_repair_zip_name_recovers_utf8_names_decoded_as_cp437(self):
        module = load_module()
        self.assertTrue(
            hasattr(module, "repair_zip_name"),
            "repair_zip_name has not been implemented",
        )
        self.assertEqual(module.repair_zip_name("mpcµû░µò░µì«"), "mpc新数据")
        self.assertEqual(
            module.repair_zip_name("µëôσêåµò░µì« 1.xlsx"),
            "打分数据 1.xlsx",
        )
        self.assertEqual(module.repair_zip_name("MSSQ.xlsx"), "MSSQ.xlsx")

    def test_profile_csv_bytes_reports_rows_schema_missingness_and_sampling(self):
        module = load_module()
        self.assertTrue(
            hasattr(module, "profile_csv_bytes"),
            "profile_csv_bytes has not been implemented",
        )
        raw = (
            b"time,seconds_elapsed,x,y,z\n"
            b"1000,0.00,1,2,3\n"
            b"1010,0.01,1,,3\n"
            b"1020,0.02,1,2,3\n"
        )
        profile = module.profile_csv_bytes(raw)
        self.assertEqual(profile["row_count"], 3)
        self.assertEqual(
            profile["columns"],
            ["time", "seconds_elapsed", "x", "y", "z"],
        )
        self.assertEqual(profile["missing_cells"], 1)
        self.assertAlmostEqual(profile["median_dt_s"], 0.01)
        self.assertAlmostEqual(profile["sampling_hz"], 100.0)

    def test_archive_inventory_excludes_macos_artifacts_and_counts_nested_zip(self):
        module = load_module()
        self.assertTrue(
            hasattr(module, "archive_inventory"),
            "archive_inventory has not been implemented",
        )
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w") as inner:
            inner.writestr("extra.csv", "a,b\n1,2\n")

        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "fixture.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("dataset/3/Annotation.csv", b"")
                archive.writestr(
                    "dataset/3/Accelerometer.csv",
                    "time,seconds_elapsed,x\n1000,0.0,1\n1010,0.01,2\n",
                )
                archive.writestr("dataset/3/extra.zip", nested.getvalue())
                archive.writestr("__MACOSX/dataset/3/._Accelerometer.csv", b"x")

            inventory = module.archive_inventory(archive_path)

        self.assertEqual(inventory["real_file_count"], 3)
        self.assertEqual(inventory["macos_artifact_count"], 1)
        self.assertEqual(inventory["empty_annotation_count"], 1)
        self.assertEqual(inventory["nested_zip_count"], 1)
        self.assertEqual(inventory["extensions"], {".csv": 2, ".zip": 1})

    def test_audit_dataset_writes_aggregate_outputs_without_identifier_values(self):
        module = load_module()
        self.assertTrue(
            hasattr(module, "audit_dataset"),
            "audit_dataset has not been implemented",
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["姓名", "来自IP", "17、组别", "评分"])
        sheet.append(["Person One", "192.0.2.1", "第三组", 6])
        sheet.append(["Person Two", "192.0.2.2", "3", 5])
        workbook_bytes = io.BytesIO()
        workbook.save(workbook_bytes)

        mssq = Workbook()
        mssq_sheet = mssq.active
        mssq_sheet.append(["name", "MSSQ_score"])
        mssq_sheet.append(["Person One", 4])
        mssq_sheet.append(["Person Three", 7])
        mssq_bytes = io.BytesIO()
        mssq.save(mssq_bytes)

        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "fixture.zip"
            output_dir = Path(tmp) / "outputs"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("dataset/questionnaire.xlsx", workbook_bytes.getvalue())
                archive.writestr("dataset/MSSQ.xlsx", mssq_bytes.getvalue())
                accelerometer = (
                    "time,seconds_elapsed,x\n1000,0.0,1\n1010,0.01,2\n"
                )
                archive.writestr(
                    "dataset/3/Accelerometer.csv",
                    accelerometer,
                )
                archive.writestr("dataset/3/Annotation.csv", b"")
                archive.writestr("dataset/4/Accelerometer.csv", accelerometer)
                archive.writestr("dataset/4/Annotation.csv", b"")

            summary = module.audit_dataset(
                archive_path,
                output_dir,
                salt=b"audit-test-salt",
            )
            combined_output = "\n".join(
                path.read_text(encoding="utf-8-sig")
                for path in output_dir.iterdir()
                if path.is_file()
            )

        self.assertEqual(summary["questionnaires"][0]["row_count"], 2)
        self.assertEqual(summary["questionnaires"][0]["unique_participant_keys"], 2)
        self.assertEqual(summary["normalized_group_counts"], {"3": 2})
        self.assertIn(
            "questionnaire_name_linkage",
            summary,
            "cross-questionnaire name linkage has not been implemented",
        )
        self.assertEqual(
            summary["questionnaire_name_linkage"]["pairwise"][0]["exact_overlap"],
            1,
        )
        self.assertNotIn("Person One", combined_output)
        self.assertNotIn("Person Two", combined_output)
        self.assertNotIn("192.0.2.1", combined_output)
        self.assertNotIn("192.0.2.2", combined_output)
        self.assertIn("dataset_dictionary.csv", summary["output_files"])
        self.assertIn("sensor_file_profiles.csv", summary["output_files"])
        self.assertIn("group_normalization.csv", summary["output_files"])
        self.assertEqual(summary["duplicate_sensor_session_groups"], [[3, 4]])


if __name__ == "__main__":
    unittest.main()
