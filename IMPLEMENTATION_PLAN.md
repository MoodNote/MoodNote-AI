# Implementation Plan: Accuracy Improvement + FR-11/12/13

**Version:** 1.0
**Date:** 2026-03-08
**Scope:** AI Module — MoodNote-AI (PhoBERT Emotion Classifier)

---

## 1. Tổng quan

| Mục tiêu | Trạng thái trước | Target | Trạng thái sau |
|-----------|-----------------|--------|----------------|
| Accuracy | 64.07% | ≥ 75% | Chờ train lại |
| F1-Macro | 61.10% | ≥ 70% | Chờ train lại |
| FR-11: Sentiment Score | Chưa có | -1.0 đến +1.0 | ✅ Implemented |
| FR-12: Intensity | Chưa có | 0 đến 100 | ✅ Implemented |
| FR-13: Keyword Extraction | Chưa có | 3-10 từ/văn bản | ✅ Implemented |

---

## 2. Phase 1 — Tăng Accuracy (Target: ≥ 75%)

### 2.1 Label Smoothing

**Vấn đề:** Model quá tự tin (overconfident), dễ overfit trên training set.

**Giải pháp:** Label smoothing `0.1` — thay vì học nhãn cứng (0 hoặc 1), model học phân phối mềm `[0.0167, ..., 0.9167, ..., 0.0167]`, giúp generalize tốt hơn.

**Files đã sửa:**
- [configs/model_config.yaml](configs/model_config.yaml): Thêm `label_smoothing: 0.1`
- [src/models/phobert_classifier.py](src/models/phobert_classifier.py): Thêm param `label_smoothing` vào `__init__()` và `CrossEntropyLoss`
- [scripts/train.py](scripts/train.py): Truyền `label_smoothing` từ config vào model

```python
# phobert_classifier.py — forward()
loss = nn.CrossEntropyLoss(
    weight=weight,
    label_smoothing=self.label_smoothing  # 0.1
)(logits, labels)
```

---

### 2.2 Cosine LR Scheduler

**Vấn đề:** Linear decay cắt giảm LR đều đặn, không tối ưu cho fine-tuning BERT.

**Giải pháp:** Cosine scheduler giảm LR theo dạng cosine — chậm ở đầu, nhanh ở giữa, chậm lại ở cuối — thường cho kết quả tốt hơn.

**Files đã sửa:**
- [configs/training_config.yaml](configs/training_config.yaml): `scheduler.type: "cosine"`
- [src/training/trainer.py](src/training/trainer.py): `lr_scheduler_type="cosine"` trong `TrainingArguments`

---

### 2.3 Hyperparameter Tuning

**Files đã sửa:** [configs/training_config.yaml](configs/training_config.yaml)

| Param | Trước | Sau | Lý do |
|-------|-------|-----|-------|
| `learning_rate` | 3e-5 | 2e-5 | LR thấp hơn ổn định hơn cho fine-tuning |
| `num_epochs` | 10 | 15 | Nhiều epoch hơn (early stopping giữ best) |
| `warmup_steps` | 200 | 300 | Warmup dài hơn tránh learning quá nhanh ban đầu |
| `scheduler` | linear | cosine | Cosine decay tốt hơn cho BERT |

---

### 2.4 Fix Save/Load Model

**Vấn đề:** Checkpoint cũ không lưu `dropout` và `label_smoothing` → khi load lại model dùng giá trị mặc định.

**Files đã sửa:** [src/models/model_utils.py](src/models/model_utils.py)

```python
# save_model(): thêm vào checkpoint dict
'dropout': model.dropout.p,
'label_smoothing': model.label_smoothing

# load_model(): đọc từ checkpoint
dropout=checkpoint.get('dropout', 0.1),
label_smoothing=checkpoint.get('label_smoothing', 0.0)
```

---

## 3. Phase 2 — FR-11: Sentiment Score (-1.0 đến +1.0)

**Mô tả SRS:** Mỗi diary entry phải có điểm sentiment từ -1.0 (rất tiêu cực) đến +1.0 (rất tích cực).

**Cách tính:** Weighted sum của xác suất mỗi cảm xúc nhân với giá trị sentiment của cảm xúc đó.

```
sentiment_score = Σ(sentiment_value[emotion_i] × P(emotion_i))
```

**Sentiment mapping** ([configs/model_config.yaml](configs/model_config.yaml)):

| Cảm xúc | Giá trị | Lý do |
|---------|---------|-------|
| Enjoyment | +1.0 | Tích cực nhất |
| Surprise | +0.3 | Trung tính dương |
| Other | 0.0 | Trung tính |
| Fear | -0.5 | Tiêu cực nhẹ |
| Disgust | -0.7 | Tiêu cực vừa |
| Sadness | -0.8 | Tiêu cực mạnh |
| Anger | -0.9 | Tiêu cực nhất |

**Ví dụ:**
- Text "Hôm nay rất vui!" → P(Enjoyment)=0.92 → score ≈ **+0.87**
- Text "Tôi buồn quá" → P(Sadness)=0.85 → score ≈ **-0.67**

**Files đã sửa:**
- [configs/model_config.yaml](configs/model_config.yaml): Thêm section `sentiment_scores`
- [src/inference/predictor.py](src/inference/predictor.py): Tính `sentiment_score` trong `predict()`
- [src/inference/api.py](src/inference/api.py): Thêm `sentiment_score: float` vào `PredictionResponse`

