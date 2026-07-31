# Runtime Layer

This document defines deterministic evaluation of a `MechanisticModel` at one
point in time. The runtime layer owns transient rates and evaluation
diagnostics; it does not choose scenario inputs, construct solver state,
advance time, or redefine persistent model identity.
