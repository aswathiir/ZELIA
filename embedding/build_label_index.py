from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List

from annoy import AnnoyIndex
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CANONICAL = BASE_DIR / "canonical_labels.json"
DEFAULT_INDEX_PATH = BASE_DIR / "annoy_index.ann"
DEFAULT_LABEL_INDEX_PATH = BASE_DIR / "label_index.json"
DEFAULT_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
DEFAULT_TREES = int(os.getenv("ANNOY_NUM_TREES", 40))


def _flatten_canonical(canonical: Dict[str, Iterable[str]]) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    for field_id, aliases in canonical.items():
        for alias in aliases:
            records.append({"field_id": field_id, "alias": alias})
    return records


def build_index(
    canonical_path: Path = DEFAULT_CANONICAL,
    index_path: Path = DEFAULT_INDEX_PATH,
    label_index_path: Path = DEFAULT_LABEL_INDEX_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    num_trees: int = DEFAULT_TREES,
) -> None:
    """Build the Annoy index and label metadata files."""
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical label file not found: {canonical_path}")

    logging.info("Loading canonical labels from %s", canonical_path)
    with canonical_path.open("r", encoding="utf-8") as f:
        canonical = json.load(f)

    labels = _flatten_canonical(canonical)
    texts = [item["alias"] for item in labels]

    logging.info("Encoding %d labels using %s", len(texts), model_name)
    model = SentenceTransformer(model_name)
    embs = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    emb_dim = embs.shape[1]

    logging.info("Building Annoy index (dim=%d, trees=%d)", emb_dim, num_trees)
    ann = AnnoyIndex(emb_dim, "angular")
    for i, emb in enumerate(embs):
        ann.add_item(i, emb.tolist())
    ann.build(num_trees)
    ann.save(str(index_path))

    logging.info("Writing label metadata to %s", label_index_path)
    with label_index_path.open("w", encoding="utf-8") as f:
        json.dump({str(i): labels[i] for i in range(len(labels))}, f, ensure_ascii=False, indent=2)

    logging.info("Successfully built %s and %s", index_path, label_index_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Annoy index for canonical labels.")
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL, help="Path to canonical_labels.json")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH, help="Output path for annoy_index.ann")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABEL_INDEX_PATH, help="Output path for label_index.json")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_NAME, help="SentenceTransformer model name")
    parser.add_argument("--trees", type=int, default=DEFAULT_TREES, help="Number of trees for Annoy index")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = _parse_args()
    build_index(args.canonical, args.index, args.labels, args.model, args.trees)
