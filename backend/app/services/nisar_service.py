from app.core.exceptions import NotFoundError
from app.integrations.nisar.asf_client import AsfClient
from app.integrations.nisar.catalog_mapper import map_asf_product
from app.repositories.nisar_repository import NisarRepository
from app.schemas.nisar import NisarSceneOut
from app.utils.geometry import as_geojson


class NisarService:
    def __init__(self, repo: NisarRepository | None = None, client: AsfClient | None = None) -> None:
        self.repo = repo or NisarRepository()
        self.client = client or AsfClient()

    @staticmethod
    def _to_out(row) -> NisarSceneOut:
        scene, geojson = row
        return NisarSceneOut(
            id=scene.id,
            product_id=scene.product_id,
            product_type=scene.product_type,
            maturity=scene.maturity,
            acquisition_start=scene.acquisition_start,
            acquisition_end=scene.acquisition_end,
            orbit_direction=scene.orbit_direction,
            polarization=scene.polarization,
            footprint=as_geojson(geojson),
            source_url=scene.source_url,
            metadata=scene.extra_metadata,
            discovered_at=scene.discovered_at,
        )

    def list(self, db, **filters) -> list[NisarSceneOut]:
        return [self._to_out(row) for row in self.repo.list(db, **filters)]

    def get(self, db, scene_id) -> NisarSceneOut:
        row = self.repo.get(db, scene_id)
        if row is None:
            raise NotFoundError(f"scene {scene_id} not found")
        return self._to_out(row)

    def sync_from_catalogue(self, db, *, bbox, start, end, max_results: int = 250) -> int:
        """Pull products from ASF DAAC into `catalog.nisar_scenes`. Returns rows touched."""
        products = self.client.search(bbox=bbox, start=start, end=end, max_results=max_results)
        count = 0
        for product in products:
            payload = map_asf_product(product)
            if payload is None:
                continue
            self.repo.upsert(db, **payload)
            count += 1
        return count
