# Composition Layer

This document defines how models and scenario data become one runnable system
and how that system produces a durable `ModelSolution`. The composition layer
owns cross-model resolution, solver boundaries, and run specifications; it does
not rewrite the scientific declarations stored in a `MechanisticModel`.
