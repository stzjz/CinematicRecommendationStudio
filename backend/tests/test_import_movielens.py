import os
import sqlite3
import tempfile
import unittest
import zipfile

from scripts.import_movielens import import_movielens


class MovieLensImportTest(unittest.TestCase):
    def test_import_movielens_archive(self):
        handle, archive_path = tempfile.mkstemp(suffix=".zip")
        os.close(handle)
        db_handle, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_handle)
        try:
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("ml-1m/users.dat", "1::F::25::4::00000\n")
                archive.writestr("ml-1m/movies.dat", "10::Example Movie (2001)::Drama|Comedy\n")
                archive.writestr("ml-1m/ratings.dat", "1::10::4::978300760\n")

            result = import_movielens(archive_path, db_path)
            self.assertEqual(result["users"], 1)
            self.assertEqual(result["movies"], 1)
            self.assertEqual(result["ratings"], 1)

            connection = sqlite3.connect(db_path)
            try:
                movie = connection.execute(
                    "SELECT title, year, genres FROM movies WHERE movie_id = 10"
                ).fetchone()
                self.assertEqual(movie, ("Example Movie", 2001, "Drama|Comedy"))
            finally:
                connection.close()
        finally:
            if os.path.exists(archive_path):
                os.remove(archive_path)
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
