---
name: scientific-rigor
description: Conditional scientific controls. Load only when a change affects measurements, units, calibration, filtering, normalization, transformations, models, statistical meaning, or engineering conclusions. Routine software work skips this.
---

# Scientific rigor (conditional)

Apply only the items relevant to this change. In the contract, capture them under `scientific: yes` plus the specific acceptance criteria and checks below.

## Capture in the contract
- **Claim:** what scientific or engineering statement does this code support?
- **Quantities:** measured vs derived vs inferred vs assumed, with units and dimensional meaning.
- **Calibration:** source, version, valid range.
- **Transforms:** filtering, normalization, resampling, and unit conversion, in the order they run.
- **Model:** assumptions, valid domain, and competing models. Never silently choose between them; flag it as a decision for the user.
- **Provenance:** raw data source, and which artifacts are derived or cached. Don't substitute weaker evidence (derived for raw, extracted text for an original file) without approval.

## Checks to turn into runnable tests
- Dimensional and unit consistency, including round-trip conversions.
- Known-answer tests against reference values or analytic solutions, with stated tolerances.
- Invariants: conservation, monotonicity, bounds, sign.
- Numerical stability: edge inputs, ill-conditioning, float tolerance, and seeded reproducibility.
- Sensitivity: does a small input perturbation produce a proportionate output change?
- Leakage or confounding, for any fitting or statistics.

## Verification stance
Passing software tests does not establish scientific validity. The verifier separates supported conclusions from conditional, speculative, and unsupported ones, names alternative explanations, and names the smallest experiment or test that would falsify the claim.
