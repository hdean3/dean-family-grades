FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the entire project
COPY . .

# Install dependencies
RUN pip install --no-cache-dir streamlit pandas azure-storage-blob

# Expose the Streamlit port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
