import pandas as pd
from collections import Counter
from model.preprocessing import preprocess_text

df = pd.read_csv("data/dataset.csv")

def label(score):
    if score >= 4:
        return "Positif"
    elif score <= 2:
        return "Negatif"
    else:
        return "Netral"

df['label'] = df['score'].apply(label)

df = df[df['label'] != "Netral"]

df['tokens'] = df['clean_text'].apply(preprocess_text)

# 🔷 PRIOR
priors = df['label'].value_counts(normalize=True).to_dict()

# 🔷 WORD COUNTS
word_counts = {"Positif": Counter(), "Negatif": Counter()}

for _, row in df.iterrows():
    word_counts[row['label']].update(row['tokens'])

# 🔷 TOTAL WORDS
total_words = {
    label: sum(word_counts[label].values())
    for label in word_counts
}

# 🔷 VOCAB
vocab = set()
for words in word_counts.values():
    vocab.update(words)

vocab_size = len(vocab)

# 🔥 SIMPAN MODEL
with open("model/model_data.py", "w", encoding="utf-8") as f:
    f.write("priors = " + str(priors) + "\n\n")
    f.write("total_words = " + str(total_words) + "\n\n")
    f.write("vocab_size = " + str(vocab_size) + "\n\n")
    f.write("word_counts = " + str({k: dict(v) for k, v in word_counts.items()}))

# 🔥 DEBUG (TARUH DI PALING BAWAH)
print("Model berhasil disimpan!")
print("Priors:", priors)
print("Total Words:", total_words)
print("Vocab Size:", vocab_size)