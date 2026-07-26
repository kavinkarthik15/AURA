# Retrieval Benchmark

## Version

- Retrieval Version: `retrieval_v1`
- Similarity Metric: hybrid
- Retrieval Weight: 0.4
- Dataset Version: v1

## Metrics

The retrieval evaluator records:

- Retrieval Precision
- Retrieval Recall
- Average Similarity
- Planning Improvement proxy
- Average Retrieval Time

Results are stored in `backend/ai/retrieval_registry.json` with the metric, weight, dataset version, and timestamp.

## Retrieval Design

The default hybrid score combines:

- cosine state similarity: 60%
- weighted state similarity: 20%
- goal similarity: 10%
- action overlap: 10%

The retriever supports cosine-only and weighted-only modes, a cache for repeated queries, and diversity-aware Top-K selection.
