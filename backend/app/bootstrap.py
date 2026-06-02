from app.config import get_runtime_settings
from app.repositories import load_dataset
from app.services.catalog_service import CatalogService
from app.services.recommendation_service import RecommendationService


def build_services():
    settings = get_runtime_settings()
    dataset = load_dataset(settings["data_source"], settings["db_path"])

    catalog_service = CatalogService(
        dataset["users"],
        dataset["movies"],
        dataset["ratings"],
        dataset.get("movie_tags", []),
        dataset["model_metrics"],
        dataset["ablation_results"],
        data_source=dataset["data_source"],
        db_path=dataset.get("db_path"),
    )
    recommendation_service = RecommendationService(
        dataset["movies"],
        dataset["ratings"],
        data_source=dataset["data_source"],
    )

    return {
        "settings": settings,
        "dataset": dataset,
        "catalog_service": catalog_service,
        "recommendation_service": recommendation_service,
    }
