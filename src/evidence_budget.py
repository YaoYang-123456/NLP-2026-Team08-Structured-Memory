"""Shared rendering and offline proxy-token budget for phase-two evidence."""
import hashlib
import os
from pathlib import Path

from metamem_pilot.data import digest

RENDER_VERSION = "evidence-v1"
COUNTER = "cl100k_base"
ASSET_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
ASSET_SHA256 = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"


def render_evidence(contexts):
    """Render validated contexts in order; keep full source identifiers out of the prompt."""
    return "\n\n".join(f"[E{i}] {context['kind']}\n{context['text']}"
                       for i, context in enumerate(contexts, 1))


class EvidenceBudget:
    def __init__(self, max_tokens, tokenizer_cache):
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("Evidence max_tokens must be a positive integer")
        if tokenizer_cache is None:
            raise ValueError("Phase-two evidence requires an explicit --tokenizer-cache")
        cache = Path(tokenizer_cache).resolve()
        asset = cache / hashlib.sha1(ASSET_URL.encode()).hexdigest()
        if not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest() != ASSET_SHA256:
            raise ValueError("Prepare the pinned cl100k_base asset in --tokenizer-cache before running offline")
        os.environ["TIKTOKEN_CACHE_DIR"] = str(cache)
        import tiktoken
        self.encoding = tiktoken.get_encoding(COUNTER)
        self.max_tokens = max_tokens

    def count(self, contexts):
        """B/D use this on the entire proposed selection, including headers and separators."""
        return len(self.encoding.encode_ordinary(render_evidence(contexts)))

    def prepare(self, contexts):
        text = render_evidence(contexts)
        tokens = len(self.encoding.encode_ordinary(text))
        if tokens > self.max_tokens:
            raise ValueError(f"Evidence budget exceeded: {tokens} > {self.max_tokens}; repack upstream")
        return {"renderer": RENDER_VERSION, "counter": COUNTER, "max_tokens": self.max_tokens,
                "proxy_tokens": tokens, "text": text,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "contexts_sha256": digest(contexts),
                "source_map": [{"evidence_id": f"E{i}", "kind": context["kind"],
                                "source_ids": context["source_ids"]}
                               for i, context in enumerate(contexts, 1)]}
