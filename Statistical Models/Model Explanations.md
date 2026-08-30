# Model Explanations

How to read **Appendix: Full Regression Output** in the New Verticals analytics report.

The appendix is the **receipts**. The findings quote odds ratios and p-values; these five tables are the full models those numbers come from. A DoorDash reader can check that a claim is not a raw cross-tab, and that the other variables were held constant.

## How to read one row

**M1–M4 are logistic.** The coefficient is on the log-odds scale. Convert with \(e^{\beta}\):

- Coefficient **> 0** → higher odds of the outcome (missing item, complaint, late, cancel)
- Coefficient **< 0** → lower odds
- **p < 0.05** → distinguishable from zero after dasher-clustered standard errors
- **Reference category** is the omitted group. Every store effect is *versus DashMart1*. Every category in M1 is *versus Drinks*. Every daypart is *versus midday (11am–2pm)*.

**M5 is OLS.** The coefficient is already in minutes of acceptance wait. No exponentiation.

**Pseudo R² / R²** is “how much of the outcome these variables capture,” not model quality by itself. M3 at 0.31 is strong for ops data. M5 at 0.009 is the finding: CLAT is mostly *not* in this file.

---

## M1 — Will this item be missing?

Grain: **one row per item** on completed deliveries (N = 58,725). Outcome: `WAS_MISSING`. Pseudo R² = 0.213. Standard errors clustered by dasher (2,421 clusters). Reference: Item Category = Drinks, Store = DashMart1.

This is Finding 2 in equation form. Once store is in the model, perishables are **safer** than Drinks, not riskier.

| Term | Coefficient | Odds ratio | p-value |
| --- | ---: | ---: | ---: |
| Intercept | −6.177 | 0.002 | <0.001 |
| Category: Alcohol | 0.014 | 1.01 | 0.935 |
| Category: Baby & Child | 0.459 | 1.58 | 0.006 |
| Category: Bakery | 0.424 | 1.53 | <0.001 |
| Category: Candy | 0.319 | 1.38 | 0.006 |
| Category: Dairy & Eggs | −0.200 | 0.82 | 0.007 |
| Category: Fresh Food | 0.361 | 1.43 | 0.019 |
| Category: Frozen | 0.367 | 1.44 | <0.001 |
| Category: Health | 0.402 | 1.49 | 0.008 |
| Category: Household | 0.548 | 1.73 | <0.001 |
| Category: Ice Cream | −0.737 | 0.48 | 0.204 |
| Category: Meat & Fish | −0.245 | 0.78 | 0.022 |
| Category: Medicine | 0.302 | 1.35 | 0.429 |
| Category: Other/Rare (<150 obs.) | 0.471 | 1.60 | 0.001 |
| Category: Pantry | −0.035 | 0.97 | 0.617 |
| Category: Personal Care | 0.185 | 1.20 | 0.112 |
| Category: Pet Care | −0.210 | 0.81 | 0.211 |
| Category: Produce | −0.476 | 0.62 | <0.001 |
| Category: Snacks | −0.052 | 0.95 | 0.522 |
| Store: Grocery1 | 4.352 | 77.6 | <0.001 |
| Store: Grocery2 | 4.164 | 64.3 | <0.001 |
| Store: Grocery3 | 4.086 | 59.5 | <0.001 |
| Item price ($) | 0.006 | 1.01 | 0.055 |

The intercept (−6.18) is the log-odds of a Drink at DashMart1 being missing — a very small baseline, which matches the 0.2% DashMart miss rate. Store swamps category. That is why a pooled “perishables are the problem” model is wrong, and why Rec 1 specifies a **channel-conditional** confidence score.

Alcohol, Ice Cream, Medicine, Pantry, Snacks, Personal Care, Pet Care are **not** distinguishable from Drinks once store and price are held. Do not build a workstream on those rows.

---

## M2 — Will the customer file a missing/incorrect complaint?

