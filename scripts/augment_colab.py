"""
Back-translation augmentation — chạy trên Colab trước khi train.

Thay thế train_augmented.csv (đã được tạo local bằng swap/insertion) bằng phiên bản
có back-translation cho Enjoyment, Anger, Surprise.

Cách dùng (trên Colab):
    !pip install deep_translator -q
    !python /content/MoodNote-AI/scripts/augment_colab.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TRAIN_CSV      = REPO_ROOT / "data" / "processed" / "train.csv"
OUTPUT_CSV     = REPO_ROOT / "data" / "processed" / "train_augmented.csv"
TEST_CSV       = REPO_ROOT / "data" / "processed" / "test.csv"


def main():
    try:
        from deep_translator import GoogleTranslator  # noqa: F401
    except ImportError:
        print("deep_translator not found. Run: pip install deep_translator")
        sys.exit(1)

    import pandas as pd
    from src.data.augment import augment_dataset

    print("=" * 60)
    print("Augmentation with back-translation (Colab)")
    print("=" * 60)
    print("Classes using back_translation: Enjoyment(0), Anger(2), Surprise(5)")
    print("Classes using swap/insertion  : Fear(3), Disgust(4)")
    print()

    augment_dataset(
        input_csv=str(TRAIN_CSV),
        output_csv=str(OUTPUT_CSV),
        target_counts={0: 2000, 2: 1800, 3: 1200, 4: 1100, 5: 1800},
        techniques=["swap", "insertion"],
        class_techniques={
            0: ["back_translation", "swap"],
            2: ["back_translation", "swap"],
            5: ["back_translation", "swap"],
        },
        seed=42,
    )

    # Leakage prevention
    if TEST_CSV.exists():
        test_texts = set(pd.read_csv(TEST_CSV)["text"].str.strip().str.lower())
        aug_df     = pd.read_csv(OUTPUT_CSV)
        before     = len(aug_df)
        aug_df     = aug_df[~aug_df["text"].str.strip().str.lower().isin(test_texts)]
        n_removed  = before - len(aug_df)
        if n_removed:
            aug_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
            print(f"Removed {n_removed} augmented samples overlapping with test set.")

    print("\nDone! train_augmented.csv ready for training.")


if __name__ == "__main__":
    main()
