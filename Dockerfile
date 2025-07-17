FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy Pipenv files and install dependencies
COPY Pipfile Pipfile.lock ./
RUN pip install pipenv && pipenv install --deploy --ignore-pipfile

# Copy entire project
COPY . .

# Expose Streamlit and Locust ports
EXPOSE 8501 8089

# Default command: run Streamlit
CMD ["pipenv", "run", "streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
