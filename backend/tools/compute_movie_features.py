import csv
import itertools
import sys

from backend.wiring import Wiring
from tools.add_movies import generate_slug

if __name__ == "__main__":
    wiring = Wiring()

    reader = iter(csv.reader(sys.stdin))
    header = next(reader)

    writer = csv.writer(sys.stdout)

    query_index = header.index("query")
    movie_name_index = header.index("movie_name")

    chunks = itertools.groupby(reader, lambda row: row[query_index])
    for query, rows in chunks:
        card_ids = [
            wiring.card_dao.get_by_slug(generate_slug(row[movie_name_index])).id
            for row in rows
        ]
        features = wiring.search_ranking_manager.compute_cards_features(query, card_ids)
        for card_id in card_ids:
            if card_id not in features:
                # Probably we couldn't find card by given query.
                continue
            writer.writerow((query, card_id, *features[card_id]))