Grain: **one row per completed delivery** (N = 12,313). Outcome: MI report. Pseudo R² = 0.048. Standard errors clustered by dasher. Reference: Store = DashMart1. Grocery2 and Grocery3 are pooled because Grocery3 had **zero** complaints — the model would otherwise blow up (perfect separation).

| Term | Coefficient | Odds ratio | p-value |
| --- | ---: | ---: | ---: |
| Intercept | −4.909 | 0.007 | <0.001 |
| Item unfulfilled rate | 0.741 | 2.10 | 0.063 |
| # items requested | 0.098 | 1.10 | <0.001 |
| Order value ($) | −0.007 | 0.99 | 0.172 |
| Was 20+ min late | 0.881 | 2.41 | <0.001 |
| Store: Grocery1 | 0.759 | 2.14 | <0.001 |
| Store: Grocery2/3 | 0.478 | 1.61 | 0.037 |
| Has perishable item | 0.085 | 1.09 | 0.603 |
| Has alcohol item | 0.179 | 1.20 | 0.670 |

Pseudo R² = 0.048 is low because complaints are rare (1.7%). The model is for **which knobs move odds**, not for predicting a specific order. This is Finding 4: a late delivery more than doubles complaint odds (2.41×); each extra item adds ~10% (1.10×); unfulfilled rate is 2.10× but p = 0.063 because it shares signal with store. Substituting the miss does not appear here because the outcome is the *customer flag*, not the Dasher’s recovery. Order value, perishable, and alcohol are not independent complaint drivers.

---

## M3 — Will this delivery be 20+ minutes late?

Grain: completed deliveries with usable timers (N = 11,922). Pseudo R² = 0.311. Standard errors clustered by dasher. D2R and CLAT winsorized at p99.5 so a 1,313-minute travel time cannot dominate the fit. Reference: Store = DashMart1, Daypart = Midday (11am–2pm).

| Term | Coefficient | Odds ratio | p-value |
| --- | ---: | ---: | ---: |
| Intercept | −4.924 | 0.007 | <0.001 |
| Dasher travel time (D2R, min) | 0.151 | 1.16 | <0.001 |
| Dasher acceptance time (CLAT, min) | 0.140 | 1.15 | <0.001 |
| Store: Grocery1 | −1.460 | 0.23 | <0.001 |
| Store: Grocery2 | −1.694 | 0.18 | <0.001 |
| Store: Grocery3 | −2.986 | 0.05 | 0.004 |
| # items requested | −0.020 | 0.98 | 0.339 |
| Order value ($) | 0.018 | 1.02 | <0.001 |
| Daypart: Overnight (12–5am) | 0.109 | 1.12 | 0.636 |
| Daypart: Morning (6–10am) | −0.302 | 0.74 | 0.151 |
| Daypart: Afternoon (3–5pm) | −0.029 | 0.97 | 0.881 |
| Daypart: Evening (6–9pm) | −0.180 | 0.84 | 0.266 |
| Daypart: Night (10pm–12am) | 0.078 | 1.08 | 0.691 |
| Weekend | −0.185 | 0.83 | 0.122 |

This is the counter-intuitive Finding 3 result. Raw, Grocery2 looks late because Dashers travel 7+ minutes. **Adjusted**, DashMart is the late store — grocery odds of lateness fall to 0.05–0.23× once CLAT and D2R are held. The residual is pick/pack/stage, which this dataset cannot see. Dayparts, item count, and weekend are insignificant *for lateness* after the two clocks are in the model; overnight shows up in M4 and M5 instead.

Pseudo R² = 0.31 is the strongest of the five. The two clocks plus store actually explain lateness.

---

## M4 — Will this order cancel?

Grain: **all 12,506 deliveries**. Outcome is defined for cancels; the other models are not. Pseudo R² = 0.082. Standard errors clustered by dasher. Reference: Store = DashMart1, Daypart = Midday (11am–2pm).

