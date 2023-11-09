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

# Copy the requirements.txt file and set ownership to the "user"
COPY --chown=user:user requirements.txt $HOME/

# Change to the user's home directory
WORKDIR $HOME

# Install requirements
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the application source code and set ownership to the "user"
COPY --chown=user:user travel.py .

# Expose the port the app runs on
EXPOSE 7860

# Set the default command to run the app
ENTRYPOINT ["python", "-m", "solara", "run", "travel.py", "--host=0.0.0.0", "--port=80"]

