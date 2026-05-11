import pandas as pd
from model.preprocessing import preprocess_text
from model.naive_bayes import predict

# load dataset
df = pd.read_csv("data/dataset.csv")

# mapping label
def label(score):
    if score >= 4:
        return "Positif"
    elif score <= 2:
        return "Negatif"
    else:
        return "Netral"

df['actual'] = df['score'].apply(label)

# buang netral
df = df[df['actual'] != "Netral"]

# prediksi
y_true = []
y_pred = []

for _, row in df.iterrows():
    tokens = preprocess_text(row['clean_text'])
    result = predict(tokens)
    pred = result["label"]

    y_true.append(row['actual'])
    y_pred.append(pred)

# confusion matrix
TP = TN = FP = FN = 0

for actual, pred in zip(y_true, y_pred):
    if actual == "Positif" and pred == "Positif":
        TP += 1
    elif actual == "Negatif" and pred == "Negatif":
        TN += 1
    elif actual == "Negatif" and pred == "Positif":
        FP += 1
    elif actual == "Positif" and pred == "Negatif":
        FN += 1

# accuracy
accuracy = (TP + TN) / (TP + TN + FP + FN)

print("=== CONFUSION MATRIX ===")
print("TP:", TP)
print("TN:", TN)
print("FP:", FP)
print("FN:", FN)

print("\n=== HASIL EVALUASI ===")
print("Accuracy:", round(accuracy * 100, 2), "%")