| Term | Coefficient | Odds ratio | p-value |
| --- | ---: | ---: | ---: |
| Intercept | −3.853 | 0.021 | <0.001 |
| Store: Grocery1 | 1.521 | 4.58 | <0.001 |
| Store: Grocery2 | 1.830 | 6.23 | <0.001 |
| Store: Grocery3 | 1.133 | 3.11 | 0.066 |
| Order value ($) | −0.037 | 0.96 | <0.001 |
| # items requested | −0.036 | 0.96 | 0.468 |
| Daypart: Overnight (12–5am) | 1.296 | 3.66 | <0.001 |
| Daypart: Morning (6–10am) | −0.492 | 0.61 | 0.120 |
| Daypart: Afternoon (3–5pm) | −0.248 | 0.78 | 0.335 |
| Daypart: Evening (6–9pm) | −0.255 | 0.77 | 0.264 |
| Daypart: Night (10pm–12am) | 0.077 | 1.08 | 0.781 |
| Weekend | 0.134 | 1.14 | 0.390 |
| Has perishable item | −0.391 | 0.68 | 0.015 |
| Has alcohol item | 0.769 | 2.16 | 0.021 |

The appendix cannot show the channel split inside overnight — that is in Finding 5’s descriptive cut (all 31 overnight cancels are DashMart). M4’s overnight coefficient is real (3.66×); it is **not** “grocery at night.” Alcohol is 2.16× (p = 0.021) but rests on only 11 cancels, so it is hypothesis-generating. Grocery3 is the same direction as the other partners (3.11×) but p = 0.066 on thin n. Item count, other dayparts, and weekend are not the cancel story.

CLAT and D2R are absent on purpose: they are missing for 100% of cancelled deliveries (no Dasher was ever assigned).

---

## M5 — What lengthens acceptance wait?

OLS on completed deliveries (N = 11,971). R² = 0.009 (adj. 0.008). Standard errors clustered by dasher. Reference: Store = DashMart1, Daypart = Midday (11am–2pm). Coefficients are **minutes**, not odds.

| Term | Coefficient (minutes) | p-value |
| --- | ---: | ---: |
| Intercept | 4.930 | <0.001 |
| # items requested | 0.043 | 0.206 |
| Order value ($) | −0.040 | <0.001 |
| Store: Grocery1 | 0.401 | 0.231 |
| Store: Grocery2 | 1.337 | <0.001 |
| Store: Grocery3 | −0.091 | 0.855 |
| Daypart: Overnight (12–5am) | 0.753 | 0.046 |
| Daypart: Morning (6–10am) | 0.081 | 0.784 |
| Daypart: Afternoon (3–5pm) | 0.188 | 0.422 |
| Daypart: Evening (6–9pm) | 0.292 | 0.157 |
| Daypart: Night (10pm–12am) | 0.266 | 0.344 |
| Weekend | 0.069 | 0.641 |

R² = 0.009 is the result. Basket size, store (except Grocery2), and most dayparts do **not** determine how long an order sits. CLAT is dasher supply at the moment of create — mostly off-file. The two things that *do* move it are Grocery2 (+1.34 min) and overnight (+0.75 min). Higher-value orders wait slightly less (−0.04 min per dollar). That is why Rec 3 does not open with “boost pay after 5 minutes of CLAT” as a DashMart pick-time fix, and why Rec 4 treats overnight as a **promise** problem.

---

## Shared design choices (why the tables look the way they do)

- **Clustered by dasher.** The same Dasher appears on many orders (top 10% = 60% of volume). Ignoring that would make p-values look sharper than they are. Clustering barely moved the logistic SEs; it did move M5’s OLS SEs.
- **Completed-only for M1–M3.** A cancelled order cannot be “late” or draw an MI complaint. On cancelled shops, only 40% of items were ever marked found — those rows are an abandoned cart, not a fulfillment outcome.
- **Python and R match to ~0.0000036.** The appendix is one implementation; Cross-Tool Validation is the check that a second solver reached the same coefficients.

---

## Interview one-liner

The appendix is five models that unconfound store, category, clocks, and basket — M1 says grocery shelf truth dominates category, M3 says DashMart’s lateness is not last-mile, M4–M5 say overnight is an assignment/promise problem, and M5’s empty R² says do not treat CLAT as an in-store lever.
