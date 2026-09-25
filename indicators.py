"""Plain-Python technical indicators. Each returns a list aligned to the input."""


def ema(values, period):
    out, k, prev = [], 2 / (period + 1), None
    for v in values:
        prev = v if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def rsi(closes, period=14):
    out = [50.0] * len(closes)
    gain = loss = 0.0
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        g, l_ = max(ch, 0), max(-ch, 0)
        if i <= period:
            gain += g / period
            loss += l_ / period
        else:
            gain = (gain * (period - 1) + g) / period
            loss = (loss * (period - 1) + l_) / period
        if i >= period:
            out[i] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    return out


def atr(candles, period=14):
    out, prev_atr = [], None
    for i, c in enumerate(candles):
        tr = c["h"] - c["l"] if i == 0 else max(
            c["h"] - c["l"], abs(c["h"] - candles[i - 1]["c"]), abs(c["l"] - candles[i - 1]["c"]))
        prev_atr = tr if prev_atr is None else (prev_atr * (period - 1) + tr) / period
        out.append(prev_atr)
    return out
