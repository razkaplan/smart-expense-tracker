# 💳 Smart Expense to Investment Tracker 📈

## 🚀 About the Project
This tool helps you analyze your **credit card expenses** and check whether you've spent money on publicly traded companies. It then **tracks their stock performance** since your purchase date.

🔹 **Upload a PDF of your credit card statement**  
🔹 **Automatically extracts transactions**  
🔹 **Identifies publicly traded companies**  
🔹 **Fetches stock data** and **visualizes trends**

📌 **Live Demo:** [Expense2Invest Streamlit App](https://expense2invest.streamlit.app/)

---
## 🛠️ How to Install and Run Locally

### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/your-username/smart-expense-tracker.git
cd smart-expense-tracker
```

### **2️⃣ Install Dependencies**
```bash
pip install -r requirements.txt
```

### **3️⃣ Run the App**
```bash
streamlit run app.py
```

---
## 🏗️ How It Works
1. Upload your **credit card PDF** (supports Israeli, US Mastercard, Visa, and Amex formats)
2. The tool **extracts transactions** (merchant, date, amount)
3. It **matches merchants to stock tickers** (e.g., Amazon → AMZN)
4. It fetches **stock data from Yahoo Finance**
5. You get an **interactive dashboard** to track stock trends!

---
## 🎨 Future Improvements
- 🔍 **Better company matching** using AI
- 📊 **More advanced analytics & insights**
- 🌎 **Multi-language support**

💡 **Contributions are welcome!** If you have ideas, feel free to open a PR.

