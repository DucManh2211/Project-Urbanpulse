"""
risk_service.py — Load risk_classifier_model.joblib (Tuần 7) và cung cấp
hàm classify_risk() dùng chung cho API.

Đặt file model tại: <project_root>/models/risk_classifier_model.joblib
(copy file .joblib bạn đã lưu ở Ngày 42 vào đúng đường dẫn này).
"""

import sys
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODEL_PATH = PROJECT_ROOT / "models" / "risk_classifier_model.joblib"

_model = None  # cache trong RAM, load 1 lần duy nhất


def load_risk_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Không tìm thấy model tại {MODEL_PATH}. "
                f"Copy file risk_classifier_model.joblib (Ngày 42) vào đúng thư mục models/."
            )
        _model = joblib.load(MODEL_PATH)
        print(f"[risk_service] Đã load model từ {MODEL_PATH}")
    return _model


def classify_risk(aqi: float, hour: int, temperature: float, humidity: float,
                   user_group: str = "healthy") -> dict:
    """
    Trả về dict gồm risk_level (nhãn cuối) và probabilities (xác suất từng lớp).
    Áp dụng threshold tùy chỉnh theo nhóm đối tượng — đúng logic đã học/debug ở Ngày 42.
    """
    model = load_risk_model()

    input_df = pd.DataFrame([{
        "aqi": aqi, "hour": hour, "temperature": temperature,
        "humidity": humidity, "user_group": user_group,
    }])

    probs = model.predict_proba(input_df)[0]
    classes = model.classes_
    prob_dict = dict(zip(classes, probs.tolist()))

    # Threshold khác nhau theo nhóm — ÁP DỤNG NHẤT QUÁN cho cả 2 mức (đã sửa bug Ngày 42)
    threshold_nguyhiem = 0.1 if user_group in ["child", "elderly"] else 0.2
    threshold_cao = 0.3 if user_group in ["child", "elderly"] else 0.5

    if prob_dict.get("NguyHiem", 0) > threshold_nguyhiem:
        risk_level = "NguyHiem"
    elif prob_dict.get("Cao", 0) > threshold_cao:
        risk_level = "Cao"
    else:
        risk_level = model.predict(input_df)[0]

    return {"risk_level": risk_level, "probabilities": prob_dict}
