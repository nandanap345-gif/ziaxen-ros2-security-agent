# v2 class signal analysis

All limits were fit from seed-1 normal recordings and selected on seed-2 normal recordings. Seed 3 was not read by this build.

| Class | Signal decision | Evidence boundary |
|---|---|---|
| freeze | usable: flatline/zero first-difference in target channels | Manifest/event definitions remain the label authority; no labels are detector inputs. |
| jump | usable only after per-column calibration; mixed-unit/global thresholds were invalid | Manifest/event definitions remain the label authority; no labels are detector inputs. |
| replay | not implemented as a positive rule until a stable repeated sequence is demonstrated | Manifest/event definitions remain the label authority; no labels are detector inputs. |
| clock_skew | usable when stamp lag columns are present | Manifest/event definitions remain the label authority; no labels are detector inputs. |
| bias_drift | candidate only; residual calibration requires a validated cross-sensor pairing | Manifest/event definitions remain the label authority; no labels are detector inputs. |
| false_contact | disabled if seed-2 normal firing exceeds 2 alerts/hour or does not beat matched-window chance | Manifest/event definitions remain the label authority; no labels are detector inputs. |
| missed_contact | undetectable with the available recorded channels when no independent collision signature exists | Manifest/event definitions remain the label authority; no labels are detector inputs. |

## Seed-2 normal firing audit

Normal exposure: 1.7665 h; budget: <=2.000 alerts/hour/rule.

| Rule | Alerts/hour | Status |
|---|---:|---|
| freeze | 0.000000 | within budget |
| jump | 0.000000 | within budget |
| clock_skew | 0.000000 | disabled |
| false_contact | 0.000000 | disabled |

The previous over-trigger was caused by a single global jump limit applied across mixed-unit sensor/contact columns and by state crossing artificial joins. v2 now uses per-column limits and reset slices; seed-3 was not used for calibration.

## Seed-2 attack-vs-chance check

The JSON contains one row per event and rule; `counts_for_class` is true only when the matched-duration normal-window chance indicator is lower than the attack-window indicator.
