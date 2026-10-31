from config import SL_PIPS, TP_PIPS


def generate_signal(prediction: int, price: float, pair: str):
    sl = SL_PIPS.get(pair, SL_PIPS["default"])
    tp = TP_PIPS.get(pair, TP_PIPS["default"])
    if prediction == 1:
        return "BUY",  price, round(price - sl, 5), round(price + tp, 5)
    return "SELL", price, round(price + sl, 5), round(price - tp, 5)
