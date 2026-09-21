# MoodNote AI - Vietnamese Emotion Classification

Repo đang được xây lại từ đầu để bám sát Nội dung 1 & 2 của đề cương NCKH 2026
("Nghiên cứu phân tích cảm xúc tiếng Việt và thuật toán gợi ý âm nhạc theo cảm
xúc, nhận biết ngữ cảnh"): sinh dữ liệu nhật ký giả lập bằng LLM mã nguồn mở
(Human-in-the-loop QA) + huấn luyện/đánh giá ablation mô hình PhoBERT trên
UIT-VSMEC.

Việc rebuild chia thành 7 phase tuần tự. **Phase 1-2 đã xong**: khung dự án,
`src/utils/*` carry-forward, schema validate config, CI lint; tải + tiền xử lý UIT-VSMEC.

## Roadmap

1. ✅ Scaffold dự án + core utils (config, logger, emotion constants, metrics) + CI.
2. ✅ Dữ liệu thật (UIT-VSMEC): tải + tiền xử lý, giữ nguyên split train/validation/test gốc.
3. Dữ liệu giả lập bằng LLM (Llama-3-8B-Instruct, Qwen3-8B) + Human-in-the-loop QA.
4. Huấn luyện PhoBERT + ablation 3 kịch bản (real-only/synthetic-only/combined).
5. Serving layer (inference/API), sửa công thức tính intensity.
6. Mở rộng testing & CI (models/training/inference thật).
7. Tài liệu cuối (methodology, kết quả) phục vụ báo cáo NCKH.

## Chuẩn bị dữ liệu thật (UIT-VSMEC)

```bash
.venv/Scripts/python.exe -m src.data.real.download_vsmec   # -> data/real/raw/{train,validation,test}.csv
.venv/Scripts/python.exe -m src.data.real.preprocess       # -> data/real/processed/{train,validation,test}.csv
```

`data/real/processed/test.csv` là tập kiểm thử cố định cho cả 3 kịch bản ablation: chỉ ghi
lần đầu, các lần chạy sau nếu kết quả khác sẽ báo lỗi thay vì ghi đè.

## Chạy lint

```bash
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
```

Cài môi trường: `pip install -r requirements.txt` (đầy đủ, gồm torch/transformers) hoặc
`pip install -r requirements-dev.txt` (chỉ ruff, giống CI).

Bộ test tạm gỡ theo yêu cầu chủ dự án — CI hiện chỉ lint.
