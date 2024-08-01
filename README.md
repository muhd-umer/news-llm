<p align="center">
  <img src="images/banner.png" width="60%">
</p>

NewsLLM is a RAG-based LLM application designed to analyze and summarize news articles. It uses the [Google Generative AI](https://cloud.google.com/ai-solutions/gemini) model to generate summaries and insights for different countries and different topics. The application is built using Streamlit and Python.

## Getting Started

1. **Clone the repository:**
    ```
    git clone https://github.com/muhd-umer/news-llm.git
    ```

2. **Install dependencies:**
    ```
    pip install -r requirements.txt
    ```
    
3. **Set API Key:** Obtain an API key for Google Generative AI and store it in a `.env` file as `GOOGLE_API_KEY="<your_api_key>"`.
2. **Run the application:**
    ```
    streamlit run app.py
    ```
