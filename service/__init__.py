"""HTTP service that exposes the competency-alignment engine to Moodle.

The service is an adapter. Every alignment decision (normalisation,
fragmentation, BM25 retrieval, constrained model selection, response and
evidence validation, aggregation, hierarchy diagnostics) is made by the research
engine in ``src/moodle_competency``. Nothing in this package reimplements it.
"""
