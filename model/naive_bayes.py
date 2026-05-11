import math
from model.model_data import priors, total_words, word_counts, vocab_size

def calculate_likelihood(word, label):
    count = word_counts[label].get(word, 0)
    return (count + 1) / (total_words[label] + vocab_size)

def predict(tokens):
    if not tokens:
        return {"label": "Netral", "scores": {}}

    scores = {}

    for label in priors:
        score = math.log(priors[label])
        for word in tokens:
            likelihood = calculate_likelihood(word, label)
            score += math.log(likelihood)
        scores[label] = score

    best_label = max(scores, key=scores.get)

    return {
        "label": best_label,
        "scores": scores
    }