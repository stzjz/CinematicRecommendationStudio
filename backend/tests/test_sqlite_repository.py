import os
import tempfile
import unittest

from app.repositories import load_dataset
from scripts.init_sqlite import initialize_database


class SQLiteRepositoryTest(unittest.TestCase):
    def test_load_dataset_from_sqlite(self):
        handle, db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        try:
            initialize_database(db_path)
            dataset = load_dataset("sqlite", db_path)
            self.assertEqual(dataset["data_source"], "sqlite")
            self.assertTrue(dataset["users"])
            self.assertTrue(dataset["movies"])
            self.assertTrue(dataset["ratings"])
            self.assertIsInstance(dataset["movies"][0]["genres"], list)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
