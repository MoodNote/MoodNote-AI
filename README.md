# MoodNote AI - Vietnamese Emotion Classification

Repo đang được xây lại từ đầu để bám sát Nội dung 1 & 2 của đề cương NCKH 2026
("Nghiên cứu phân tích cảm xúc tiếng Việt và thuật toán gợi ý âm nhạc theo cảm
xúc, nhận biết ngữ cảnh"): sinh dữ liệu nhật ký giả lập bằng LLM mã nguồn mở
(Human-in-the-loop QA) + huấn luyện/đánh giá ablation mô hình PhoBERT trên
UIT-VSMEC.

Repo vừa được wipe trắng để làm lại; chỉ còn `configs/*.yaml` carry-forward,
giữ nguyên hyperparameter đã tuning. Việc rebuild chia thành 7 phase tuần tự.

## Roadmap

1. Scaffold dự án + core utils (config, logger, emotion constants, metrics) + CI.
2. Dữ liệu thật (UIT-VSMEC): tải + tiền xử lý, tách train/validation/test.
3. Dữ liệu giả lập bằng LLM (Llama-3-8B-Instruct, Qwen3-8B) + Human-in-the-loop QA.
4. Huấn luyện PhoBERT + ablation 3 kịch bản (real-only/synthetic-only/combined).
5. Serving layer (inference/API), sửa công thức tính intensity.
6. Mở rộng testing & CI (models/training/inference thật).
7. Tài liệu cuối (methodology, kết quả) phục vụ báo cáo NCKH.
