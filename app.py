# train.py (Sirf apne laptop par run karna hai ek baar)
import pandas as pd
import re
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


def wordopt(text):
    text = str(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\d", "", text)
    text = re.sub(r"\n", " ", text)
    return text


print("Training model locally...")
df_fake = pd.read_csv("Fake.csv").head(5000)
df_true = pd.read_csv("True.csv").head(5000)

df_fake["class"] = 0
df_true["class"] = 1

df_marge = pd.concat([df_fake, df_true], axis=0).sample(frac=1).reset_index(drop=True)
df_marge["text"] = df_marge["text"].apply(wordopt)

vectorization = TfidfVectorizer()
xv = vectorization.fit_transform(df_marge["text"])

model = LogisticRegression()
model.fit(xv, df_marge["class"])

# Files ko save kar rahe hain
pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(vectorization, open("vectorizer.pkl", "wb"))
print("Done! model.pkl and vectorizer.pkl created successfully.")
