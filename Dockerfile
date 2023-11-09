FROM python:3.11

# Set up a new user named "user" with user ID 1000 for permission
RUN useradd -m -u 1000 user
# Switch to the "user" user
USER user
# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
# Upgrade pip
RUN pip install --no-cache-dir --user --upgrade pip

COPY --chown=user:user requirements.txt $HOME/

# Change to the user's home directory
WORKDIR $HOME

# Install requirements
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user:user travel.py .

ENTRYPOINT ["solara", "run", "travel.py", "--host=0.0.0.0", "--port=80"]
