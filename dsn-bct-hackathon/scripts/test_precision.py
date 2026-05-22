import sys
import os

# Ensure repository root is on sys.path so 'app' package imports work
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.metrics.precision import calculate_precision_at_k

recs = [
    {"primary_category": "Pizza", "similarity_score": 0.9},
    {"primary_category": "Italian", "similarity_score": 0.7},
    {"primary_category": "Burgers", "similarity_score": 0.8},
]

print(calculate_precision_at_k(recs, "pizza", k=2))
