# Bank campaign responses: a time-aware baseline comparison

**Question.** Can information recorded before a call help rank likely term-deposit subscriptions? I used the [UCI Bank Marketing dataset](https://archive.ics.uci.edu/dataset/222/bank+marketing) (CC BY 4.0), specifically its date-ordered 41,188-row `bank-additional-full.csv`. This is a retrospective model evaluation, not a live targeting system.

**Design.** The [reproducible analysis](README.md) checks source fields and labels, holds out the latest 20% of rows, and chooses logistic-regression regularization on an earlier 16% validation segment. It compares the refit model to a constant training-prevalence baseline on the held-out segment. Preprocessing is fitted only on training rows. I excluded call duration, which is unknown before the call; individual dates and customer IDs are unavailable.

![Held-out precision recall curve](outputs/precision_recall.svg)

**Result.** On 8,238 held-out rows, average precision was **0.5383**, compared with **0.3083** for the constant baseline; ROC AUC was **0.7012** versus **0.5000**. The top-scored 10% contained **547 positive outcomes among 824 records** (66.38% precision, 21.54% recall). These are historical outcomes and do not estimate the lift from contacting anyone.

**Tradeoff.** Chronological evaluation makes campaign drift visible: positive rates were **4.79%**, **12.72%**, and **30.83%** in training, validation, and test. The higher held-out prevalence affects average precision. The model's large coefficients involve month and economic indicators, which may proxy period effects and are not causal. Without exact dates, customer IDs, costs, and a prospective comparison, I would use this as an analysis of ranking and drift, not as evidence for deployment. Any operational extension would need feature timing checks, recent customer-disjoint testing, calibration and subgroup review.
