import tkintermapview as tmv
from pathlib import Path

MAP_DB_PATH = Path(__file__).parent / "database" / "map.db"

class MapDownloader(tmv.OfflineLoader):

    def __init__(self) -> None:
        if not MAP_DB_PATH.parent.is_dir():
            MAP_DB_PATH.parent.mkdir(parents=True)
        super().__init__(
            path=MAP_DB_PATH,
            tile_server="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"  # OpenStreetMap tiles
        )

    def download_world(self):
        self.save_offline_tiles((85.05112878, -180.0), (-85.05112878, 180.0), 3, 6)
