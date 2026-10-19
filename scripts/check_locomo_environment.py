"""Check the frozen data and a real local embedding load (no answering API)."""

import argparse
from importlib.metadata import version
import json
import platform
from pathlib import Path
import time

from prepare_locomo import ROOT, materialize, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/locomo-smoke.json")
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw/locomo10.json")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/locomo")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data/model-cache")
    parser.add_argument("--report", type=Path, default=ROOT / "output/locomo/environment.json")
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    result = {"python": platform.python_version(), "platform": platform.system(),
              "status": "failed", "local_files_only": args.local_files_only,
              "data": {}, "embedding": config["embedding"]}
    started = time.perf_counter()
    try:
        result["data"] = materialize(args.source, config, args.data_dir)
        import numpy as np
        import torch
        from sentence_transformers import SentenceTransformer

        result["packages"] = {n: version(n) for n in
                              ("torch", "sentence-transformers", "transformers", "huggingface-hub", "numpy")}
        result["cuda_available"] = torch.cuda.is_available()
        embedding = config["embedding"]
        model = SentenceTransformer(embedding["model_id"], revision=embedding["revision"],
                                    device=embedding["device_for_check"], cache_folder=str(args.cache_dir),
                                    local_files_only=args.local_files_only, trust_remote_code=False)
        if (model.get_sentence_embedding_dimension() != embedding["dimensions"]
                or model.max_seq_length != embedding["max_seq_length"]):
            raise ValueError("Embedding dimensions or sequence limit differs from config")
        rows = json.loads((args.data_dir / "development.conversations.json").read_text(encoding="utf-8"))
        conv = rows[0]["conversation"]
        turn = conv["session_1"][0]
        text = f"{conv['session_1_date_time']} {turn['speaker']}: {turn['text']}"
        vectors = model.encode([text, text], normalize_embeddings=embedding["normalize_embeddings"],
                               convert_to_numpy=True, show_progress_bar=False)
        if (vectors.shape != (2, embedding["dimensions"]) or not np.isfinite(vectors).all()
                or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
                or not np.allclose(vectors[0], vectors[1], atol=1e-6)):
            raise ValueError("Embedding shape/finiteness/normalization/repeatability check failed")
        result.update(status="passed", shape=list(vectors.shape),
                      vector_norms=[float(v) for v in np.linalg.norm(vectors, axis=1)],
                      actual_device=str(model.device), checked_message_id=turn["dia_id"],
                      independent_member_verification="pending")
    except Exception as exc:
        # Save the failure while retaining a failing exit status and the traceback.
        result["error_type"] = type(exc).__name__
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        save(args.report, result)
        raise
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    save(args.report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
