from typing import Iterable, List, Mapping

from elasticsearch import Elasticsearch
from elasticsearch_ltr import LTRClient

from backend.search.features import CardFeaturesManager


class SearchRankingManager:

    DEFAULT_FEATURE_SET_NAME = "card_features"

    def __init__(self, elasticsearch_client: Elasticsearch, card_features_manager: CardFeaturesManager,
                 cards_index_name: str):
        self.elasticsearch_client = elasticsearch_client
        self.card_features_manager = card_features_manager
        self.cards_index_name = cards_index_name

    def initialize_ranking(self, feature_set_name=DEFAULT_FEATURE_SET_NAME):
        ltr: LTRClient = self.elasticsearch_client.ltr
        try:
            ltr.create_feature_store()
        except Exception as exc:
            if "resource_already_exists_exception" not in str(exc):
                raise
        ltr.create_feature_set(feature_set_name, {
            "featureset": {
                "features": [
                    self._make_feature("name_tf_idf", ["query"], {
                        "match": {
                            "name": "{{query}}"
                        }
                    }),
                    self._make_feature("combined_tf_idf", ["query"], {
                        "multi_match": {
                            "query": "{{query}}",
                            "fields": ["name^3", "tags.text", "text"]
                        }
                    }),
                    *(
                        self._make_feature(feature_name, [], {
                            "function_score": {
                                "field_value_factor": {
                                    "field": feature_name
                                }
                            }
                        })
                        for feature_name in sorted(self.card_features_manager.get_all_feature_names_set())
                    )
                ]
            }
        })

    def compute_cards_features(self, query: str, card_ids: Iterable[str],
                               feature_set_name=DEFAULT_FEATURE_SET_NAME) -> Mapping[str, List[float]]:
        card_ids = list(card_ids)
        result = self.elasticsearch_client.search({
            "query": {
                "bool": {
                    "filter": [
                        {
                            "terms": {
                                "_id": card_ids
                            }
                        },
                        {
                            "sltr": {
                                "_name": "logged_featureset",
                                "featureset": feature_set_name,
                                "params": {
                                    "query": query
                                }
                        }}
                    ]
                }
            },
            "ext": {
                "ltr_log": {
                    "log_specs": {
                        "name": "log_entry1",
                        "named_query": "logged_featureset"
                    }
                }
            },
            "size": len(card_ids),
        })
        return {
            hit["_id"]: [feature.get("value", float("nan")) for feature in hit["fields"]["_ltrlog"][0]["log_entry1"]]
            for hit in result["hits"]["hits"]
        }

    @staticmethod
    def _make_feature(name, params, query):
        return {
            "name": name,
            "params": params,
            "template_language": "mustache",
            "template": query,
        }
