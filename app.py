from flask import Flask, request, render_template
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

app = Flask(__name__)


# --- 1. Text Cleaning Function (wordopt) ---
def wordopt(text):
    text = str(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\d", "", text)
    text = re.sub(r"\n", " ", text)
    return text


# --- 2. Automatic Model Training on Startup ---
print("⏳ Model train ho raha hai... Isme kuch seconds lag sakte hain, please wait!")

# CSV files ko load kar rahe hain (make sure names exactly match your files)
df_fake = pd.read_csv("Fake.csv")
df_true = pd.read_csv("True.csv")

# Fake ko 0 aur True ko 1 class assign kar rahe hain
df_fake["class"] = 0
df_true["class"] = 1

# Dono datasets ko merge kar rahe hain
# Note: For faster startup in testing, hum sirf top 5000 rows le rahe hain.
# Agar accuracy badhani ho, toh '.head(5000)' hata dena.
df_fake_sampled = df_fake.head(5000)
df_true_sampled = df_true.head(5000)
df_marge = pd.concat([df_fake_sampled, df_true_sampled], axis=0)

# Data ko shuffle aur clean kar rahe hain
df_marge = df_marge.sample(frac=1).reset_index(drop=True)
df_marge["text"] = df_marge["text"].apply(wordopt)

x = df_marge["text"]
y = df_marge["class"]

# Vectorizer aur Model ko initialize karke train kar rahe hain
vectorization = TfidfVectorizer()
xv = vectorization.fit_transform(x)

model = LogisticRegression()
model.fit(xv, y)

print("✅ Model successfully train ho gaya hai! Flask server ab ready hai.")


# --- 3. Flask Web Routes ---
@app.route("/")
def home():
    # templates/ folder ke andar index.html hona zaroori hai
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    if request.method == "POST":
        # Form se input le rahe hain (ensure your HTML input name is 'news_input')
        news_text = request.form["news_input"]

        # Input ko clean aur vectorize kar rahe hain
        cleaned_text = wordopt(news_text)
        vectorized_text = vectorization.transform([cleaned_text])

        # Prediction
        prediction = model.predict(vectorized_text)

        # Result mapping (1 = Real, 0 = Fake)
        result = "Real News" if prediction[0] == 1 else "Fake News"

        return render_template("index.html", prediction_text=f"Prediction: {result}")


if __name__ == "__main__":
    # use_reloader=False isliye lagaya hai taaki server do baar data train na kare startup pe
    app.run(debug=True, use_reloader=False)
