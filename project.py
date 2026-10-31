import pandas as pd
import yfinance as yf
import numpy as np
import ta
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
import warnings
warnings.filterwarnings('ignore')

# Download data
print("Downloading data...")
eurusd = yf.download("EURUSD=X", period="10y", interval="1d", auto_adjust=True, progress=False)
gbpusd = yf.download("GBPUSD=X", period="10y", interval="1d", auto_adjust=True, progress=False)
usdjpy = yf.download("USDJPY=X", period="10y", interval="1d", auto_adjust=True, progress=False)

# Flatten columns
for df in [eurusd, gbpusd, usdjpy]:
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

# Save raw data to CSV
eurusd.to_csv("EURUSD.csv")
gbpusd.to_csv("GBPUSD.csv")
usdjpy.to_csv("USDJPY.csv")
print("✅ CSV files saved: EURUSD.csv, GBPUSD.csv, USDJPY.csv")

print("EURUSD shape before cleaning:", eurusd.shape)

def create_advanced_features(df):
    """Create comprehensive technical indicators with proper NaN handling"""
    
    df = df.copy()
    
    # Basic price features (no NaN)
    df['Body'] = abs(df['Close'] - df['Open'])
    df['Upper_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['Lower_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['Range'] = df['High'] - df['Low']
    
    # SMAs (shorter periods first to minimize NaN)
    for period in [5, 10, 20]:
        df[f'SMA_{period}'] = df['Close'].rolling(window=period, min_periods=period//2).mean()
        df[f'SMA_Ratio_{period}'] = df['Close'] / df[f'SMA_{period}']
    
    # RSI (14 period default)
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    
    # MACD
    macd = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['Close'], window=20)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
    # ATR
    df['ATR'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
    
    # Price momentum
    df['Price_Change'] = df['Close'].pct_change()
    df['Price_Change_5'] = df['Close'].pct_change(5)
    
    # Volatility (rolling std)
    df['Volatility'] = df['Price_Change'].rolling(window=10, min_periods=5).std()
    
    # Lagged features (very powerful)
    for lag in [1, 2, 3]:
        df[f'Close_Lag_{lag}'] = df['Close'].shift(lag)
        df[f'Return_Lag_{lag}'] = df['Close'].pct_change(lag)
    
    # Target: Next day's direction
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    return df

# Add features
print("Creating features...")
eurusd = create_advanced_features(eurusd)

# Drop rows with NaN in target first
eurusd = eurusd.dropna(subset=['Target'])

# Fill remaining NaN with forward fill + backward fill + 0
eurusd = eurusd.fillna(method='ffill').fillna(method='bfill').fillna(0)

print("EURUSD shape after cleaning:", eurusd.shape)
print("Target distribution:")
print(eurusd['Target'].value_counts(normalize=True))

# Select features (only those that exist)
features = [
    'Open', 'High', 'Low', 'Close', 
    'Body', 'Range', 'RSI', 'MACD', 'MACD_Signal',
    'BB_Position', 'ATR', 'Price_Change', 'Volatility',
    'Close_Lag_1', 'Close_Lag_2', 'Return_Lag_1'
]

# Filter available features
available_features = [f for f in features if f in eurusd.columns]
print(f"Using {len(available_features)} features: {available_features[:5]}...")

X = eurusd[available_features]
y = eurusd['Target']

print(f"Final dataset: {X.shape}")

# Time-series split (80/20)
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx].copy(), X.iloc[split_idx:].copy()
y_train, y_test = y.iloc[:split_idx].copy(), y.iloc[split_idx:].copy()

# Scale features
scaler = RobustScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

X_train_scaled = pd.DataFrame(X_train_scaled, columns=available_features, index=X_train.index)
X_test_scaled = pd.DataFrame(X_test_scaled, columns=available_features, index=X_test.index)

print(f"Training set: {X_train_scaled.shape}, Test set: {X_test_scaled.shape}")

# Simple but effective models (faster training)
models = {
    'XGBoost': XGBClassifier(
        n_estimators=200, 
        learning_rate=0.1, 
        max_depth=6,
        random_state=42,
        eval_metric='logloss'
    ),
    'Random Forest': RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=10,
        random_state=42
    ),
    'Logistic Regression': LogisticRegression(
        C=1.0,
        max_iter=1000,
        random_state=42
    )
}

best_score = 0
best_model = None
best_name = ""

# Train models
for name, model in models.items():
    print(f"\nTraining {name}...")
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    score = accuracy_score(y_test, y_pred)
    
    print(f"{name} Test Accuracy: {score:.4f}")
    
    if score > best_score:
        best_score = score
        best_model = model
        best_name = name

print(f"\n🏆 Best Model: {best_name} with {best_score:.4f} accuracy")

# Detailed results
print("\nDetailed Results:")
print(classification_report(y_test, best_model.predict(X_test_scaled)))

# Feature importance
if hasattr(best_model, 'feature_importances_'):
    importance_df = pd.DataFrame({
        'feature': available_features,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)
    print("\nTop 10 Features:")
    print(importance_df.head(10))

# Save model
import pickle
model_data = {
    'model': best_model,
    'scaler': scaler,
    'features': available_features
}

with open('best_forex_model.pkl', 'wb') as f:
    pickle.dump(model_data, f)

print("\n✅ Model saved successfully!")
print(f"📈 Final Test Accuracy: {best_score:.4f}")

# Add this after your results to verify
print("🔍 VERIFICATION TESTS:")

# 1. Cross-validation score (most important)
from sklearn.model_selection import cross_val_score
cv_scores = cross_val_score(best_model, X_train_scaled, y_train, cv=5, scoring='accuracy')
print(f"✅ 5-Fold CV Score: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")

# 2. Walk-forward validation (time series)
walk_forward_scores = []
for i in range(100, len(X_test_scaled), 50):
    temp_train = X_train_scaled.iloc[:i]
    temp_test = X_test_scaled.iloc[i:i+50]
    temp_ytrain = y_train.iloc[:i]
    temp_ytest = y_test.iloc[i:i+50]
    
    model_temp = type(best_model)()
    model_temp.fit(temp_train, temp_ytrain)
    score = accuracy_score(temp_ytest, model_temp.predict(temp_test))
    walk_forward_scores.append(score)

print(f"✅ Walk-Forward Avg: {np.mean(walk_forward_scores):.4f}")

# 3. Out-of-sample on GBPUSD
print("\n🧪 Testing on GBPUSD (unseen pair)...")
gbpusd = create_advanced_features(gbpusd)
gbpusd = gbpusd.dropna(subset=['Target']).fillna(method='ffill').fillna(method='bfill').fillna(0)
X_gbp = gbpusd[available_features]
y_gbp = gbpusd['Target']
X_gbp_scaled = scaler.transform(X_gbp)
gbp_score = accuracy_score(y_gbp, best_model.predict(X_gbp_scaled))
print(f"GBPUSD OOS Accuracy: {gbp_score:.4f}")