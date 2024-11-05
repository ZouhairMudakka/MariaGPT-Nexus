from setuptools import setup, find_packages

setup(
    name="multi_agent_chatbot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "openai",
        "python-dotenv",
    ],
)
