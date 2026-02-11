import os
import shutil
import stat
import time
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

def on_rm_error(func, path, exc_info):
    """
    Error handler for shutil.rmtree.
    If the error is due to an access error (read only file),
    it changes the file to be writable and then executes the function again.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"Could not force delete {path}. Reason: {e}")

def ingest_data():
    DB_PATH = '../data/vector_store/'
    
    print("Loading policy.txt...")
    loader = TextLoader("../data/policy.txt")
    documents = loader.load()

    print("Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    print("Creating Vector DB...")
    embeddings = FastEmbedEmbeddings()

    # 2. Robust Deletion Logic
    if os.path.exists(DB_PATH):
        print("Removing old vector store...")
        try:
            # Pass the error handler to fix permission issues
            shutil.rmtree(DB_PATH, onerror=on_rm_error)
            print("Previous vector store cleared.")
        except Exception as e:
            print(f"Error clearing database: {e}")
            print("TIP: Close any other Python terminals that might be using the DB.")
            return # Stop here if we can't clean up

    # 3. Create new DB
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH
    )

    print(f"Success! Vector DB created with {len(chunks)} chunks in '{DB_PATH}'")

if __name__ == "__main__":
    ingest_data()