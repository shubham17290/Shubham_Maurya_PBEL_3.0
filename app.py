from flask import Flask, request, render_template
import pickle
import re

# YEH LINE SABSE ZAROORI HAI RENDER KE LIYE
app = Flask(__name__)

# Pre-trained model aur vectorizer ko load kar rahe hain
model = pickle.load(open("model.pkl", "rb"))
vectorization = pickle.load(open("vectorizer.pkl", "rb"))


# Text Cleaning Function
def wordopt(text):
    text = str(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\d", "", text)
    text = re.sub(r"\n", " ", text)
    return text


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    if request.method == "POST":
        news_text = request.form["news_input"]

        # Process input text
        cleaned_text = wordopt(news_text)
        vectorized_text = vectorization.transform([cleaned_text])

        # Predict using the loaded model
        prediction = model.predict(vectorized_text)
        result = "Real News" if prediction[0] == 1 else "Fake News"

        return render_template("index.html", prediction_text=f"Prediction: {result}")


if __name__ == "__main__":
    app.run()

