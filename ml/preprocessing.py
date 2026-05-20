import re
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# stopword & stemmer
stop_words = set(stopwords.words('indonesian'))
stemmer = StemmerFactory().create_stemmer()

# kamus normalisasi
normalisasi_dict = {
    "gk": "tidak", "ga": "tidak", "nggak": "tidak",
    "tdk": "tidak", "bgt": "banget",
    "apk": "aplikasi", "app": "aplikasi",
    "eror": "error", "yg": "yang"
}

def preprocess_text(text):
    # 1. case folding
    text = str(text).lower()

    # 2. cleaning
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-z\s]', '', text)

    # 3. tokenizing
    tokens = text.split()

    # 4. normalisasi
    tokens = [normalisasi_dict.get(word, word) for word in tokens]

    # 5. stopword removal
    tokens = [w for w in tokens if w not in stop_words]

    # 6. stemming
    tokens = [stemmer.stem(w) for w in tokens]

    return tokens


