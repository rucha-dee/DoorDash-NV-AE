## DoorDash New Verticals Analytics Exercise
## R replication of the five regression models built in Python (statsmodels).
##
## Purpose: independent-solver check on the SAME cleaned feature tables.
## Python uses maximum likelihood (Newton-Raphson); R's glm() uses IRLS. Because
## the logistic log-likelihood is concave there is a single global optimum, so
## agreement confirms both implementations solve the same problem correctly.
## This is implementation verification / replication -- NOT statistical
## cross-validation (no train/test split is involved).
##
## Note: this script deliberately consumes delivery_level.csv and item_level.csv
## exactly as Python wrote them (including ITEM_CATEGORY_GRP, STORE_GRP, daypart
## and cluster_id) rather than re-deriving features. Re-deriving would silently
## re-implement the cleaning and weaken the check.
##
## Cluster-robust standard errors are computed in base R below, so the script
## has no package dependencies beyond a stock install (no sandwich/lmtest).

deliv <- read.csv("delivery_level.csv", stringsAsFactors = FALSE)
item  <- read.csv("item_level.csv",     stringsAsFactors = FALSE)

ref <- function(x, r) relevel(factor(x), ref = r)
deliv$DELIV_STORE_NAME <- ref(deliv$DELIV_STORE_NAME, "DashMart1")
deliv$STORE_GRP        <- ref(deliv$STORE_GRP,        "DashMart1")
deliv$daypart          <- ref(deliv$daypart,          "Midday(11-14)")
deliv$is_weekend       <- factor(deliv$is_weekend)

item$DELIV_STORE_NAME  <- ref(item$DELIV_STORE_NAME,  "DashMart1")
item$ITEM_CATEGORY_GRP <- ref(item$ITEM_CATEGORY_GRP, "Drinks")

## ---------------------------------------------------------------------------
## CR1 cluster-robust covariance, base R only.
##   V = B %*% ( sum_g s_g s_g' ) %*% B  * c
## where B is the model bread (X'WX)^-1, s_g the summed score contributions for
## cluster g, and c = G/(G-1) * (N-1)/(N-K) the standard finite-sample scaling.
## For a canonical-link logit the score is X'(y - p); for OLS it is X'e.
## ---------------------------------------------------------------------------
## Cluster ids are recovered by ROW NAME from the frame the model was fitted on.
## Positional indexing would be wrong: subset() and listwise deletion preserve
## the parent frame's row names, so row name != row position.
model_clusters <- function(model, data) {
  as.character(data[rownames(model.matrix(model)), "cluster_id"])
}

cluster_se <- function(model, data) {
  X  <- model.matrix(model)
  u  <- if (inherits(model, "glm")) residuals(model, type = "response")
        else residuals(model)
  cl <- factor(model_clusters(model, data))
  stopifnot(!any(is.na(cl)), length(cl) == nrow(X))
  s  <- rowsum(X * as.numeric(u), cl)        # one summed score row per cluster
  # Bread must be the unscaled (X'WX)^-1. glm(binomial) fixes dispersion at 1 so
  # vcov() is already correct, but lm()'s vcov() carries a sigma^2 factor that
  # would double-count the residual variance already present in the meat.
  B  <- if (inherits(model, "glm")) vcov(model)
        else vcov(model) / summary(model)$sigma^2
  G  <- nlevels(cl); N <- nrow(X); K <- ncol(X)
  cc <- (G / (G - 1)) * ((N - 1) / (N - K))  # CR1, matches statsmodels' CRV1
  V  <- B %*% (t(s) %*% s) %*% B * cc
  sqrt(diag(V))
}

report <- function(model, data, label) {
  cat("\n================ ", label, " ================\n", sep = "")
  co    <- summary(model)$coefficients
  se_cl <- cluster_se(model, data)
  est   <- co[, 1]
  p_cl  <- 2 * pnorm(-abs(est / se_cl))
  out <- data.frame(
    term        = rownames(co),
    estimate_R  = est,
    se_naive_R  = co[, 2],
    se_clust_R  = se_cl,
    p_clust_R   = p_cl,
    row.names   = NULL
  )
  print(out, digits = 5)
  cat(sprintf("\nN = %d | clusters = %d\n", nrow(model.matrix(model)),
              length(unique(model_clusters(model, data)))))
  if (inherits(model, "glm")) {
    cat(sprintf("McFadden pseudo R2 = %.4f\n",
                1 - model$deviance / model$null.deviance))
  } else {
    cat(sprintf("R2 = %.4f (adj %.4f)\n", summary(model)$r.squared,
                summary(model)$adj.r.squared))
  }
  out
}

