FROM python:3.11

# Set up a new user named "user" with user ID 1000 for permission
RUN useradd -m -u 1000 user
# Switch to the "user" user
USER user
# Set home to the user's home directory
ENV HOME=/Users/miguel/Desktop/conversational_om/user \
	PATH=/Users/miguel/Desktop/conversational_om/user/.local/bin:$PATH
# Upgreade pip
RUN pip install --no-cache-dir --upgrade pip

COPY --chown=user requirements.txt .

# Install requirements
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user travel.py travel.py

ENTRYPOINT ["solara", "run", "travel.py", "--host=0.0.0.0", "--port", "7860"]
