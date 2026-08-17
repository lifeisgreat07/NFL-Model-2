"""
Stage 4: Chronological backtest.

For each test season in [2022, 2023, 2024, 2025]:
  - Train only on games from EARLIER seasons (strictly before the test season)
  - Evaluate on that season's games
  - Pool all out-of-sample predictions across test seasons for final metrics

This is an expanding-window, season-level holdout -- never trains on a
season it's then evaluated on. Reported numbers come only from this
actual backtest; nothing here is estimated or asserted without being run.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, roc_auc_score

feat = pd.read_pickle('/home/claude/nfl_real_model/game_features.pkl')

FEATURES = ['off_matchup', 'def_matchup', 'sr_off_matchup', 'sr_def_matchup']
TEST_SEASONS = [2022, 2023, 2024, 2025]

def run_backtest(model_builder, name):
    all_true, all_pred_prob, all_season = [], [], []
    for test_season in TEST_SEASONS:
        train = feat[feat['season'] < test_season]
        test = feat[feat['season'] == test_season]
        if len(train) < 50 or len(test) == 0:
            continue
        X_train, y_train = train[FEATURES].values, train['home_win'].values
        X_test, y_test = test[FEATURES].values, test['home_win'].values

        model = model_builder()
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_test)[:, 1]

        all_true.extend(y_test)
        all_pred_prob.extend(probs)
        all_season.extend([test_season] * len(y_test))

    all_true = np.array(all_true)
    all_pred_prob = np.array(all_pred_prob)
    all_pred = (all_pred_prob >= 0.5).astype(int)

    acc = accuracy_score(all_true, all_pred)
    ll = log_loss(all_true, all_pred_prob)
    brier = brier_score_loss(all_true, all_pred_prob)
    auc = roc_auc_score(all_true, all_pred_prob)

    print(f"\n=== {name} ===")
    print(f"Games evaluated (pooled, {TEST_SEASONS[0]}-{TEST_SEASONS[-1]}): {len(all_true)}")
    print(f"Accuracy:    {acc:.4f}")
    print(f"Log loss:    {ll:.4f}")
    print(f"Brier score: {brier:.4f}")
    print(f"ROC-AUC:     {auc:.4f}")
    return all_true, all_pred_prob, {'name': name, 'accuracy': acc, 'log_loss': ll,
                                       'brier': brier, 'auc': auc, 'n': len(all_true)}

results_summary = []

# ---------- Baseline 1: Home team always wins ----------
home_true, home_prob = [], []
for test_season in TEST_SEASONS:
    test = feat[feat['season'] == test_season]
    home_true.extend(test['home_win'].values)
    home_prob.extend([0.5773] * len(test))  # historical league-wide home win rate as constant "probability"
home_true = np.array(home_true)
home_pred = np.ones(len(home_true))  # always predict home wins
acc = accuracy_score(home_true, home_pred)
print(f"\n=== Baseline: Home team always wins ===")
print(f"Games evaluated: {len(home_true)}")
print(f"Accuracy: {acc:.4f}")
results_summary.append({'name': 'Baseline: Home always wins', 'accuracy': acc, 'log_loss': None,
                          'brier': None, 'auc': None, 'n': len(home_true)})

# ---------- Baseline 2: Coin flip ----------
results_summary.append({'name': 'Baseline: Coin flip (50%)', 'accuracy': 0.5, 'log_loss': log_loss([0,1],[0.5,0.5]),
                          'brier': 0.25, 'auc': 0.5, 'n': len(home_true)})

# ---------- Model A1: Logistic Regression ----------
_, _, s = run_backtest(lambda: LogisticRegression(max_iter=1000), "Logistic Regression (football-only)")
results_summary.append(s)

# ---------- Model A2: Gradient Boosting ----------
_, _, s = run_backtest(lambda: GradientBoostingClassifier(n_estimators=100, max_depth=2, learning_rate=0.05, random_state=42), "Gradient Boosting (football-only)")
results_summary.append(s)

# ---------- Calibration check for logistic regression ----------
print("\n=== Calibration: Logistic Regression ===")
model = LogisticRegression(max_iter=1000)
train = feat[feat['season'] < 2022]
model.fit(train[FEATURES].values, train['home_win'].values)
test = feat[feat['season'] >= 2022]
probs = model.predict_proba(test[FEATURES].values)[:, 1]
truth = test['home_win'].values

bins = [0, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.0]
labels = ['<45%', '45-50%', '50-55%', '55-60%', '60-65%', '65-70%', '70%+']
test_c = test.copy()
test_c['pred_prob'] = probs
test_c['bucket'] = pd.cut(probs, bins=bins, labels=labels)
calib = test_c.groupby('bucket', observed=True).agg(
    n=('home_win', 'count'),
    predicted_avg=('pred_prob', 'mean'),
    actual_rate=('home_win', 'mean')
)
print(calib)

pd.DataFrame(results_summary).to_csv('/home/claude/nfl_real_model/backtest_results.csv', index=False)
calib.to_csv('/home/claude/nfl_real_model/calibration.csv')
print("\nSaved backtest_results.csv and calibration.csv")