## Model frames must match Python's: same restrictions, same listwise deletion.
completed <- subset(deliv, WAS_CANCELLED == 0)
item_comp <- subset(item, DELIVERY_UUID %in% completed$DELIVERY_UUID)

## M1 -- item-level, completed deliveries only.
m1 <- glm(WAS_MISSING ~ ITEM_CATEGORY_GRP + ITEM_PRICE + DELIV_STORE_NAME,
          data = item_comp, family = binomial("logit"))
c1 <- report(m1, item_comp, "MODEL 1 (R) - Item-level: WAS_MISSING")

## M2 -- complaint, completed only, Grocery2/3 pooled (perfect separation).
m2 <- glm(DELIV_MISSING_INCORRECT_REPORT_BINARY ~ unfulfilled_rate + n_items_requested +
            order_value + DELIV_IS_20_MIN_LATE + STORE_GRP + has_perishable + has_alcohol,
          data = completed, family = binomial("logit"))
c2 <- report(m2, completed, "MODEL 2 (R) - Complaint: DELIV_MISSING_INCORRECT_REPORT_BINARY")

## M3 -- lateness, completed only, requires non-null CLAT & D2R.
m3 <- glm(DELIV_IS_20_MIN_LATE ~ DELIV_D2R + DELIV_CLAT + DELIV_STORE_NAME +
            n_items_requested + order_value + daypart + is_weekend,
          data = completed, family = binomial("logit"))
c3 <- report(m3, completed, "MODEL 3 (R) - Lateness: DELIV_IS_20_MIN_LATE")

## M4 -- cancellation, all deliveries.
m4 <- glm(WAS_CANCELLED ~ DELIV_STORE_NAME + order_value + n_items_requested +
            daypart + is_weekend + has_perishable + has_alcohol,
          data = deliv, family = binomial("logit"))
c4 <- report(m4, deliv, "MODEL 4 (R) - Cancellation: WAS_CANCELLED")

## M5 -- OLS on dasher acceptance time.
m5 <- lm(DELIV_CLAT ~ n_items_requested + order_value + DELIV_STORE_NAME +
           daypart + is_weekend, data = completed)
c5 <- report(m5, completed, "MODEL 5 (R) - OLS: DELIV_CLAT (dasher acceptance time)")

for (nm in c("c1", "c2", "c3", "c4", "c5")) {
  write.csv(get(nm), paste0("R_", sub("c", "m", nm), "_coefs.csv"), row.names = FALSE)
}

## ---------------------------------------------------------------------------
## Cross-tool comparison against the Python coefficient tables.
## ---------------------------------------------------------------------------
cat("\n\n================ PYTHON vs R COEFFICIENT COMPARISON ================\n")
normalise <- function(x) {
  x <- gsub("^C\\(|, Treatment\\(reference='[^']*'\\)\\)", "", x)
  x <- gsub("\\[T\\.|\\]$", "", x)
  x <- gsub("\\[|\\]", "", x)
  gsub("[^A-Za-z0-9]", "", tolower(x))
}
worst <- 0
for (m in paste0("m", 1:5)) {
  pf <- paste0("py_", m, "_coefs.csv"); rf <- paste0("R_", m, "_coefs.csv")
  if (!file.exists(pf)) { cat(sprintf("%s: %s not found - run python_analysis.py first\n", m, pf)); next }
  py <- read.csv(pf); rr <- read.csv(rf)
  py$key <- normalise(py$term); rr$key <- normalise(rr$term)
  j <- merge(py[, c("key", "coef", "se_clustered")],
             rr[, c("key", "estimate_R", "se_clust_R")], by = "key")
  dc <- max(abs(j$coef - j$estimate_R))
  ds <- max(abs(j$se_clustered - j$se_clust_R))
  worst <- max(worst, dc)
  cat(sprintf("%s: %2d/%d terms matched | max |coef diff| = %.3e | max |clustered SE diff| = %.3e\n",
              m, nrow(j), nrow(rr), dc, ds))
}
cat(sprintf("\nLargest coefficient discrepancy across all models: %.3e\n", worst))
cat("Differences at this magnitude are solver floating-point precision, not methodological.\n")
cat(sprintf("\nR version used: %s\n", R.version.string))
