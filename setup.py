from setuptools import setup, find_packages

setup(
    name="mariagpt_nexus",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "flask>=2.0.0",
        "autogen>=1.0.0",
        "google-auth>=2.0.0",
        "google-auth-oauthlib>=1.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-api-python-client>=2.0.0",
        "python-docx>=0.8.11"
    ],
    python_requires=">=3.8",
)