---

## 4. Phase 3 — FR-12: Intensity (0-100)

**Mô tả SRS:** Mức độ mạnh yếu của cảm xúc, từ 0 (rất nhẹ/không rõ) đến 100 (rất mạnh/rõ ràng).

**Cách tính:** Dựa trên entropy của phân phối xác suất.

```
entropy = -Σ(P(i) × log(P(i)))
max_entropy = log(7) ≈ 1.946   # entropy tối đa khi phân phối đều
intensity = (1 - entropy/max_entropy) × 100
```

**Tính chất:**
- Khi model predict 95% Enjoyment → entropy thấp → intensity ≈ **85-95**
- Khi model không chắc, phân phối đều → entropy cao → intensity ≈ **5-15**

**Files đã sửa:**
- [src/inference/predictor.py](src/inference/predictor.py): Tính `intensity` trong `predict()`
- [src/inference/api.py](src/inference/api.py): Thêm `intensity: float` vào `PredictionResponse`

---

## 5. Phase 4 — FR-13: Keyword Extraction (3-10 từ)

**Mô tả SRS:** Trích xuất 3-10 từ khóa quan trọng nhất từ mỗi diary entry.

**Thư viện:** [YAKE](https://github.com/LIAAD/yake) (Yet Another Keyword Extractor)
- Không cần corpus, không cần train
- Hoạt động tốt với tiếng Việt đã segment bởi pyvi
- Nhẹ và nhanh, phù hợp cho inference real-time

**Cách hoạt động YAKE:** Tính điểm quan trọng của từng từ dựa trên vị trí, tần suất, và ngữ cảnh xung quanh. Điểm thấp = quan trọng hơn.

**Files đã tạo/sửa:**
- [src/utils/keyword_extractor.py](src/utils/keyword_extractor.py): **File mới** — `VietnameseKeywordExtractor` class
- [src/inference/predictor.py](src/inference/predictor.py): Tích hợp keyword extraction
- [src/inference/api.py](src/inference/api.py): Thêm `keywords: List[str]` vào `PredictionResponse`
- [train_colab.ipynb](train_colab.ipynb): Thêm `pip install yake`

---

## 6. API Response sau khi implement

**Endpoint:** `POST /predict`

**Request:**
```json
{
  "text": "Hôm nay tôi rất vui và hạnh phúc khi được gặp lại bạn bè"
}
```

**Response (mới):**
```json
{
  "text": "Hôm nay tôi rất vui và hạnh phúc khi được gặp lại bạn bè",
  "emotion": "Enjoyment",
  "confidence": 0.9234,
  "probabilities": {
    "Enjoyment": 0.9234,
    "Sadness": 0.0123,
    "Anger": 0.0089,
    "Fear": 0.0201,
    "Disgust": 0.0156,
    "Surprise": 0.0145,
    "Other": 0.0052
  },
  "sentiment_score": 0.87,
  "intensity": 82.5,
  "keywords": ["vui", "hạnh phúc", "bạn bè", "gặp lại"]
}
```

---

## 7. Hướng dẫn train lại trên Colab

```bash
# 1. Push code lên GitHub
git add -A
git commit -m "feat: label smoothing, cosine scheduler, FR-11/12/13"
git push origin main

# 2. Trên Colab — pull code mới
cd /content/MoodNote-AI
git pull origin main

# 3. Chạy notebook từ Cell 1 đến Cell 7
# (KHÔNG cần download dataset lại nếu data/processed/ còn tồn tại)
```

**Kỳ vọng sau training:**
- Accuracy: 68-75% (tăng từ 64%)
- F1-Macro: 65-72% (tăng từ 61%)
- Anger recall được cải thiện nhờ class weights

---

## 8. Files đã thay đổi

| File | Loại | Thay đổi chính |
|------|------|----------------|
| [configs/model_config.yaml](configs/model_config.yaml) | Edit | `label_smoothing: 0.1`, `sentiment_scores` mapping |
| [configs/training_config.yaml](configs/training_config.yaml) | Edit | LR `2e-5`, epochs `15`, cosine scheduler |
| [src/models/phobert_classifier.py](src/models/phobert_classifier.py) | Edit | `label_smoothing` param trong `CrossEntropyLoss` |
| [src/models/model_utils.py](src/models/model_utils.py) | Edit | Save/load `dropout` và `label_smoothing` |
| [src/training/trainer.py](src/training/trainer.py) | Edit | `lr_scheduler_type="cosine"` |
| [scripts/train.py](scripts/train.py) | Edit | Truyền `label_smoothing` vào model |
| [src/utils/keyword_extractor.py](src/utils/keyword_extractor.py) | **New** | YAKE keyword extractor cho tiếng Việt |
| [src/inference/predictor.py](src/inference/predictor.py) | Edit | Tính `sentiment_score`, `intensity`, `keywords` |
| [src/inference/api.py](src/inference/api.py) | Edit | `PredictionResponse` có 3 trường mới |
| [train_colab.ipynb](train_colab.ipynb) | Edit | `pip install yake`, `label_smoothing` trong Cell 6 |

---

## 9. Dependencies mới

```
yake>=0.4.8
```

Thêm vào `requirements.txt` nếu chưa có.
