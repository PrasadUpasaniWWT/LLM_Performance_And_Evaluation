FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipenv files and install dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --ignore-pipfile

# Copy rest of the app
COPY . .

# Expose ports
EXPOSE 8501 8089

# Run Streamlit
CMD ["pipenv", "run", "streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
